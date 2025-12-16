import requests
from datetime import datetime, timedelta
import math
import json 
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# Open-Meteo variables
HOURLY_VARS = [
    "temperature_2m",
    "relativehumidity_2m",
    "dewpoint_2m",
    "precipitation",
    "windspeed_10m",
    "shortwave_radiation",
    "vapour_pressure_deficit"
]

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "shortwave_radiation_sum"
]

TZ_OFFSET_FALLBACK = {"Asia/Kolkata": 5.5, "UTC": 0.0}


def geocode_location(location: str):
    """Geocode a location using Open-Meteo API with a Nominatim fallback."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": location, "count": 1, "language": "en", "format": "json"}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "results" in data and len(data["results"]) > 0:
            res = data["results"][0]
            return {
                "name": res.get("name"),
                "latitude": res.get("latitude"),
                "longitude": res.get("longitude"),
                "country": res.get("country"),
                "admin1": res.get("admin1"),
                "timezone": res.get("timezone")
            }
    except Exception:
        pass

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        headers = {"User-Agent": "CropAdvisorySystem/1.0 (your@email.com)"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            res = data[0]
            addr = res.get("address", {}) or {}
            return {
                "name": res.get("display_name") or location,
                "latitude": float(res.get("lat")) if res.get("lat") is not None else None,
                "longitude": float(res.get("lon")) if res.get("lon") is not None else None,
                "country": addr.get("country", "Unknown"),
                "admin1": addr.get("state", ""),
                "timezone": "Asia/Kolkata",
            }
    except Exception:
        pass

    return None


def reverse_geocode(lat: float, lon: float):
    """
    Reverse geocode coordinates to get location name using Nominatim (OpenStreetMap).
    """
    try:
        # Use nominatim-style reverse geocoding
        url = "https://nominatim.openstreetmap.org/reverse"
        # Search for closest location to these coordinates
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 10,
            "addressdetails": 1
        }
        headers = {"User-Agent": "CropAdvisorySystem/1.0 (your@email.com)"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        display_name = data.get("display_name", "")
        return {
            "name": display_name,
            "latitude": lat,
            "longitude": lon,
            "country": data.get("address", {}).get("country", "Unknown"),
            "admin1": data.get("address", {}).get("state", ""),
            "timezone": "Asia/Kolkata"
        }
    except Exception:
        return {
            "name": f"Location ({lat:.4f}, {lon:.4f})",
            "latitude": lat,
            "longitude": lon,
            "country": "Unknown",
            "admin1": "",
            "timezone": "Asia/Kolkata"
        }


def fetch_open_meteo(lat, lon, timezone_name, days=7):
    start_date = datetime.utcnow().date()
    end_date = start_date + timedelta(days=days)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone_name,
        "hourly": ",".join(HOURLY_VARS),
        "daily": ",".join(DAILY_VARS),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def quality_check(raw_json):
    hourly = raw_json.get("hourly", {})
    daily = raw_json.get("daily", {})
    return {"hourly": hourly, "daily": daily}


def pick_closest_hourly_sample(hourly: dict):
    """
    Picks hourly value closest to current IST hour.
    """
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])

    if not times or not temps:
        return None

    now_hour = datetime.now().hour

    best_idx = 0
    best_diff = 999

    for i, tstr in enumerate(times):
        try:
            hour = int(tstr.split("T")[1].split(":")[0])
        except:
            continue

        diff = abs(hour - now_hour)
        if diff < best_diff:
            best_diff = diff
            best_idx = i

    return {
        "time": times[best_idx],
        "temp": temps[best_idx]
    }


def minimal_metrics_from_raw(raw):
    daily = raw.get("daily", {})
    hourly = raw.get("hourly", {})

    d_time = daily.get("time", [])
    d_tmin = daily.get("temperature_2m_min", [])
    d_tmax = daily.get("temperature_2m_max", [])
    d_precip = daily.get("precipitation_sum", [])
    d_swr = daily.get("shortwave_radiation_sum", [])

    precip7 = None
    if d_precip:
        precip7 = sum([p for p in d_precip if p is not None])

    h_time = hourly.get("time", [])
    h_rh = hourly.get("relativehumidity_2m", [])
    h_wind = hourly.get("windspeed_10m", [])
    h_swr = hourly.get("shortwave_radiation", [])

    def hourly_daily_means(h_times, h_vals):
        if not h_times or not h_vals:
            return {}
        day_map = {}
        for ts, v in zip(h_times, h_vals):
            if v is None:
                continue
            date = ts.split("T")[0]
            day_map.setdefault(date, []).append(v)
        return {d: (sum(vals)/len(vals)) for d, vals in day_map.items()}

    rh_mean_by_day = hourly_daily_means(h_time, h_rh)
    wind_mean_by_day = hourly_daily_means(h_time, h_wind)
    swr_mean_by_day = hourly_daily_means(h_time, h_swr)

    return {
        "daily_time": d_time,
        "daily_tmin": d_tmin,
        "daily_tmax": d_tmax,
        "daily_precip": d_precip,
        "daily_swr_sum": d_swr,
        "precip_7d_total": precip7,
        "rh_mean_by_day": rh_mean_by_day,
        "wind_mean_by_day": wind_mean_by_day,
        "swr_mean_by_day": swr_mean_by_day,
        "hourly": hourly
    }


def format_compact_table(geo, metrics, sample):
    lines = []
    loc = geo.get("name") or ""
    if geo.get("admin1"): loc += f", {geo.get('admin1')}"
    if geo.get("country"): loc += f", {geo.get('country')}"
    lines.append(f"Location: {loc}")
    lines.append(f"Coordinates: {geo.get('latitude'):.4f}, {geo.get('longitude'):.4f}")
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if sample and sample.get("temp") is not None:
        lines.append(f"Current temperature (latest): {sample['temp']:.1f} °C (as of {sample['time']})")
    if metrics.get("precip_7d_total") is not None:
        p7 = metrics["precip_7d_total"]
        avail = "High" if p7 >= 50 else ("Medium" if p7 >= 15 else "Low")
        lines.append(f"Rainfall (next 7 days total): {p7:.1f} mm → Water availability: {avail}")
    lines.append("")
    lines.append("7-day compact table (Date | Tmin/Tmax °C | Precip mm | MeanRH% | Wind m/s | Shortwave sum):")
    for d, tmin, tmax, p in zip(metrics.get("daily_time", []), metrics.get("daily_tmin", []), metrics.get("daily_tmax", []), metrics.get("daily_precip", [])):
        parts = [f"{d}"]
        if tmin is not None and tmax is not None:
            parts.append(f"{tmin:.1f}/{tmax:.1f}°C")
        else:
            parts.append("-")
        parts.append(f"{p:.1f}" if p is not None else "-")
        rh = metrics.get("rh_mean_by_day", {}).get(d)
        wind = metrics.get("wind_mean_by_day", {}).get(d)
        swr_sum = metrics.get("daily_swr_sum", [])
        swr_val = None
        if metrics.get("daily_swr_sum"):
            try:
                idx = metrics["daily_time"].index(d)
                swr_val = metrics.get("daily_swr_sum")[idx]
            except Exception:
                swr_val = None
        parts.append(f"{rh:.0f}%" if rh is not None else "-")
        parts.append(f"{wind:.1f}" if wind is not None else "-")
        parts.append(f"{swr_val:.1f}" if swr_val is not None else "-")
        lines.append(" - " + " | ".join(parts))
    conf = 0.80 if metrics.get("precip_7d_total") is not None else 0.60
    lines.append(f"\nConfidence: {conf:.2f}")
    return "\n".join(lines)


def weather_7day_compact(location: str = None, days: int = 7, latitude: float = None, longitude: float = None, crop_name: str = "", save_to_db: bool = True, model_name: str = "", run_id: int = None):
    """
    Fetch 7-day weather forecast using either:
    1. latitude/longitude (preferred if provided)
    2. location name (fallback)
    
    Args:
        location: Location name string
        days: Number of days to forecast
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    
    Returns:
        Plain-text compact 7-day weather table
    """
    geo = None
    
    # Priority 1: Use coordinates if provided
    if latitude is not None and longitude is not None:
        geo = reverse_geocode(latitude, longitude)
        print("reverse------------->",geo)
    # Priority 2: Fallback to location name
    elif location:
        geo = geocode_location(location)
        print("geocode------------->",geo)

    else:
        return "Error: No location or coordinates provided."
    
    if not geo:
        return f"Error: Could not determine location from {'coordinates' if latitude else 'name'}."
    
    raw = fetch_open_meteo(geo["latitude"], geo["longitude"], geo.get("timezone") or "Asia/Kolkata", days=days)
    cleaned = {"daily": raw.get("daily", {}), "hourly": raw.get("hourly", {})}
    metrics = minimal_metrics_from_raw(cleaned)
    sample = pick_closest_hourly_sample(cleaned.get("hourly", {}))
    report_text = format_compact_table(geo, metrics, sample)
    
    if save_to_db:
        try:
            from backend.init_db import SessionLocal
            from backend.data_store import save_weather
            output_str = report_text
            # output_str = (
            #     report_text['output'] 
            #     if isinstance(report_text, dict) and 'output' in report_text 
            #     else report_text
            # )

            if isinstance(output_str, dict):
                output_str = json.dumps(output_str, ensure_ascii=False)

            with SessionLocal() as session:
                obj = save_weather(
                    session,
                    location or geo.get("name", ""),
                    crop_name,
                    model_name,
                    "",
                    output_str,
                    run_id=run_id
                )
                print("-----------------------object>",obj)
                print("weather object id ----------------->",obj.id)
                return {
                "id": obj.id,
                "output": output_str
                } 
        except Exception as ex:
            print(f"[weather_7day_compact] Warning: Could not save to DB: {ex}")