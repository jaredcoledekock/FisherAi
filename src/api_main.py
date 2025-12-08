import datetime
import os
import sys
from pathlib import Path
from typing import List, Optional, Any, Dict

import joblib
import jwt
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure src modules are importable when uvicorn runs from repo root
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
sys.path.append(str(BASE_DIR))
sys.path.append(str(ROOT_DIR))

from species_rules import get_species_list, baits_for, species_notes
from collect_data import fetch_openweather, fetch_open_meteo, fetch_tide_phase
from region_data import list_regions
from planner_service import plan_trip, PlanningError
from presets_store import get_presets, add_preset

app = FastAPI(
    title="False Bay FisherAI API",
    description="FastAPI version of the planner + predictor",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_DIR = "models/"
# Render/Fly/Linux filesystems are case-sensitive; ensure the path matches the
# actual trained model directory.
if not os.path.exists(MODEL_DIR) and os.path.exists("Models/"):
    MODEL_DIR = "Models/"

models: Dict[str, Any] = {}
encoders: Dict[str, Any] = {}

print("🔄 Loading AI models (FastAPI)...")
for sp in get_species_list():
    model_path = f"{MODEL_DIR}{sp}_rf_model.pkl"
    enc_path = f"{MODEL_DIR}{sp}_label_encoder.pkl"
    if os.path.exists(model_path) and os.path.exists(enc_path):
        models[sp] = joblib.load(model_path)
        encoders[sp] = joblib.load(enc_path)
        print(f"   ✔ Loaded model for: {sp}")
    else:
        print(f"   ⚠ WARNING: Missing model or encoder for {sp}")
print("✅ Model load complete.\n")


def build_feature_vector(date_obj: datetime.date):
    """Fetch forecast data & build model-ready feature vector."""
    ow = fetch_openweather(date_obj)
    om = fetch_open_meteo(date_obj)
    tide = fetch_tide_phase(date_obj)

    tide_map = {"Low": 0, "Rising": 1, "High": 2, "Falling": 3, "Unknown": -1}

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


def resolve_user_id(authorization: Optional[str], dev_user: Optional[str]) -> Optional[str]:
    """
    Lightweight auth helper.
    - If SUPABASE_JWT_SECRET is set, attempt to verify a Bearer JWT and return sub/user_id.
    - Otherwise, allow a plain X-User-Id header as a lightweight dev override.
    """
    secret = os.getenv("SUPABASE_JWT_SECRET")
    token = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if secret and token:
        try:
            decoded = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return decoded.get("sub") or decoded.get("user_id")
        except Exception:
            return None

    if dev_user:
        return dev_user.strip()

    return None


class PlanPayload(BaseModel):
    region_id: str
    area_id: str
    species: List[str] = []
    start_date: str
    end_date: str


class FeedbackPayload(BaseModel):
    payload: dict


@app.get("/")
def home():
    return {
        "message": "False Bay FisherAI FastAPI Running",
        "species_supported": get_species_list(),
        "endpoints": {
            "/predict": "Predict conditions → /predict?species=kob&date=2025-12-01",
            "/meta/regions": "Region + species metadata",
            "/plan": "Planner → POST region/area/species/date range",
            "/user/presets": "GET/POST user presets (needs auth header)",
            "/feedback": "POST feedback payload for scoring quality",
        },
    }


@app.get("/meta/regions")
def meta_regions():
    return {
        "regions": list_regions(),
        "species": get_species_list(),
        "defaults": {"region_id": "western_cape", "area_id": "false_bay"},
    }


@app.post("/plan")
def plan(payload: PlanPayload):
    try:
        result = plan_trip(
            region_id=payload.region_id.strip(),
            area_id=payload.area_id.strip(),
            species=[s.lower() for s in payload.species] if payload.species else [],
            start_date=payload.start_date.strip(),
            end_date=payload.end_date.strip(),
        )
        return result
    except PlanningError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal planning error: {str(e)}"
        )


@app.get("/predict")
def predict(species: str, date: str):
    species_key = species.strip().lower()
    if not species_key or not date:
        raise HTTPException(status_code=400, detail="Missing species or date")
    if species_key not in models:
        raise HTTPException(
            status_code=400,
            detail=f"Species '{species_key}' not supported. Available: {', '.join(get_species_list())}",
        )
    try:
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        fv, tide_phase, ow, om = build_feature_vector(date_obj)
        model = models[species_key]
        enc = encoders[species_key]

        pred_idx = model.predict([fv])[0]
        label = enc.inverse_transform([pred_idx])[0]
        confidence = float(model.predict_proba([fv])[0].max())

        return {
            "species": species_key,
            "prediction": label,
            "confidence": confidence,
            "recommended_baits": baits_for(species_key),
            "notes": species_notes(species_key),
            "conditions": {
                "wind_speed": ow.get("wind_speed"),
                "wind_direction": ow.get("wind_deg"),
                "pressure": ow.get("pressure"),
                "sea_temp": om.get("sea_temp"),
                "swell_height": om.get("swell_height"),
                "swell_period": om.get("swell_period"),
                "tide_phase": tide_phase,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal prediction error: {str(e)}")


@app.get("/user/presets")
def list_presets(
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
):
    user_id = resolve_user_id(authorization, x_user_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized. Provide Bearer token or X-User-Id header.")
    return {"user_id": user_id, "presets": get_presets(user_id)}


@app.post("/user/presets")
def save_presets(
    payload: PlanPayload,
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
):
    user_id = resolve_user_id(authorization, x_user_id)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized. Provide Bearer token or X-User-Id header.")

    saved = add_preset(
        user_id,
        {
            "region_id": payload.region_id,
            "area_id": payload.area_id,
            "species": payload.species,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        },
    )
    return {"user_id": user_id, "presets": saved}


@app.post("/feedback")
def feedback(data: dict):
    entry = {
        "received_at": datetime.datetime.utcnow().isoformat() + "Z",
        "payload": data,
    }
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/feedback.log", "a") as f:
            f.write(f"{entry}\n")
    except Exception:
        pass
    return {"status": "ok"}
