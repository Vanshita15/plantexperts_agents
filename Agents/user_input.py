from dataclasses import dataclass
from typing import Optional, Literal, List, Dict, Any, Tuple

@dataclass
class FarmerInput:
    crop_name: str
    crop_variety: Optional[str] = ""
    location: str = ""
    sowing_date: Optional[str] = None  # "YYYY-MM-DD"
    area: Optional[float] = None

    previous_crop_sowed: Optional[str] = None
    soil_type: Optional[Literal["light","medium","heavy"]] = None
    irrigation_type: Optional[Literal["rainfed","borewell","canal","drip"]] = "rainfed"
    farming_method: Optional[Literal["traditional","organic","integrated","precision","natural","mixed"]] = None
    water_source: Optional[Literal["rainfed","borewell","canal","river","pond","tank","other"]] = None
    irrigation_method: Optional[Literal["drip","sprinkler","flood","furrow","basin","rainfed","other"]] = None
    last_fertilizers_used: Optional[List[str]] = None
    last_fertilizer_date: Optional[str] = None  # "YYYY-MM-DD"
    planting_method: Optional[Literal["direct_seeding","transplanting","dibbling","broadcasting","ridge_furrow","other"]] = None
    soil_texture: Optional[Literal["sandy","loamy","clayey","silty","black_cotton","unknown"]] = "unknown"
    drainage: Optional[Literal["good","medium","poor","unknown"]] = "unknown"
    waterlogging: Optional[Literal["never","sometimes","often","unknown"]] = "unknown"
    salinity_signs: Optional[Literal["none","suspected","confirmed","unknown"]] = "unknown"
    field_slope: Optional[Literal["flat","gentle","steep","unknown"]] = "unknown"
    hardpan_crusting: Optional[Literal["no","yes","unknown"]] = "unknown"
    irrigation_water_quality: Optional[Literal["good","salty","unknown"]] = "unknown"
    water_reliability: Optional[Literal["reliable","sometimes_short","often_short","unknown"]] = "unknown"
    last_season_pest_pressure: Optional[Literal["low","medium","high","unknown"]] = "unknown"
    last_season_disease_pressure: Optional[Literal["low","medium","high","unknown"]] = "unknown"
    custom_prompt: Optional[str] = None
    # Coordinates from map (primary source for location)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_coords: Optional[Any] = None  # Full polygon data if needed

# Utility to get FarmerInput from Streamlit session state
def get_farmer_input_from_session(st_session_state) -> FarmerInput:

    # Extract latitude and longitude from location_coords
    coords = st_session_state.get("location_coords", None)
    lat, lon = None, None
    if coords and len(coords) == 2:
        lat, lon = coords[0], coords[1]
    
    return FarmerInput(
        crop_name=st_session_state.get("crop_name", ""),
        crop_variety=st_session_state.get("crop_variety", ""),
        location=st_session_state.get("location_name", ""),
        sowing_date=st_session_state.get("sowing_date", None),
        area=st_session_state.get("area", None),

        previous_crop_sowed=st_session_state.get("previous_crop_sowed", None),
        soil_type=st_session_state.get("soil_type", None),
        irrigation_type=st_session_state.get("irrigation_type", "rainfed"),
        farming_method=st_session_state.get("farming_method", None),
        water_source=st_session_state.get("water_source", None),
        irrigation_method=st_session_state.get("irrigation_method", None),
        last_fertilizers_used=st_session_state.get("last_fertilizers_used", None),
        last_fertilizer_date=st_session_state.get("last_fertilizer_date", None),
        planting_method=st_session_state.get("planting_method", None),
        soil_texture=st_session_state.get("soil_texture", "unknown"),
        drainage=st_session_state.get("drainage", "unknown"),
        waterlogging=st_session_state.get("waterlogging", "unknown"),
        salinity_signs=st_session_state.get("salinity_signs", "unknown"),
        field_slope=st_session_state.get("field_slope", "unknown"),
        hardpan_crusting=st_session_state.get("hardpan_crusting", "unknown"),
        irrigation_water_quality=st_session_state.get("irrigation_water_quality", "unknown"),
        water_reliability=st_session_state.get("water_reliability", "unknown"),
        last_season_pest_pressure=st_session_state.get("last_season_pest_pressure", "unknown"),
        last_season_disease_pressure=st_session_state.get("last_season_disease_pressure", "unknown"),
        custom_prompt=st_session_state.get("custom_prompt", None),
        latitude=lat,
        longitude=lon,
        map_coords=coords
    )