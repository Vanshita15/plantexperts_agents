from sqlalchemy.orm import Session
from .db_models import Soil, Stage, Water, Weather, Pest, Nutrient, Disease, Irrigation
import json
from datetime import datetime,timedelta

def save_soil(session, location, crop_name, model_name=None, prompt=None, output=None):
    # Normalize output: if dict -> stringify
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output 

    soil = Soil(
        location=location,
        crop_name=crop_name,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save
    )
    session.add(soil)
    session.commit()
    session.refresh(soil)
    return soil            # return the ORM instance so caller can use soil.id

def save_water(session: Session, location: str, crop_name: str, model_name: str = None, prompt: str = None, output: str = None):
    water = Water(
        location=location,
        crop_name=crop_name,
        model_name=model_name,
        prompt=prompt,
        output=output
    )
    session.add(water)
    session.commit()
    return water

def save_weather(session: Session, location: str, crop_name: str = None, model_name: str = None, prompt: str = None, output=None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output
    weather = Weather(
        location=location,
        crop_name=crop_name,
        model_name="open-meteo",
        prompt=prompt,
        output=output_to_save
    )
    session.add(weather)
    session.commit()
    return weather

def save_stage(session: Session, location: str, crop_name: str, sowing_date: str, soil_id: int, water_id: int, weather_id: int, model_name: str = None, prompt: str = None, output: str = None):
    from .db_models import Stage
    stage = Stage(
        location=location,
        crop_name=crop_name,
        sowing_date=sowing_date,
        soil_id=soil_id,
        water_id=water_id,
        weather_id=weather_id,
        model_name=model_name,
        prompt=prompt,
        output=output
    )
    session.add(stage)
    session.commit()
    return stage

def save_pest(session: Session,crop_name: str,crop_variety: str,location: str,sowing_date: str,stage_id: int,soil_id: int,water_id: int,weather_id: int,model_name: str = None,prompt: str = None,output=None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    pest = Pest(
        crop_name=crop_name,
        crop_variety=crop_variety,
        location=location,
        sowing_date=sowing_date,
        stage_id=stage_id,
        soil_id=soil_id,
        water_id=water_id,
        weather_id=weather_id,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save
    )
    session.add(pest)
    session.commit()
    session.refresh(pest)
    return pest

def save_nutrient(session: Session, crop_name: str, crop_variety: str, location: str, area: str, stage_id: int, soil_id: int, water_id: int,weather_id: int, model_name: str = None, prompt: str = None, output=None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    nutrient = Nutrient(
        crop_name=crop_name,
        crop_variety=crop_variety,
        location=location,
        area=str(area) if area is not None else None,
        stage_id=stage_id,
        soil_id=soil_id,
        water_id=water_id,
        weather_id=weather_id,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save,
    )
    session.add(nutrient)
    session.commit()
    session.refresh(nutrient)
    return nutrient

def save_disease(
    session: Session,
    crop_name: str,
    crop_variety: str,
    location: str,
    sowing_date: str,
    stage_id: int,
    soil_id: int,
    weather_id: int,
    model_name: str = None,
    prompt: str = None,
    output=None,
):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    disease = Disease(
        crop_name=crop_name,
        crop_variety=crop_variety,
        location=location,
        sowing_date=sowing_date,
        stage_id=stage_id,
        soil_id=soil_id,
        weather_id=weather_id,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save,
    )
    session.add(disease)
    session.commit()
    session.refresh(disease)
    return disease

def save_irrigation(
    session: Session,
    location: str,
    crop_name: str,
    sowing_date: str,
    area: str,
    stage_id: int,
    soil_id: int,
    water_id: int,
    weather_id: int,
    model_name: str = None,
    prompt: str = None,
    output=None,
):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    irrigation = Irrigation(
        location=location,
        crop_name=crop_name,
        sowing_date=sowing_date,
        area=str(area) if area is not None else None,
        stage_id=stage_id,
        soil_id=soil_id,
        water_id=water_id,
        weather_id=weather_id,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save,
    )
    session.add(irrigation)
    session.commit()
    session.refresh(irrigation)
    return irrigation

def get_latest_soil(session: Session, location: str, crop_name: str, max_age_hours: int = 24):
    """
    Get the latest soil report for a location/crop within max_age_hours.
    Returns None if not found or too old.
    """
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    
    result = session.query(Soil).filter(
        Soil.location == location,
        Soil.crop_name == crop_name,
        Soil.created_at >= cutoff
    ).order_by(Soil.created_at.desc()).first()
    
    return result


def get_latest_water(session: Session, location: str, crop_name: str, max_age_hours: int = 24):
    """
    Get the latest water report for a location/crop within max_age_hours.
    Returns None if not found or too old.
    """
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    result = session.query(Water).filter(
        Water.location == location,
        Water.crop_name == crop_name,
        Water.created_at >= cutoff
    ).order_by(Water.created_at.desc()).first()
    
    return result


def get_latest_weather(session: Session, location: str, crop_name: str = None, max_age_hours: int = 6):
    """
    Get the latest weather report for a location within max_age_hours.
    Weather data refreshes more frequently, so default is 6 hours.
    """
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    query = session.query(Weather).filter(
        Weather.location == location,
        Weather.created_at >= cutoff
    )
    
    if crop_name:
        query = query.filter(Weather.crop_name == crop_name)
    
    result = query.order_by(Weather.created_at.desc()).first()
    
    return result


def get_latest_stage(session: Session, location: str, crop_name: str, sowing_date: str, max_age_hours: int = 48):
    """
    Get the latest stage report for a specific crop planting.
    Matches location, crop, and sowing_date.
    """
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    
    result = session.query(Stage).filter(
        Stage.location == location,
        Stage.crop_name == crop_name,
        Stage.sowing_date == sowing_date,
        Stage.created_at >= cutoff
    ).order_by(Stage.created_at.desc()).first()
    
    return result


def clear_old_cache(session: Session, days_old: int = 7):
    """
    Utility function to clean up very old cached data.
    Can be run periodically to keep database clean.
    """
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    
    deleted_counts = {
        'soil': session.query(Soil).filter(Soil.created_at < cutoff).delete(),
        'water': session.query(Water).filter(Water.created_at < cutoff).delete(),
        'weather': session.query(Weather).filter(Weather.created_at < cutoff).delete(),
        'stage': session.query(Stage).filter(Stage.created_at < cutoff).delete(),
    }
    
    session.commit()
    return deleted_counts