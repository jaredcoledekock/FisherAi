from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import datetime
import os
from species_rules import (
    get_species_list,
    baits_for,
    species_notes,
)
from collect_data import (
    fetch_openweather,
    fetch_open_meteo,
    fetch_tide_phase,
)
from region_data import list_regions
from planner_service import plan_trip, PlanningError
from auth import get_user_id
from presets_store import get_presets, add_preset

app = Flask(__name__)
CORS(app)

MODEL_DIR = "models/"

# --------------------------------------------------------
# LOAD ALL MODELS + LABEL ENCODERS AT STARTUP
# --------------------------------------------------------
models = {}
encoders = {}

print("🔄 Loading AI models...")

species_list = get_species_list()

for sp in species_list:
    model_path = f"{MODEL_DIR}{sp}_rf_model.pkl"
    enc_path = f"{MODEL_DIR}{sp}_label_encoder.pkl"

    if os.path.exists(model_path) and os.path.exists(enc_path):
        models[sp] = joblib.load(model_path)
        encoders[sp] = joblib.load(enc_path)
        print(f"   ✔ Loaded model for: {sp}")
    else:
        print(f"   ⚠ WARNING: Missing model or encoder for {sp}")

print("✅ All available models loaded.\n")


# --------------------------------------------------------
# UTILITY → BUILD FEATURE VECTOR
# --------------------------------------------------------
def build_feature_vector(date_obj):
    """Fetch forecast data & build model-ready feature vector."""

    ow = fetch_openweather(date_obj)
    om = fetch_open_meteo(date_obj)
    tide = fetch_tide_phase(date_obj)

    tide_map = {
        "Low": 0,
        "Rising": 1,
        "High": 2,
        "Falling": 3,
        "Unknown": -1,
    }

    fv = [
        ow.get("wind_speed", 0),
        ow.get("wind_deg", 0),
        ow.get("pressure", 0),
        om.get("swell_height", 0),
        om.get("swell_period", 0),
        om.get("swell_direction", 0),
        om.get("sea_temp", 0),
        tide_map.get(tide, -1),
    ]

    return fv, tide, ow, om


# --------------------------------------------------------
# API ENDPOINT → PREDICT
# --------------------------------------------------------
@app.route("/predict")
def predict():
    """Predict fishing conditions for a species & date."""

    species = request.args.get("species", "").strip().lower()
    date_str = request.args.get("date", "").strip()

    if not species or not date_str:
        return jsonify({"error": "Missing 'species' or 'date' parameter"}), 400

    if species not in models:
        available = get_species_list()
        return jsonify({
            "error": f"Species '{species}' not supported",
            "available_species": available
        }), 400

    # Convert incoming date
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    try:
        fv, tide_phase, ow, om = build_feature_vector(date_obj)
        model = models[species]
        enc = encoders[species]

        pred_idx = model.predict([fv])[0]
        label = enc.inverse_transform([pred_idx])[0]
        confidence = float(model.predict_proba([fv])[0].max())

        return jsonify({
            "species": species,
            "prediction": label,
            "confidence": confidence,
            "recommended_baits": baits_for(species),
            "notes": species_notes(species),
            "conditions": {
                "wind_speed": ow.get("wind_speed"),
                "wind_direction": ow.get("wind_deg"),
                "pressure": ow.get("pressure"),
                "sea_temp": om.get("sea_temp"),
                "swell_height": om.get("swell_height"),
                "swell_period": om.get("swell_period"),
                "tide_phase": tide_phase,
            }
        })

    except Exception as e:
        return jsonify({
            "error": "Internal prediction error",
            "details": str(e)
        }), 500


# --------------------------------------------------------
# API ENDPOINT → REGION + SPECIES METADATA
# --------------------------------------------------------
@app.route("/meta/regions")
def meta_regions():
    """Return region + area metadata and supported species."""
    return jsonify({
        "regions": list_regions(),
        "species": get_species_list(),
        "defaults": {
            "region_id": "western_cape",
            "area_id": "false_bay",
        }
    })


# --------------------------------------------------------
# API ENDPOINT → MULTI-SPECIES PLANNER
# --------------------------------------------------------
@app.route("/plan", methods=["POST"])
def plan():
    """Plan best windows by region/area/species/date range."""
    try:
        payload = request.get_json(force=True) or {}
        region_id = (payload.get("region_id") or "").strip()
        area_id = (payload.get("area_id") or "").strip()
        species = payload.get("species") or []
        start_date = (payload.get("start_date") or "").strip()
        end_date = (payload.get("end_date") or "").strip()

        if not region_id or not area_id:
            return jsonify({"error": "region_id and area_id are required"}), 400
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date are required"}), 400

        result = plan_trip(
            region_id=region_id,
            area_id=area_id,
            species=[s.lower() for s in species] if species else [],
            start_date=start_date,
            end_date=end_date,
        )
        return jsonify(result)
    except PlanningError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({
            "error": "Internal planning error",
            "details": str(e)
        }), 500


# --------------------------------------------------------
# API ENDPOINT → USER PRESETS (requires user id)
# --------------------------------------------------------
@app.route("/user/presets", methods=["GET", "POST"])
def user_presets():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized. Provide Bearer token or X-User-Id header."}), 401

    if request.method == "GET":
        return jsonify({"user_id": user_id, "presets": get_presets(user_id)})

    payload = request.get_json(force=True) or {}
    required = ["region_id", "area_id", "species", "start_date", "end_date"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    saved = add_preset(user_id, {
        "region_id": payload["region_id"],
        "area_id": payload["area_id"],
        "species": payload["species"],
        "start_date": payload["start_date"],
        "end_date": payload["end_date"],
    })
    return jsonify({"user_id": user_id, "presets": saved})


# --------------------------------------------------------
# API ENDPOINT → FEEDBACK CAPTURE
# --------------------------------------------------------
@app.route("/feedback", methods=["POST"])
def feedback():
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        payload = {}

    entry = {
        "received_at": datetime.datetime.utcnow().isoformat() + "Z",
        "user_id": get_user_id(),
        "payload": payload,
    }

    try:
        os.makedirs("data", exist_ok=True)
        with open("data/feedback.log", "a") as f:
            f.write(f"{entry}\n")
    except Exception:
        pass

    return jsonify({"status": "ok"})


# --------------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------------
@app.route("/")
def home():
    return jsonify({
        "message": "False Bay FisherAI API Running",
        "species_supported": get_species_list(),
        "endpoints": {
            "/predict": "Predict conditions → /predict?species=kob&date=2025-12-01",
            "/meta/regions": "Region + species metadata",
            "/plan": "Planner → POST region/area/species/date range",
            "/user/presets": "GET/POST user presets (needs auth header)",
            "/feedback": "POST feedback payload for scoring quality",
        }
    })


# --------------------------------------------------------
# MAIN
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
