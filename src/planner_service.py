import datetime
from typing import List, Dict, Any, Optional

import os
import requests

from species_rules import label_species, get_species_list
from species_metadata import SPECIES_METADATA
from region_data import find_area, SPECIES_LEGAL_NOTES

# Avoid hammering the API; cap the range for now
MAX_PLANNING_DAYS = 10

OWM_API_KEY = os.getenv("OWM_API_KEY")
STORMGLASS_API_KEY = os.getenv("STORMGLASS_API_KEY")
WORLDTIDES_API_KEY = os.getenv("WORLDTIDES_API_KEY")


class PlanningError(Exception):
    pass


def _parse_date(date_str: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as exc:
        raise PlanningError("Dates must be in YYYY-MM-DD format") from exc


def _safe_get(seq, idx, default=0):
    try:
        return seq[idx]
    except Exception:
        return default


def _hour_of(timestr: str) -> int:
    try:
        return int(timestr.split("T")[1].split(":")[0])
    except Exception:
        return 0


def _parse_time(timestr: str) -> Optional[datetime.datetime]:
    try:
        return datetime.datetime.fromisoformat(timestr.replace("Z", "+00:00"))
    except Exception:
        return None


def _nearest(record_list: List[Dict[str, Any]], target: datetime.datetime, field: str):
    best = None
    best_delta = None
    for rec in record_list:
        ts = rec.get("time_dt")
        if not ts:
            continue
        delta = abs((ts - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = rec.get(field, 0)
    return best


def fetch_open_meteo(lat: float, lon: float, date: datetime.date) -> Dict[str, Any]:
    iso_date = date.isoformat()
    tz = "Africa/Johannesburg"

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={iso_date}&end_date={iso_date}"
        "&hourly=wind_speed_10m,wind_direction_10m,temperature_2m"
        f"&timezone={tz}"
    )

    marine_url = (
        "https://marine-api.open-meteo.com/v1/marine"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={iso_date}&end_date={iso_date}"
        # Request both swell_* and combined wave_* to reduce gaps
        "&hourly=swell_wave_height,swell_wave_direction,swell_wave_period,"
        "wave_height,wave_direction,wave_period,sea_surface_temperature,sea_level"
        f"&timezone={tz}"
    )

    try:
        weather = requests.get(weather_url, timeout=12).json().get("hourly", {})
    except Exception:
        weather = {}

    try:
        marine = requests.get(marine_url, timeout=12).json().get("hourly", {})
    except Exception:
        marine = {}

    return {"weather": weather, "marine": marine}


def fetch_owm_forecast(lat: float, lon: float) -> List[Dict[str, Any]]:
    """3-hourly forecast (5 days)."""
    if not OWM_API_KEY:
        return []
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&units=metric&appid={OWM_API_KEY}"
    )
    try:
        data = requests.get(url, timeout=12).json().get("list", [])
    except Exception:
        return []

    rows = []
    for entry in data:
        ts = entry.get("dt_txt")
        dt = _parse_time(ts.replace(" ", "T") + "Z") if ts else None
        rows.append({
            "time": ts,
            "time_dt": dt,
            "wind_speed": entry.get("wind", {}).get("speed", 0),
            "wind_deg": entry.get("wind", {}).get("deg", 0),
            "pressure": entry.get("main", {}).get("pressure", 0),
            "air_temp": entry.get("main", {}).get("temp", 0),
        })
    return rows


def fetch_stormglass(lat: float, lon: float, date: datetime.date) -> List[Dict[str, Any]]:
    """Optional marine fallback if key is configured."""
    if not STORMGLASS_API_KEY:
        return []

    start = datetime.datetime.combine(date, datetime.time(0, 0))
    end = start + datetime.timedelta(days=1)

    url = (
        "https://api.stormglass.io/v2/weather/point"
        f"?lat={lat}&lng={lon}"
        f"&params=waveHeight,wavePeriod,waterTemperature"
        f"&start={int(start.timestamp())}&end={int(end.timestamp())}"
        "&source=noaa"
    )
    try:
        data = requests.get(
            url,
            headers={"Authorization": STORMGLASS_API_KEY},
            timeout=12,
        ).json().get("hours", [])
    except Exception:
        return []

    rows = []
    for h in data:
        ts = h.get("time")
        dt = _parse_time(ts)
        rows.append({
            "time": ts,
            "time_dt": dt,
            "swell_height": h.get("waveHeight", {}).get("noaa", 0),
            "swell_period": h.get("wavePeriod", {}).get("noaa", 0),
            "sea_temp": h.get("waterTemperature", {}).get("noaa", 0),
        })
    return rows


def fetch_worldtides(lat: float, lon: float, date: datetime.date) -> Optional[List[Dict[str, Any]]]:
    """Optional tide data; falls back to Open-Meteo sea level if missing."""
    if not WORLDTIDES_API_KEY:
        return None
    url = (
        "https://www.worldtides.info/api"
        f"?extremes&date={date.isoformat()}&lat={lat}&lon={lon}&key={WORLDTIDES_API_KEY}"
    )
    try:
        data = requests.get(url, timeout=12).json().get("extremes", [])
    except Exception:
        return None
    return data or None


def merge_source_value(base_val, base_src, override_val, override_src, prefer="override"):
    """
    Return value + source. If override has a usable value, take it; otherwise keep base.
    """
    if override_val is None:
        return base_val, base_src
    if isinstance(override_val, (int, float)):
        if override_val == 0 and prefer != "zero-ok":
            return base_val, base_src
    return override_val, override_src


def fetch_hourly_bundle(lat: float, lon: float, date: datetime.date) -> List[Dict[str, Any]]:
    """
    Pull hourly weather + marine forecast for a single date.
    Combines Open-Meteo (baseline), OWM (wind/pressure), Stormglass (marine) when available.
    """
    om = fetch_open_meteo(lat, lon, date)
    om_weather = om.get("weather", {})
    om_marine = om.get("marine", {})
    times = om_weather.get("time", [])

    owm_rows = fetch_owm_forecast(lat, lon)
    sg_rows = fetch_stormglass(lat, lon, date)
    # WorldTides currently unused in aggregation; sea_level from Open-Meteo drives tide trend.
    _ = fetch_worldtides(lat, lon, date)

    rows = []
    for i, t in enumerate(times):
        t_dt = _parse_time(t)
        # Helper to convert m/s → km/h
        def mps_to_kmh(val):
            try:
                return float(val) * 3.6
            except Exception:
                return 0
        # Base from Open-Meteo
        wind_speed = mps_to_kmh(_safe_get(om_weather.get("wind_speed_10m", []), i, 0))
        wind_deg = _safe_get(om_weather.get("wind_direction_10m", []), i, 0)
        air_temp = _safe_get(om_weather.get("temperature_2m", []), i, 0)
        # Prefer swell-specific series; fallback to combined wave series
        swell_height = _safe_get(om_marine.get("swell_wave_height", []), i, None)
        if swell_height in (None, 0):
            swell_height = _safe_get(om_marine.get("wave_height", []), i, 0)
        swell_period = _safe_get(om_marine.get("swell_wave_period", []), i, None)
        if swell_period in (None, 0):
            swell_period = _safe_get(om_marine.get("wave_period", []), i, 0)
        swell_direction = _safe_get(om_marine.get("swell_wave_direction", []), i, None)
        if swell_direction in (None, 0):
            swell_direction = _safe_get(om_marine.get("wave_direction", []), i, 0)
        sea_temp = _safe_get(om_marine.get("sea_surface_temperature", []), i, 0)
        sea_level = _safe_get(om_marine.get("sea_level", []), i, 0)

        # Optional overrides
        owm_wind = _nearest(owm_rows, t_dt, "wind_speed") if t_dt else None
        owm_deg = _nearest(owm_rows, t_dt, "wind_deg") if t_dt else None
        owm_temp = _nearest(owm_rows, t_dt, "air_temp") if t_dt else None

        sg_height = _nearest(sg_rows, t_dt, "swell_height") if t_dt else None
        sg_period = _nearest(sg_rows, t_dt, "swell_period") if t_dt else None
        sg_temp = _nearest(sg_rows, t_dt, "sea_temp") if t_dt else None

        # Convert override wind to km/h before merging
        if owm_wind is not None:
            owm_wind = mps_to_kmh(owm_wind)

        wind_speed, wind_src = merge_source_value(wind_speed, "open-meteo", owm_wind, "owm")
        wind_deg, winddeg_src = merge_source_value(wind_deg, "open-meteo", owm_deg, "owm")
        air_temp, airtemp_src = merge_source_value(air_temp, "open-meteo", owm_temp, "owm")

        swell_height, swell_src = merge_source_value(swell_height, "open-meteo", sg_height, "stormglass")
        swell_period, swellp_src = merge_source_value(swell_period, "open-meteo", sg_period, "stormglass")
        sea_temp, seatemp_src = merge_source_value(sea_temp, "open-meteo", sg_temp, "stormglass")

        rows.append({
            "time": t,
            "time_dt": t_dt,
            "wind_speed": wind_speed,
            "wind_deg": wind_deg,
            "air_temp": air_temp,
            "swell_height": swell_height,
            "swell_period": swell_period,
            "swell_direction": swell_direction,
            "sea_temp": sea_temp,
            "sea_level": sea_level,
            "sources": {
                "wind": wind_src,
                "wind_deg": winddeg_src,
                "air_temp": airtemp_src,
                "swell": swell_src,
                "swell_period": swellp_src,
                "sea_temp": seatemp_src,
                "tide": "open-meteo",
            }
        })

    return rows


WINDOWS = [
    {"id": "dawn", "label": "Dawn", "start": 5, "end": 8},
    {"id": "morning", "label": "Morning", "start": 8, "end": 11},
    {"id": "afternoon", "label": "Afternoon", "start": 12, "end": 15},
    {"id": "evening", "label": "Evening", "start": 16, "end": 19},
]

# Time-of-day preferences (generic): dawn/evening favored for many surf species
TIME_PREF = {
    "dawn": {"species": 6, "generic": 4},
    "evening": {"species": 6, "generic": 4},
}

# Map coast facing to azimuth (rough)
FACING_AZIMUTH = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "ESE": 112,
    "SE": 135,
    "SSE": 157,
    "S": 180,
    "SW": 225,
    "W": 270,
    "WNW": 292,
    "NW": 315,
    "ENE": 67,
    "WSW": 247,
}


