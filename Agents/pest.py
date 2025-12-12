import os
import json
from typing import TypedDict, Optional, Literal, Dict, Any
from datetime import datetime, date
from dotenv import load_dotenv
from together import Together
from dataclasses import dataclass
from langgraph.graph import StateGraph
from soil import FarmerInput, run_soil_agent
from stage_agent import stage_generation
from water import water_agent
from weather import weather_7day_compact


load_dotenv()

Together_api_key = os.getenv("TOGETHER_API_KEY")
client = Together()
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"

# ensure FarmerInput uses YYYY-MM-DD sowing date when instantiating
user_input = FarmerInput(location="dhar", crop_name="wheat", sowing_date="2024-11-11")
Pest_system_prompt="""You are the PEST MANAGEMENT AGENT in a multi-agent agricultural system.

    INPUTS YOU WILL RECEIVE:
    - Crop Name & Variety
    - Current Growth Stage (name, dates, duration)
    - Weather Data (temperature, humidity, rainfall, wind)
    - Location

    YOUR TASK:
    Based on the crop, stage, weather conditions, and location, predict which pests are likely to attack and provide practical management advice. Use your agricultural knowledge to determine relevant pests for this specific combination.

    OUTPUT FORMAT:

    PEST RISK ASSESSMENT
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Crop: {crop_name}
    Stage: {stage_name}
    Duration: {start_date} to {end_date} ({X} days)
    Location: {location}

    WEATHER CONDITIONS:
    ├─ Temperature: {range}
    ├─ Humidity: {value}
    ├─ Rainfall: {value}
    └─ Wind Speed: {value}

    OVERALL PEST RISK LEVEL: [Low/Medium/High/Critical]

    LIKELY PESTS FOR THIS STAGE:
    [List 2-4 most relevant pests based on your knowledge of this crop, stage, and weather]

    For each pest, provide:
    - Pest name (common + scientific if known)
    - Risk level (Low/Medium/High/Critical)
    - Why this pest is likely (weather factors, stage vulnerability)
    - When risk is highest (specific days/conditions)

    SYMPTOMS TO MONITOR:
    [List observable symptoms farmers should watch for]
    [Include where to check (leaf/stem/root/grain)]

    MANAGEMENT ACTIONS:

    If symptoms detected:
    [Immediate steps farmers should take]

    Preventive measures:
    [Cultural/mechanical/biological controls - prioritize non-chemical]

    Chemical control (if needed):
    [Mention only if risk is high, with safe products and application guidelines]

    WEATHER-BASED REASONING:
    [Brief explanation of why these pests are likely given current weather conditions]
    
    ***Generate the output in a concise, easy-to-read format. 
    Avoid unnecessary details, but make sure all key information is clearly included.***
    
    CONFIDENCE LEVEL: {X.X/5}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    IMPORTANT GUIDELINES:
    ✅ Use your agricultural knowledge to identify relevant pests
    ✅ Consider crop type, growth stage, and local weather patterns
    ✅ Prioritize practical, farmer-friendly advice
    ✅ Suggest non-chemical methods first
    ✅ Be specific about symptoms and timing
    ✅ Keep language simple and actionable
    ❌ Don't mention diseases (separate agent handles that)
    ❌ Don't give fertilizer or irrigation advice
    ❌ Don't use placeholder text like {pest_name} - use actual pest names
    """

"""
Pest Agent - Simplified version
"""

# pest.py
import os
import re
from datetime import datetime, date
from dotenv import load_dotenv
from together import Together
from soil import FarmerInput

load_dotenv()
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"

Pest_system_prompt = """You are the PEST MANAGEMENT AGENT in a multi-agent agricultural system.

Inputs:
- Crop name & variety
- Current growth stage (name, start/end)
- Weather summary (temp, humidity, rainfall, wind)
- Location and water/soil summary (optional)

Task:
For each provided growth stage, list top 2-4 likely pests with:
- Pest name (common + scientific if possible)
- Risk level (Low/Medium/High/Critical)
- Why (weather/stage reasons)
- Symptoms (where to inspect)
- Non-chemical prevention (priority)
- Chemical control guidelines (only if risk is High; safe dosage/time)
Also provide an overall risk level and short weather-based alerts.
Keep language farmer-friendly and concise.
"""

