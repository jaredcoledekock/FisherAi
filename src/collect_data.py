import os
import datetime
import pandas as pd
import requests
from dotenv import load_dotenv
from species_rules import get_species_list, label_species

# Load API keys from environment (.env)
load_dotenv()
OWM_API_KEY = os.getenv("OWM_API_KEY")

# False Bay coordinates
LAT, LON = -34.16, 18.47


# --------------------------------------------------------
# API CALLS
# --------------------------------------------------------

def fetch_openweather(date):
    """Fetch wind + weather conditions for a specific date."""
    ts = int(datetime.datetime.combine(date, datetime.time(12)).timestamp())

    url = (
        f"https://api.openweathermap.org/data/3.0/onecall/timemachine"
        f"?lat={LAT}&lon={LON}&dt={ts}&units=metric&appid={OWM_API_KEY}"
    )
    resp = requests.get(url)
    data = resp.json()

    # Some OWM accounts return "data", others return "current"
    current = data["data"][0] if "data" in data else data.get("current", {})

    return {
        "wind_speed": current.get("wind_speed", 0),
        "wind_deg": current.get("wind_deg", 0),
        "pressure": current.get("pressure", 0),
        "air_temp": current.get("temp", 0)
    }


def fetch_open_meteo(date):
    """Fetch swell, sea-surface temperature & wave data."""
    iso_date = date.isoformat()
    url = (
        f"https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={iso_date}&end_date={iso_date}"
        f"&hourly=swell_wave_height,swell_wave_direction,swell_wave_period,"
        f"sea_surface_temperature"
        f"&timezone=UTC"
    )

    data = requests.get(url).json()
    hourly = data.get("hourly", {})

    # Pick midday (12:00) index
    idx = 12

    return {
        "swell_height": hourly.get("swell_wave_height", [0]*24)[idx],
        "swell_period": hourly.get("swell_wave_period", [0]*24)[idx],
        "swell_direction": hourly.get("swell_wave_direction", [0]*24)[idx],
        "sea_temp": hourly.get("sea_surface_temperature", [0]*24)[idx],
    }


def fetch_tide_phase(date):
    """Approximate tide phase using sea_level_height trend."""
    iso_date = date.isoformat()
    url = (
        f"https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={iso_date}&end_date={iso_date}"
        f"&hourly=sea_level_height&timezone=UTC"
    )

    hourly = requests.get(url).json().get("hourly", {})
    sea = hourly.get("sea_level_height", [])

    if len(sea) < 16:
        return "Unknown"

    # Compare 9:00 vs 15:00
    if sea[15] > sea[9]:
        return "Rising"
    elif sea[15] < sea[9]:
        return "Falling"
    else:
        return "High"


# --------------------------------------------------------
# DATASET BUILDER
# --------------------------------------------------------

def build_dataset(start_date, end_date):
    """Create dataset with conditions + rule-based labels for ALL species."""
    species_list = get_species_list()
    print(f"Species detected: {species_list}")

    records = []
    date_iter = start_date

    while date_iter <= end_date:
        print(f"Fetching data for {date_iter}...")

        try:
            ow = fetch_openweather(date_iter)
            om = fetch_open_meteo(date_iter)
            tide = fetch_tide_phase(date_iter)

            # Combine features
            row = {**ow, **om, "tide_phase": tide, "date": date_iter}

            # Apply rule-based labels for each species
            for sp in species_list:
                try:
                    row[f"{sp}_label"] = label_species(sp, row)
                except:
                    row[f"{sp}_label"] = "Unknown"

            records.append(row)

        except Exception as e:
            print(f"Error on {date_iter}: {e}")

        date_iter += datetime.timedelta(days=1)

    df = pd.DataFrame(records)
    df.to_csv("data/fisherai_dataset.csv", index=False)
    print("\nDataset saved → data/fisherai_dataset.csv")


# --------------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------------

if __name__ == "__main__":
    # Default: last 365 days
    start = datetime.date.today() - datetime.timedelta(days=365)
    end = datetime.date.today() - datetime.timedelta(days=1)
    build_dataset(start, end)
