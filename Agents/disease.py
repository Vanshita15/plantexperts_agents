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
import re
from weather import weather_7day_compact
from llm_router import call_llm


load_dotenv()

Together_api_key = os.getenv("TOGETHER_API_KEY")
client = Together()
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo" 

Disease_system_prompt = """
    You are the DISEASE MANAGEMENT AGENT in a multi-agent agricultural system.

    INPUTS YOU WILL RECEIVE:
    - Crop Name & Variety
    - Current Growth Stage (name, dates, duration)
    - Weather Data (temperature, humidity, rainfall, wind)
    - Soil Data (pH, nutrients, texture)
    - Location

    YOUR TASK:
    Based on the crop, stage, weather, soil conditions, and location, predict which diseases are likely to occur and provide practical management advice. Use your agricultural knowledge to determine relevant diseases for this specific combination.

    OUTPUT FORMAT:

    DISEASE RISK ASSESSMENT
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

    SOIL CONDITIONS:
    ├─ pH: {value}
    ├─ Texture: {type}
    └─ Organic Matter: {value}

    OVERALL DISEASE RISK LEVEL: [Low/Medium/High/Critical]

    LIKELY DISEASES FOR THIS STAGE:
    [List 2-4 most relevant diseases based on your knowledge of this crop, stage, weather, and soil]

    For each disease, provide:
    - Disease name (common + scientific if known)
    - Type (Fungal/Bacterial/Viral/other)
    - Risk level (Low/Medium/High/Critical)
    - Why this disease is likely (weather + soil factors)
    - How it spreads (wind/rain/insects/soil-borne)
    - When risk is highest

    SYMPTOMS TO MONITOR:
    [List observable symptoms farmers should watch for]
    [Include where symptoms appear and disease progression]

    MANAGEMENT ACTIONS:

    If symptoms detected:
    [Immediate steps farmers should take]

    Preventive measures:
    [Cultural practices, sanitation, resistant varieties]
    [Biological controls if applicable]

    Chemical control (if needed):
    [Mention specific fungicides/bact   ericides only if risk is high]
    [Include application timing and safety intervals]

    WEATHER & SOIL REASONING:
    [explanation of why these diseases are likely given current conditions]

    ***Generate the output in a concise, easy-to-read format. 
        Avoid unnecessary details, but make sure all key information is clearly included.***
    CONFIDENCE LEVEL: {X.X/5}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    IMPORTANT GUIDELINES:
    ✅ Use your agricultural knowledge to identify relevant diseases
    ✅ Consider crop type, growth stage, weather patterns, and soil conditions
    ✅ Prioritize practical, farmer-friendly advice
    ✅ Suggest preventive and cultural methods first
    ✅ Be specific about symptoms and management
    ✅ Consider economic thresholds for chemical intervention
    ✅ Keep language simple and actionable
    ❌ Don't mention pests (separate agent handles that)
    ❌ Don't give fertilizer or irrigation advice
    ❌ Don't use placeholder text - use actual disease names based on your knowledge
    """


"""
Disease Agent - Simplified version
"""

