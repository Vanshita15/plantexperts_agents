import os
import json
from datetime import datetime, date
from dotenv import load_dotenv
from together import Together
from dataclasses import dataclass
from openai import OpenAI
from llm_router import call_llm

from langgraph.graph import StateGraph
from soil import FarmerInput
from soil import run_soil_agent
from water import water_agent
from weather import weather_7day_compact
import re
from datetime import datetime, date
import streamlit as st

load_dotenv()

MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"
# ensure FarmerInput uses YYYY-MM-DD sowing date when instantiating
user_input = FarmerInput(location="dhar", crop_name="wheat", sowing_date="2024-11-11")
today_date= date.today()

# ---------- FIXED: use {placeholders} so .format fills them ----------
stage_system_prompt = """
    You are the STAGE-PLANNER AGENT for agricultural crop planning.

    INPUTS:
    - Location: {location}
    - Crop: {crop}
    - Sowing Date: {sowing_date}
    - Soil Report: {soil_report}
    - Water Report: {water_report}
    - Weather Report: {weather_report}

    YOUR TASK:
    Based on the crop type, determine scientifically accurate growth stages with realistic durations.

    STAGE PLANNING RULES:
    1. Use crop-specific phenological stages (NOT generic names)
    2. Calculate stage durations based on:
    - Temperature (Growing Degree Days if possible)
    - Soil fertility (NPK levels affect growth rate)
    - Water availability (rainfall + irrigation)
    - Weather patterns (cold/heat stress)

    3. For ANY crop, use your agricultural knowledge to determine the correct growth stages and typical durations based on the provided crop name and variety. Do not use hardcoded stages—output the real stages for the given crop.

    4. Adjust durations based on:
    - Cold weather → slower growth (add 10-20% days)
    - Hot weather → faster growth (reduce 5-10% days)
    - Low nitrogen → slower vegetative growth
    - Water stress → delayed flowering

    RULES:
    Use crop-specific stage names
    Calculate realistic durations
    Consider all provided data (soil, water, weather)
    Output ONLY the format above
    NO duplicates
    NO irrigation/fertilizer advice here
    NO extra explanations

    OUTPUT FORMAT (STRICT - NO DUPLICATES):

    Location: {location}
    Crop: {crop}
    Sowing Date: {sowing_date}

    GROWTH STAGE PLAN:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Stage 1: [Stage Name]
    ├─ Start Date: YYYY-MM-DD
    ├─ End Date: YYYY-MM-DD
    ├─ Duration: X days
    ├─ Confidence: 0.XX
    └─ Key Factors: [Brief note on weather/soil impact]

    Stage 2: [Stage Name]
    ├─ Start Date: YYYY-MM-DD
    ├─ End Date: YYYY-MM-DD
    ├─ Duration: X days
    ├─ Confidence: 0.XX
    └─ Key Factors: [Brief note]
 
    [Continue for all stages...]

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    TOTAL CROP DURATION: XXX days
    EXPECTED HARVEST DATE: YYYY-MM-DD
    OVERALL CONFIDENCE: 0.XX

    CURRENT STAGE:
    - Stage Name: [Current Stage Name]
    - Start Date: YYYY-MM-DD
    - End Date: YYYY-MM-DD
    - Days Completed: X/Y days
    - Progress: XX%
    - Days Remaining: X days
    - Explanation: [Brief explanation based on sowing date and stage duration]
    
    CRITICAL ASSUMPTIONS:
    - [List any assumptions made]

    CRITICAL ALERTS (if any):
    - [Temperature stress periods]
    - [Water deficit periods]
    - [Nutrient deficiency impact]

    """