def tide_phase_for_window(rows: List[Dict[str, Any]], start_h: int, end_h: int) -> str:
    """Very rough tide phase using sea level trend across the window."""
    if not rows:
        return "Unknown"

    start = next((r for r in rows if _hour_of(r["time"]) >= start_h), rows[0])
    end = next((r for r in rows if _hour_of(r["time"]) >= end_h), rows[-1])

    start_lv = start.get("sea_level", 0)
    end_lv = end.get("sea_level", 0)
    delta = end_lv - start_lv

    if abs(delta) < 0.01:
        return "High"
    return "Rising" if delta > 0 else "Falling"


def aggregate_window(rows: List[Dict[str, Any]], start_h: int, end_h: int) -> Dict[str, Any]:
    window_rows = [r for r in rows if start_h <= _hour_of(r["time"]) < end_h]
    if not window_rows:
        return {
            "wind_speed": 0,
            "wind_deg": 0,
            "swell_height": 0,
            "swell_period": 0,
            "sea_temp": 0,
            "tide_phase": "Unknown",
            "count": 0,
            "sources": {},
        }

    def avg(field):
        vals = [r.get(field, 0) for r in window_rows]
        return sum(vals) / len(vals) if vals else 0

    def common_source(key):
        vals = [r.get("sources", {}).get(key) for r in window_rows if r.get("sources", {}).get(key)]
        if not vals:
            return None
        return max(set(vals), key=vals.count)

    return {
        "wind_speed": avg("wind_speed"),
        "wind_deg": avg("wind_deg"),
        "swell_height": avg("swell_height"),
        "swell_period": avg("swell_period"),
        "sea_temp": avg("sea_temp"),
        "tide_phase": tide_phase_for_window(window_rows, start_h, end_h),
        "count": len(window_rows),
        "sources": {
            "wind": common_source("wind"),
            "wind_deg": common_source("wind_deg"),
            "swell": common_source("swell"),
            "swell_period": common_source("swell_period"),
            "sea_temp": common_source("sea_temp"),
            "tide": "open-meteo",
        }
    }


