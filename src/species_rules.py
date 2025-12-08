import os
from pathlib import Path
import pandas as pd

# Load all species rules from CSV once at import; handle case-sensitive paths
RULES_PATH = Path("data/species_rules.csv")
if not RULES_PATH.exists():
    alt = Path("Data/species_rules.csv")
    if alt.exists():
        RULES_PATH = alt
rules_df = pd.read_csv(RULES_PATH)

def get_species_list():
    """Return all species names available in the CSV."""
    return rules_df['species'].unique().tolist()

def get_rules(species):
    """Return dictionary of rules for a given species."""
    row = rules_df.loc[rules_df['species'] == species]
    if row.empty:
        raise ValueError(f"Species '{species}' not found in CSV.")
    row = row.iloc[0]

    return {
        'species': species,
        'wind_min': row['wind_direction_min'],
        'wind_max': row['wind_direction_max'],
        'temp_min': row['water_temp_min'],
        'temp_max': row['water_temp_max'],
        'swell_max': row['swell_max'],
        'tide_pref': str(row['tide_pref']).split("/"),
        'baits': [b.strip() for b in str(row['ideal_baits']).split(";")],
        'notes': row.get("notes", "")
    }

def label_species(species, features):
    """Label a single species based on rule matching."""
    r = get_rules(species)

    wind_ok  = r['wind_min'] <= features['wind_deg'] <= r['wind_max']
    temp_ok  = r['temp_min'] <= features['sea_temp'] <= r['temp_max']
    swell_ok = features['swell_height'] <= r['swell_max']
    tide_ok  = features['tide_phase'] in r['tide_pref']

    if wind_ok and temp_ok and swell_ok and tide_ok:
        return "Ideal"
    elif temp_ok and swell_ok:
        return "Good"
    else:
        return "Poor"

def baits_for(species):
    """Return recommended bait list based on CSV."""
    return get_rules(species)['baits']

def species_notes(species):
    """Return a short description for UI tooltips."""
    return get_rules(species)['notes']
