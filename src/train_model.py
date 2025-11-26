import pandas as pd
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, confusion_matrix
from species_rules import get_species_list

DATA_PATH = "data/fisherai_dataset.csv"
MODEL_DIR = "models/"

# Ensure models folder exists
os.makedirs(MODEL_DIR, exist_ok=True)

def train_species_model(species):
    """Train a RandomForest model for a given species."""

    print(f"\n🔹 Training model for: {species}")

    df = pd.read_csv(DATA_PATH)

    # Ensure tide phase encoded
    tide_map = {'Low': 0, 'Rising': 1, 'High': 2, 'Falling': 3, 'Unknown': -1}
    df["tide_phase_num"] = df["tide_phase"].map(tide_map)

    # Features ML will learn from
    features = [
        "wind_speed",
        "wind_deg",
        "pressure",
        "swell_height",
        "swell_period",
        "swell_direction",
        "sea_temp",
        "tide_phase_num"
    ]

    # Target labels for this species
    label_col = f"{species}_label"

    if label_col not in df.columns:
        print(f"⚠️ WARNING: Label column missing → {label_col}")
        return

    X = df[features]
    y = df[label_col]

    # Encode Ideal / Good / Poor -> 0/1/2
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.20, random_state=42, stratify=y_enc
    )

    # RandomForest = best for tabular ML data
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)

    # Predictions & accuracy
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"   ✔ Accuracy: {acc*100:.2f}%")
    print("   ✔ Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Save model + encoder
    joblib.dump(model, f"{MODEL_DIR}{species}_rf_model.pkl")
    joblib.dump(le, f"{MODEL_DIR}{species}_label_encoder.pkl")

    print(f"   ✔ Saved model → {MODEL_DIR}{species}_rf_model.pkl")
    print(f"   ✔ Saved encoder → {MODEL_DIR}{species}_label_encoder.pkl")


def train_all():
    """Train models for every species in CSV."""
    species_list = get_species_list()
    print("\n=== TRAINING MODELS FOR SPECIES ===")
    print(species_list)

    for sp in species_list:
        train_species_model(sp)

    print("\n🎉 ALL MODELS TRAINED & SAVED SUCCESSFULLY!")


if __name__ == "__main__":
    train_all()