def disease_agent(
    farmer_input: FarmerInput = None,
    crop: str = None,
    crop_variety: str = None,
    location: str = None,
    sowing_date: str = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    custom_prompt: str = None,
    model: str = None,
    session_state=None,
    latitude: float = None,
    longitude: float = None,
    soil_text: str = None,
    weather_text: str = None,
    stages_text: str = None,
    run_id: int = None
) -> str:
    """
    Generate stage-specific disease risk assessment.
    Model will use its knowledge to identify relevant diseases.
    """
    
    system_prompt = custom_prompt if custom_prompt else Disease_system_prompt

    from agent_helper import get_or_fetch_soil, get_or_fetch_weather, get_or_fetch_stage, extract_output_text

    # Backward compatibility: allow calling with crop/crop_variety/location/sowing_date
    if farmer_input is None:
        farmer_input = FarmerInput(
            location=location,
            crop_name=crop,
            crop_variety=crop_variety,
            sowing_date=sowing_date,
        )

    crop = getattr(farmer_input, 'crop_name', crop)
    crop_variety = getattr(farmer_input, 'crop_variety', crop_variety)
    location = getattr(farmer_input, 'location', location)
    sowing_date = getattr(farmer_input, 'sowing_date', sowing_date)

    # Fetch dependencies intelligently (session/DB first)
    soil_data = None
    weather_data = None
    stage_data = None
    if soil_text is None:
        soil_data = get_or_fetch_soil(farmer_input, session_state or {}, model, latitude, longitude, run_id=run_id)
        soil_text = extract_output_text(soil_data)
    if weather_text is None:
        weather_data = get_or_fetch_weather(farmer_input, session_state or {}, latitude, longitude, model_name=model or MODEL_NAME, run_id=run_id)
        weather_text = extract_output_text(weather_data)
    if stages_text is None:
        stage_data = get_or_fetch_stage(farmer_input, session_state or {}, model, latitude, longitude, run_id=run_id)
        stages_text = extract_output_text(stage_data)

    stage_report = stages_text
    # Robust regex for CURRENT STAGE parsing
    # Parse all stages from stage_report (shared logic with pest_agent)
    import re
    stage_pattern = r"Stage \d+: ([^\n]+)\n[\s\S]*?Start Date: (\d{4}-\d{2}-\d{2})\n[\s\S]*?End Date: (\d{4}-\d{2}-\d{2})"
    stages = re.findall(stage_pattern, stage_report)
    if not stages:
        if "CURRENT STAGE: Crop has already been harvested" in stage_report:
            return "No active stage: Crop has already been harvested."
        print("\n[DEBUG] Stage report output:\n", stage_report)
        return "Error: Could not parse stages from stage agent output."

    # weather_text and soil_text are already resolved above

    # Forecast disease risk for all future stages
    today = __import__('datetime').date.today()
    results = []
    for stage_name, stage_start, stage_end in stages:
        stage_start_date = __import__('datetime').datetime.strptime(stage_start, "%Y-%m-%d").date()
        stage_duration = ( __import__('datetime').datetime.strptime(stage_end, "%Y-%m-%d") - __import__('datetime').datetime.strptime(stage_start, "%Y-%m-%d") ).days + 1
        user_prompt = f"""
        INPUTS:
        
        Crop: {crop}
        Variety: {crop_variety}
        Location: {location}
        
        Growth Stage: {stage_name}
        Start Date: {stage_start}
        End Date: {stage_end}
        Duration: {stage_duration} days
        
        Weather Data:
        {weather_text}
        
        Soil Data:
        {soil_text}
        
        Based on your agricultural knowledge, identify the most likely diseases for this crop at this stage given these weather and soil conditions. Provide practical management advice.
        """
        chosen_model = model if model else MODEL_NAME
        try:
            text = call_llm(
                model=chosen_model,
                system_prompt=system_prompt,
                user_message=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            results.append(f"--- Disease Risk for {stage_name} ({stage_start} to {stage_end}) ---\n" + text)
        except Exception as e:
            results.append(f"Error generating disease assessment for stage {stage_name}: {e}")
    if not results:
        return "No future stages to forecast."
    final_text = "\n\n".join(results)

    # Save to DB
    try:
        from backend.init_db import SessionLocal
        from backend.data_store import save_disease

        stage_id = stage_data.get('id') if isinstance(stage_data, dict) else None
        soil_id = soil_data.get('id') if isinstance(soil_data, dict) else None
        weather_id = weather_data.get('id') if isinstance(weather_data, dict) else None

        chosen_model = model if model else MODEL_NAME
        with SessionLocal() as session:
            obj = save_disease(
                session=session,
                crop_name=crop,
                crop_variety=crop_variety,
                location=location,
                sowing_date=sowing_date,
                stage_id=stage_id,
                soil_id=soil_id,
                weather_id=weather_id,
                model_name=chosen_model,
                prompt=system_prompt,
                output=final_text,
                run_id=run_id,
            )
            return {"id": obj.id, "output": final_text}
    except Exception as ex:
        print(f"[disease_agent] Warning: Could not save to DB: {ex}")
        return final_text
