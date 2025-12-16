from sqlalchemy.orm import Session
from .db_models import (
    AgentRun,
    Soil,
    Stage,
    Water,
    Weather,
    Pest,
    Nutrient,
    Disease,
    Irrigation,
    Merge,
    PromptEvent,
    PromptPreference,
)
import json
from datetime import datetime,timedelta


def create_agent_run(
    session: Session,
    triggered_agent_id: str,
    location: str = None,
    crop_name: str = None,
    crop_variety: str = None,
    sowing_date: str = None,
    model_name: str = None,
):
    run = AgentRun(
        triggered_agent_id=triggered_agent_id,
        location=location,
        crop_name=crop_name,
        crop_variety=crop_variety,
        sowing_date=sowing_date,
        model_name=model_name,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def list_agent_runs(session: Session, limit: int = 50):
    q = session.query(AgentRun).order_by(AgentRun.created_at.desc())
    if limit is None:
        return q.all()
    return q.limit(limit).all()


def get_run_snapshot(session: Session, run_id: int):
    run = session.query(AgentRun).filter(AgentRun.id == run_id).first()
    if run is None:
        return None

    soil_rows = session.query(Soil).filter(Soil.run_id == run_id).order_by(Soil.created_at.asc()).all()
    water_rows = session.query(Water).filter(Water.run_id == run_id).order_by(Water.created_at.asc()).all()
    weather_rows = session.query(Weather).filter(Weather.run_id == run_id).order_by(Weather.created_at.asc()).all()
    stage_rows = session.query(Stage).filter(Stage.run_id == run_id).order_by(Stage.created_at.asc()).all()
    nutrient_rows = session.query(Nutrient).filter(Nutrient.run_id == run_id).order_by(Nutrient.created_at.asc()).all()
    pest_rows = session.query(Pest).filter(Pest.run_id == run_id).order_by(Pest.created_at.asc()).all()
    disease_rows = session.query(Disease).filter(Disease.run_id == run_id).order_by(Disease.created_at.asc()).all()
    irrigation_rows = session.query(Irrigation).filter(Irrigation.run_id == run_id).order_by(Irrigation.created_at.asc()).all()
    merge_rows = session.query(Merge).filter(Merge.run_id == run_id).order_by(Merge.created_at.asc()).all()

    linked_soil = []
    linked_water = []
    linked_weather = []

    # Include dependency rows referenced by stage/nutrient/pest/disease/irrigation even if they belong to older runs.
    stage_soil_ids = [r.soil_id for r in stage_rows if getattr(r, 'soil_id', None)]
    stage_water_ids = [r.water_id for r in stage_rows if getattr(r, 'water_id', None)]
    stage_weather_ids = [r.weather_id for r in stage_rows if getattr(r, 'weather_id', None)]

    if stage_soil_ids:
        linked_soil = session.query(Soil).filter(Soil.id.in_(list(set(stage_soil_ids)))).all()
    if stage_water_ids:
        linked_water = session.query(Water).filter(Water.id.in_(list(set(stage_water_ids)))).all()
    if stage_weather_ids:
        linked_weather = session.query(Weather).filter(Weather.id.in_(list(set(stage_weather_ids)))).all()

    return {
        'run': run,
        'soil': soil_rows,
        'water': water_rows,
        'weather': weather_rows,
        'stage': stage_rows,
        'nutrient': nutrient_rows,
        'pest': pest_rows,
        'disease': disease_rows,
        'irrigation': irrigation_rows,
        'merge': merge_rows,
        'linked': {
            'soil': linked_soil,
            'water': linked_water,
            'weather': linked_weather,
        },
    }


def save_prompt_event(
    session: Session,
    agent_id: str,
    prompt_source: str,
    event_type: str,
    prompt: str,
):
    evt = PromptEvent(
        agent_id=agent_id,
        prompt_source=prompt_source,
        event_type=event_type,
        prompt=prompt,
    )
    session.add(evt)
    session.commit()
    session.refresh(evt)
    return evt


def upsert_prompt_preference(
    session: Session,
    agent_id: str,
    selected_source: str,
    selected_prompt: str = None,
):
    pref = session.query(PromptPreference).filter(PromptPreference.agent_id == agent_id).first()
    if pref is None:
        pref = PromptPreference(
            agent_id=agent_id,
            selected_source=selected_source,
            selected_prompt=selected_prompt,
        )
        session.add(pref)
    else:
        pref.selected_source = selected_source
        pref.selected_prompt = selected_prompt
    session.commit()
    session.refresh(pref)
    return pref


def get_prompt_preference(session: Session, agent_id: str):
    return session.query(PromptPreference).filter(PromptPreference.agent_id == agent_id).first()


def get_recent_prompt_events(session: Session, agent_id: str, limit: int = 5):
    return (
        session.query(PromptEvent)
        .filter(PromptEvent.agent_id == agent_id)
        .order_by(PromptEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def save_soil(session, location, crop_name, model_name=None, prompt=None, output=None, run_id: int = None):
    # Normalize output: if dict -> stringify
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output 

    soil = Soil(
        run_id=run_id,
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


def save_water(session: Session, location: str, crop_name: str, model_name: str = None, prompt: str = None, output: str = None, run_id: int = None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output
    water = Water(
        run_id=run_id,
        location=location,
        crop_name=crop_name,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save
    )
    session.add(water)
    session.commit()
    return water


def save_weather(session: Session, location: str, crop_name: str = None, model_name: str = None, prompt: str = None, output=None, run_id: int = None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output
    weather = Weather(
        run_id=run_id,
        location=location,
        crop_name=crop_name,
        model_name="open-meteo",
        prompt=prompt,
        output=output_to_save
    )
    session.add(weather)
    session.commit()
    return weather


def save_stage(session: Session, location: str, crop_name: str, sowing_date: str, soil_id: int, water_id: int, weather_id: int, model_name: str = None, prompt: str = None, output: str = None, run_id: int = None):
    from .db_models import Stage
    stage = Stage(
        run_id=run_id,
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


def save_pest(session: Session,crop_name: str,crop_variety: str,location: str,sowing_date: str,stage_id: int,soil_id: int,water_id: int,weather_id: int,model_name: str = None,prompt: str = None,output=None, run_id: int = None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    pest = Pest(
        run_id=run_id,
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


def save_nutrient(session: Session, crop_name: str, crop_variety: str, location: str, area: str, stage_id: int, soil_id: int, water_id: int,weather_id: int, model_name: str = None, prompt: str = None, output=None, run_id: int = None):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    nutrient = Nutrient(
        run_id=run_id,
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
    run_id: int = None,
):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    disease = Disease(
        run_id=run_id,
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
    run_id: int = None,
):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    irrigation = Irrigation(
        run_id=run_id,
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


def save_merge(
    session: Session,
    soil: str = None,
    nutrient: str = None,
    irrigation: str = None,
    pest: str = None,
    disease: str = None,
    weather: str = None,
    stage: str = None,
    model_name: str = None,
    prompt: str = None,
    output=None,
    run_id: int = None,
):
    if isinstance(output, dict):
        output_to_save = json.dumps(output, ensure_ascii=False)
    else:
        output_to_save = output

    merge = Merge(
        run_id=run_id,
        soil=soil,
        nutrient=nutrient,
        irrigation=irrigation,
        pest=pest,
        disease=disease,
        weather=weather,
        stage=stage,
        model_name=model_name,
        prompt=prompt,
        output=output_to_save,
    )
    session.add(merge)
    session.commit()
    session.refresh(merge)
    return merge


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