def _angle_diff(a: float, b: float) -> float:
    """Smallest angle difference between two bearings."""
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff


def score_window(
    features: Dict[str, Any],
    target_species: List[str],
    coast_facing: str,
    window_id: str,
) -> Dict[str, Any]:
    species_scores = []
    species_results = []

    for sp in target_species:
        label = label_species(sp, {
            "wind_deg": features.get("wind_deg", 0),
            "sea_temp": features.get("sea_temp", 0),
            "swell_height": features.get("swell_height", 0),
            "tide_phase": features.get("tide_phase", "Unknown"),
        })

        label_score = {"Ideal": 30, "Good": 18, "Poor": 6}.get(label, 5)
        species_scores.append(label_score)
        species_results.append({
            "species": sp,
            "label": label,
            "score": label_score,
            "legal": SPECIES_LEGAL_NOTES.get(sp, ""),
        })

    wind_speed = features.get("wind_speed", 0)  # km/h
    # Penalties tuned for km/h (approx old m/s thresholds * 3.6)
    wind_penalty = max(0, wind_speed - 43) * 0.33

    swell_height = features.get("swell_height", 0)
    swell_penalty = max(0, swell_height - 2.5) * 5

    # Time-of-day bonus
    time_bonus = TIME_PREF.get(window_id, {}).get("generic", 0)
    # Species-specific time preference bonus
    for sp in target_species:
        pref = SPECIES_METADATA.get(sp, {}).get("time_pref", [])
        if window_id in pref:
            time_bonus += TIME_PREF.get(window_id, {}).get("species", 0)

    # Coast-facing wind bonus: reward offshore or light cross-shore
    wind_dir = features.get("wind_deg", 0)
    facing_deg = FACING_AZIMUTH.get(coast_facing, None)
    wind_bonus = 0
    if facing_deg is not None:
        offshore = (facing_deg + 180) % 360
        delta = _angle_diff(wind_dir, offshore)
        if delta <= 45 and wind_speed <= 54:
            wind_bonus = 6
        elif delta <= 90 and wind_speed <= 43:
            wind_bonus = 3

    base = sum(species_scores)
    score = max(0, base - wind_penalty - swell_penalty + time_bonus + wind_bonus)

    explanation = (
        f"Wind {wind_speed:.0f} km/h @ {features.get('wind_deg', 0):.0f}°, "
        f"Swell {swell_height:.1f} m / {features.get('swell_period', 0):.1f} s, "
        f"Tide {features.get('tide_phase', 'Unknown')}"
    )

    factors = []
    if wind_bonus > 0:
        factors.append("Offshore/cross wind bonus")
    if time_bonus > 0:
        factors.append(f"{window_id.title()} bite window bonus")
    if wind_penalty > 0:
        factors.append("High wind penalty")
    if swell_penalty > 0:
        factors.append("Heavy swell penalty")

    return {
        "score": round(score, 2),
        "per_species": species_results,
        "wind_speed": wind_speed,
        "wind_deg": features.get("wind_deg", 0),
        "swell_height": swell_height,
        "swell_period": features.get("swell_period", 0),
        "sea_temp": features.get("sea_temp", 0),
        "tide_phase": features.get("tide_phase", "Unknown"),
        "coast_facing": coast_facing,
        "sources": features.get("sources", {}),
        "explanation": explanation,
        "factors": factors,
    }


