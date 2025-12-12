"""
Helper functions to fetch agent data from session state or database before making new calls.
This prevents redundant API calls when agents depend on each other.
"""

from backend.init_db import SessionLocal
from backend.data_store import get_latest_soil, get_latest_water, get_latest_weather, get_latest_stage
from datetime import datetime, timedelta

def get_or_fetch_soil(farmer_input, session_state, model, latitude=None, longitude=None):
    """
    Get soil data from session state, database, or generate new.
    Returns dict with 'id' and 'output' keys.
    """
    # 1. Check session state
    if 'agent_outputs' in session_state and 'soil' in session_state['agent_outputs']:
        output = session_state['agent_outputs']['soil']
        if isinstance(output, dict):
            return output
        print("_____________________________________________________________check")
        return {'id': None, 'output': output}
    
    # 2. Check database
    try:
        with SessionLocal() as session:
            db_soil = get_latest_soil(
                session,
                location=farmer_input.location,
                crop_name=farmer_input.crop_name
            )
            if db_soil:
                return {'id': db_soil.id, 'output': db_soil.output}
    except Exception as e:
        print(f"[get_or_fetch_soil] DB lookup failed: {e}")
    
    # 3. Generate new
    from soil import run_soil_agent
    result = run_soil_agent(
        location=farmer_input.location,
        crop_name=farmer_input.crop_name,
        crop_variety=farmer_input.crop_variety,
        sowing_date=farmer_input.sowing_date,
        area=farmer_input.area,
        latitude=latitude,
        longitude=longitude,
        soil_type=farmer_input.soil_type or "",
        model=model
    )
    
    # Save to session state
    if 'agent_outputs' not in session_state:
        session_state['agent_outputs'] = {}
    session_state['agent_outputs']['soil'] = result
    
    return result


def get_or_fetch_water(farmer_input, session_state, model):
    """
    Get water data from session state, database, or generate new.
    Returns dict with 'id' and 'output' keys.
    """
    # 1. Check session state
    if 'agent_outputs' in session_state and 'water' in session_state['agent_outputs']:
        output = session_state['agent_outputs']['water']
        if isinstance(output, dict):
            return output
        return {'id': None, 'output': output}
    
    # 2. Check database
    try:
        with SessionLocal() as session:
            db_water = get_latest_water(
                session,
                location=farmer_input.location,
                crop_name=farmer_input.crop_name
            )
            if db_water:
                return {'id': db_water.id, 'output': db_water.output}
    except Exception as e:
        print(f"[get_or_fetch_water] DB lookup failed: {e}")
    
    # 3. Generate new
    from water import water_agent
    result = water_agent(farmer_input, model=model)
    
    # Save to session state
    if 'agent_outputs' not in session_state:
        session_state['agent_outputs'] = {}
    session_state['agent_outputs']['water'] = result
    
    return result


def get_or_fetch_weather(farmer_input, session_state, latitude=None, longitude=None, model_name: str = ""):
    """
    Get weather data from session state, database, or generate new.
    Returns dict with 'id' and 'output' keys.
    """
    # 1. Check session state
    if 'agent_outputs' in session_state and 'weather' in session_state['agent_outputs']:
        output = session_state['agent_outputs']['weather']
        if isinstance(output, dict):
            return output
        return {'id': None, 'output': output}
    
    # 2. Check database
    try:
        with SessionLocal() as session:
            db_weather = get_latest_weather(
                session,
                location=farmer_input.location,
                crop_name=farmer_input.crop_name
            )
            if db_weather:
                return {'id': db_weather.id, 'output': db_weather.output}
    except Exception as e:
        print(f"[get_or_fetch_weather] DB lookup failed: {e}")
    
    # 3. Generate new
    from weather import weather_7day_compact
    result = weather_7day_compact(
        location=farmer_input.location,
        latitude=latitude,
        longitude=longitude,
        days=7,
        crop_name=farmer_input.crop_name,
        save_to_db=True,
        model_name=model_name
    )
    
    # Save to session state
    if 'agent_outputs' not in session_state:
        session_state['agent_outputs'] = {}
    session_state['agent_outputs']['weather'] = result
    
    return result


def get_or_fetch_stage(farmer_input, session_state, model, latitude=None, longitude=None, soil_data=None, water_data=None, weather_data=None):
    """
    Get stage data from session state, database, or generate new.
    Returns dict with 'id' and 'output' keys.
    """
    # 1. Check session state
    if 'agent_outputs' in session_state and 'stage' in session_state['agent_outputs']:
        output = session_state['agent_outputs']['stage']
        if isinstance(output, dict) and 'output' in output:
            return output
        return {'id': None, 'output': output}
    
    # 2. Check database
    try:
        with SessionLocal() as session:
            db_stage = get_latest_stage(
                session,
                location=farmer_input.location,
                crop_name=farmer_input.crop_name,
                sowing_date=farmer_input.sowing_date
            )
            if db_stage:
                if 'agent_outputs' not in session_state:
                    session_state['agent_outputs'] = {}
                stage_obj = {'id': db_stage.id, 'output': db_stage.output}
                session_state['agent_outputs']['stage'] = stage_obj
                return stage_obj
    except Exception as e:
        print(f"[get_or_fetch_stage] DB lookup failed: {e}")
    
    # 3. Generate new - with dependency resolution
    from stage_agent import stage_generation
    
    # Ensure dependencies are fetched
    if soil_data is None:
        soil_data = get_or_fetch_soil(farmer_input, session_state, model, latitude, longitude)
    if water_data is None:
        water_data = get_or_fetch_water(farmer_input, session_state, model)
    if weather_data is None:
        weather_data = get_or_fetch_weather(farmer_input, session_state, latitude, longitude, model_name=model)
    
    result = stage_generation(
        farmer_input,
        model=model,
        latitude=latitude,
        longitude=longitude,
        soil_data=soil_data,
        water_data=water_data,
        weather_data=weather_data
    )
    
    # Save to session state
    if 'agent_outputs' not in session_state:
        session_state['agent_outputs'] = {}
    if isinstance(result, dict) and 'output' in result:
        session_state['agent_outputs']['stage'] = result
        return result
    stage_obj = {'id': None, 'output': result}
    session_state['agent_outputs']['stage'] = stage_obj
    return stage_obj


def extract_output_text(data):
    """
    Extract output text from various data formats.
    """
    if isinstance(data, dict):
        if 'output' in data:
            return data['output']
        elif 'data' in data:
            return str(data['data'])
        return str(data)
    return str(data)