def stage_planner_agent(
    location: str,
    crop: str,
    sowing_date: str,
    soil_report: str,
    water_report: str,
    weather_report: str,
    model_name: str = None,
    temperature: float = 0.1,
    max_tokens: int = 1200,
    custom_prompt: str = None,
    model: str = None,
    save_to_db: bool = True  # This will now work!
) -> str:
    """Build prompt correctly and call Together/Qwen, return plain-text model output."""
    if model_name is None:
        model_name = MODEL_NAME

    # ensure sowing_date in YYYY-MM-DD
    sd = sowing_date
    try:
        if "/" in sd:
            dt = datetime.strptime(sd, "%d/%m/%Y")
            sd = dt.strftime("%Y-%m-%d")
        else:
            datetime.strptime(sd, "%Y-%m-%d")
    except Exception:
        sd = sowing_date

    # escape braces in inputs
    def esc(s: str) -> str:
        return (s or "").replace("{", "{{").replace("}", "}}")

    # Use custom_prompt if provided, else default
    system_prompt = custom_prompt if custom_prompt else stage_system_prompt
    chosen_model = model if model else llama_model_name
    print("---------------------------------chosen model-----------------",chosen_model)

    # Format the prompt with actual data
    user_message = system_prompt.format(
        location=esc(location),
        crop=esc(crop),
        sowing_date=esc(sd),
        soil_report=esc(soil_report),
        water_report=esc(water_report),
        weather_report=esc(weather_report),
        today_date=esc(str(today_date)),
    )
    try:
        text = call_llm(
            model=chosen_model,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return text, system_prompt
    except Exception as e:
        return f"Error calling StagePlanner model: {e}"

def parse_stage_plan_and_current_stage(report_text, sowing_date_str):
    """
    Find current stage from LLM stage plan using dates + sowing date.
    Handles:
    - Sowing date in future  -> crop not yet sown
    - Today after last stage -> crop already harvested
    """
    

    # ---------- Parse sowing date safely ----------
    sowing_date = None
    if sowing_date_str:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                sowing_date = datetime.strptime(sowing_date_str, fmt).date()
                break
            except Exception:
                continue

    # ---------- Extract all stages with dates ----------
    pattern = (
        r"Stage\s*\d+[:：]\s*(.+?)\s*[\n\r]+"  # Accepts : or ：, flexible whitespace
        r".*?Start[\s_-]*Date[:：]?\s*(\d{4}-\d{2}-\d{2})[\s\n\r]*"
        r".*?End[\s_-]*Date[:：]?\s*(\d{4}-\d{2}-\d{2})"
    )
    matches = re.findall(pattern, report_text, re.DOTALL)

    if not matches:
        return "\n\nCURRENT STAGE: Could not parse stages from report.\n"

    today = date.today()

    # ---------- Check: sowing in future ----------
    if sowing_date and sowing_date > today:
        return (
            f"\n\nCURRENT STAGE: Crop not yet sown. "
            f"(Sowing date is in future: {sowing_date.isoformat()}).\n"
        )

    # ---------- Build structured stage list ----------
    stages = []
    for stage_name, start_date_str, end_date_str in matches:
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        stages.append((stage_name.strip(), start, end))

    # Sort just in case LLM ne order ulta kar diya ho
    stages.sort(key=lambda x: x[1])

    first_stage_start = stages[0][1]
    last_stage_end = stages[-1][2]

    # ---------- Check: today after last stage (already harvested) ----------
    if today > last_stage_end:
        return (
            f"\n\nCURRENT STAGE: Crop has already been harvested. "
            f"(Last stage ended on {last_stage_end.isoformat()}).\n"
        )

    # Optional: before first stage but sowing ho chuki hai / data mismatch
    if today < first_stage_start:
        return (
            f"\n\nCURRENT STAGE: Crop growth not yet started. "
            f"(First stage starts on {first_stage_start.isoformat()}).\n"
        )

    # ---------- Find stage in which 'today' falls ----------
    for stage_name, start, end in stages:
        if start <= today <= end:
            total_days = (end - start).days + 1
            completed_days = (today - start).days + 1
            remaining_days = (end - today).days
            progress_pct = (completed_days / total_days) * 100

            result = "\n\nCURRENT STAGE:\n"
            result += f"- Stage Name: {stage_name}\n"
            result += f"- Start Date: {start.isoformat()}\n"
            result += f"- End Date: {end.isoformat()}\n"
            result += f"- Days Completed: {completed_days}/{total_days} days\n"
            result += f"- Progress: {progress_pct:.1f}%\n"
            result += f"- Days Remaining: {remaining_days} days\n"
            result += (
                f"- Explanation: Crop is currently in '{stage_name}' stage "
                f"(Today: {today.isoformat()}).\n"
            )
            return result

    # Fallback: dates parse ho gaye but today kisi bhi range me nahi aaya
    return "\n\nCURRENT STAGE: Could not determine stage from date ranges.\n"

def stage_generation(
    farmer_input, 
    model, 
    save_to_db=True, 
    temperature: float = None,
    max_tokens: int = None,
    latitude: float = None, 
    longitude: float = None, 
    soil_data=None, 
    water_data=None, 
    weather_data=None,
    session_state=None,  # NEW: pass session_state
    run_id: int = None
    ):  

    system_prompt = None
    try:
        if session_state and isinstance(session_state, dict):
            # if you stored prompts in session_state.custom_prompts
            system_prompt = session_state.get("custom_prompts", {}).get("stage")
    except Exception:
        system_prompt = None
    if not system_prompt:
        system_prompt = stage_system_prompt

    """
    Generate crop growth stage plan.
    Uses cached data from session_state or database before making new API calls.
    """
    from agent_helper import (
        get_or_fetch_soil, 
        get_or_fetch_water, 
        get_or_fetch_weather,
        extract_output_text
    )
    import re
    
    # Fetch dependencies intelligently (checks session/DB first)
    dependencies = {
        'soil': (soil_data, get_or_fetch_soil, [farmer_input, session_state or {}, model, latitude, longitude, run_id]),
        'water': (water_data, get_or_fetch_water, [farmer_input, session_state or {}, model, run_id]),
        'weather': (weather_data, get_or_fetch_weather, [farmer_input, session_state or {}, latitude, longitude, "", run_id])
    }
    
    for name, (data, func, args) in dependencies.items():
        if data is None:
            data = func(*args)
        dependencies[name] = data
    
    soil_data, water_data, weather_data = dependencies.values()

    # Convert to strings
    soil_text = extract_output_text(soil_data)
    water_text = extract_output_text(water_data)
    weather_text = extract_output_text(weather_data)

    temp_to_use = temperature if temperature is not None else 0.1
    max_tokens_to_use = max_tokens if max_tokens is not None else 1200

    # Generate stage plan from LLM
    stages_data = stage_planner_agent(
        location=farmer_input.location,
        crop=farmer_input.crop_name,
        sowing_date=farmer_input.sowing_date,
        soil_report=soil_text,
        water_report=water_text,
        weather_report=weather_text,
        temperature=temp_to_use,
        max_tokens=max_tokens_to_use,
        model=model,
        save_to_db=False,  # We'll save at the end
        custom_prompt=system_prompt
    )

    # If stage_planner_agent returned tuple (text, system_prompt) normalize it:
    if isinstance(stages_data, tuple) and len(stages_data) >= 1:
        # assume first item is text
        stages_data = stages_data[0]
        
    # Remove LLM's CURRENT STAGE section (if exists)
    stages_data = re.sub(
        r"CURRENT STAGE:.*?(?=CRITICAL ASSUMPTIONS:|CRITICAL ALERTS:|$)", 
        "", 
        stages_data, 
        flags=re.DOTALL
    )

    # Calculate accurate current stage using Python
    py_current = parse_stage_plan_and_current_stage(stages_data, farmer_input.sowing_date)
    
    # Combine LLM output + Python current stage
    final_report = stages_data + py_current
    
    # Save to database if requested
    if save_to_db:
        try:
            from backend.init_db import SessionLocal
            from backend.data_store import save_stage
            with SessionLocal() as db_session:
                ids = {
                    'soil': soil_data.get('id') if isinstance(soil_data, dict) else None,
                    'water': water_data.get('id') if isinstance(water_data, dict) else None,
                    'weather': weather_data.get('id') if isinstance(weather_data, dict) else None
                }
                
                print('[DEBUG] soil_id:', ids['soil'], type(ids['soil']))
                print('[DEBUG] water_id:', ids['water'], type(ids['water']))
                print('[DEBUG] weather_id:', ids['weather'], type(ids['weather']))
                
                obj = save_stage(
                    db_session,
                    location=farmer_input.location,
                    crop_name=getattr(farmer_input, 'crop_name', None),
                    sowing_date=getattr(farmer_input, 'sowing_date', None),
                    soil_id=ids['soil'],
                    water_id=ids['water'],
                    weather_id=ids['weather'],
                    model_name=model,
                    prompt=system_prompt,
                    output=final_report,
                    run_id=run_id
                )
                
                # Return with ID for future reference
                return {'id': obj.id, 'output': final_report}
        except Exception as ex:
            print(f'[stage_generation] Warning: Could not save to DB: {ex}')
    
    return final_report