def pest_agent(
    farmer_input: FarmerInput,
    stages_data: str = None,
    soil_data = None,
    water_data = None,
    weather_data = None,
    session_state: dict = None,
    latitude: float = None,
    longitude: float = None,
    custom_prompt: str = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    model: str = None,
    save_to_db: bool = True
) -> dict:
    """
    Pest agent:
    - farmer_input: FarmerInput dataclass (location, crop_name, crop_variety, sowing_date, area, latitude, longitude)
    - optional precomputed: stages_data, soil_data, water_data, weather_data
    - returns: {"output": text, "id": db_id or None} or {"error": "..."}
    """

    # helper functions expected in repo (DB-first fetch helpers)
    try:
        from agent_helper import (
            get_or_fetch_soil,
            get_or_fetch_water,
            get_or_fetch_weather,
            get_or_fetch_stage,
            extract_output_text
        )
    except Exception as e:
        return {"error": f"Missing agent_helper or helpers: {e}", "output": None, "id": None}

    chosen_model = model if model else MODEL_NAME
    system_prompt = custom_prompt if custom_prompt else (session_state.get("custom_prompts", {}).get("pest") if session_state else Pest_system_prompt)

    # 1) ensure dependent data exists (DB/session first) - only fetch if not provided
    if soil_data is None:
        soil_data = get_or_fetch_soil(farmer_input, session_state or {}, chosen_model, latitude, longitude)
    if water_data is None:
        water_data = get_or_fetch_water(farmer_input, session_state or {}, chosen_model)
    if weather_data is None:
        weather_data = get_or_fetch_weather(farmer_input, session_state or {}, latitude, longitude, model_name=chosen_model)
    if stages_data is None:
        stages_data = get_or_fetch_stage(
            farmer_input,
            session_state or {},
            chosen_model,
            latitude,
            longitude,
            soil_data if soil_data else None,
            water_data if water_data else None,
            weather_data if weather_data else None
        )

    # 2) normalize outputs -> plain text for prompt
    soil_text = extract_output_text(soil_data)
    water_text = extract_output_text(water_data)
    weather_text = extract_output_text(weather_data)
    stages_text = extract_output_text(stages_data)

    # 3) parse stages (robust regex)
    stage_pattern = r"Stage\s*\d+[:：]\s*([^\n\r]+).*?Start Date[:：]?\s*(\d{4}-\d{2}-\d{2}).*?End Date[:：]?\s*(\d{4}-\d{2}-\d{2})"
    matches = re.findall(stage_pattern, stages_text, flags=re.DOTALL | re.IGNORECASE)

    if not matches:
        # Try to detect CURRENT STAGE block as fallback
        if "CURRENT STAGE:" in stages_text:
            # Could parse current stage block differently; for now return informative result
            return {"error": "Could not parse stage blocks; found CURRENT STAGE. Provide full stage plan for multi-stage pest forecast.", "output": None, "id": None}
        return {"error": "Could not parse stages from stage agent output.", "output": None, "id": None}

    results = []
    for (stage_name, start_date, end_date) in matches:
        # safe parsing of dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            duration = (end_dt - start_dt).days + 1
        except Exception:
            start_dt = None
            end_dt = None
            duration = "unknown"

        # prepare concise weather snapshot (first lines)
        weather_snapshot = weather_text if isinstance(weather_text, str) else str(weather_text)
        # trim long weather blocks to first ~10 lines
        weather_lines = weather_snapshot.splitlines() if weather_snapshot else []
        weather_snip = "\n".join(weather_lines[:10])

        user_prompt = f"""
Crop: {farmer_input.crop_name} ({farmer_input.crop_variety})
Location: {farmer_input.location}
Stage: {stage_name}
Start: {start_date}
End: {end_date}
Duration (days): {duration}

Weather summary (short):
{weather_snip}

Soil summary (short):
{soil_text.splitlines()[:6] if soil_text else 'No soil data'}

Water summary (short):
{water_text.splitlines()[:6] if water_text else 'No water data'}

Task:
List top 2-4 likely pests for this crop-stage-weather combination. For each pest provide:
- Pest name (common ± scientific)
- Risk: Low/Medium/High/Critical
- Why it's likely (weather/stage reasons)
- Symptoms (where to check: leaf/stem/root)
- Preventive measures (non-chemical first)
- Chemical control (brief guidance ONLY if risk is High; safe dose/time)
Also give an overall risk level for this stage and short weather-based alerts. Keep it concise and farmer-friendly.
"""

        # call model
        try:
            if chosen_model == "gpt-4.1":
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    results.append(f"Error: OPENAI_API_KEY not set for stage {stage_name}")
                    continue
                openai_client = OpenAI(api_key=api_key)
                resp = openai_client.chat.completions.create(
                    model=chosen_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                text = resp.choices[0].message.content.strip()
            else:
                client = Together()
                resp = client.chat.completions.create(
                    model=chosen_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                text = resp.choices[0].message.content.strip()

            header = f"--- Pest Risk for {stage_name} ({start_date} to {end_date}) ---"
            results.append(header + "\n" + text)

        except Exception as e:
            results.append(f"Error generating pest assessment for stage {stage_name}: {e}")

    if not results:
        return {"error": "No stage assessments generated", "output": None, "id": None}

    final_text = "\n\n".join(results)

    # 4) Save to DB if requested (ensure save_pest exists)
    if save_to_db:
        try:
            from backend.init_db import SessionLocal
            from backend.data_store import save_pest
            with SessionLocal() as session:
                out = final_text if isinstance(final_text, str) else str(final_text)
                stage_id = stages_data.get('id') if isinstance(stages_data, dict) else None
                soil_id = soil_data.get('id') if isinstance(soil_data, dict) else None
                water_id = water_data.get('id') if isinstance(water_data, dict) else None
                weather_id = weather_data.get('id') if isinstance(weather_data, dict) else None
                pest_row = save_pest(
                    session=session,
                    crop_name=farmer_input.crop_name,
                    crop_variety=getattr(farmer_input, "crop_variety", None),
                    location=farmer_input.location,
                    sowing_date=getattr(farmer_input, "sowing_date", None),
                    stage_id=stage_id,
                    soil_id=soil_id,
                    water_id=water_id,
                    weather_id=weather_id,
                    model_name=chosen_model,
                    prompt=system_prompt,
                    output=out
                )
                return {"output": out, "id": pest_row.id}
        except Exception as db_ex:
            print("[pest_agent] DB save warning:", db_ex)
            return {"output": final_text, "id": None}

    return {"output": final_text, "id": None}