def plan_trip(region_id: str, area_id: str, species: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
    if not species:
        species = get_species_list()

    region, area = find_area(region_id, area_id)
    if not region or not area:
        raise PlanningError("Unknown region/area selection")

    today = datetime.date.today()
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if start < today:
        raise PlanningError("Only today and future dates are allowed")
    if end < start:
        raise PlanningError("End date must be on or after start date")

    span = (end - start).days + 1
    if span > MAX_PLANNING_DAYS:
        raise PlanningError(f"Limit date range to {MAX_PLANNING_DAYS} days or fewer")

    results = []
    source_tracker = set(["open-meteo"])

    if OWM_API_KEY:
        source_tracker.add("openweather")
    if STORMGLASS_API_KEY:
        source_tracker.add("stormglass")

    daily_series: Dict[str, List[Dict[str, Any]]] = {}

    for offset in range(span):
        day = start + datetime.timedelta(days=offset)
        rows = fetch_hourly_bundle(area["lat"], area["lon"], day)

        for window in WINDOWS:
            features = aggregate_window(rows, window["start"], window["end"])
            scored = score_window(features, species, area.get("coast_facing", ""), window["id"])
            day_key = day.isoformat()
            daily_series.setdefault(day_key, [])
            daily_series[day_key].append({
                "window_id": window["id"],
                "window": window["label"],
                "wind_speed": scored["wind_speed"],
                "swell_height": scored["swell_height"],
                "sea_temp": scored["sea_temp"],
                "tide_phase": scored["tide_phase"],
            })
            results.append({
                "date": day.isoformat(),
                "window": window["label"],
                "window_id": window["id"],
                **scored,
            })

    # Attach per-day series for mini charts
    for r in results:
        r["day_windows"] = daily_series.get(r["date"], [])

    sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

    return {
        "region": region,
        "area": area,
        "species": species,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "results": sorted_results,
        "sources": sorted(list(source_tracker)),
    }
