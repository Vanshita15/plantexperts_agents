# Cell 1 (continued): Imports & env
import os
import json
from typing import TypedDict, Optional, Literal, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from together import Together
from dataclasses import dataclass
from langgraph.graph import StateGraph
from openai import OpenAI

load_dotenv()

Together_api_key=os.getenv("TOGETHER_API_KEY")
client=Together()
MODEL_NAME="Qwen/Qwen2.5-72B-Instruct-Turbo"

llama_model_name="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

from user_input import FarmerInput

SOIL_SYSTEM_PROMPT="""
    You are the SOIL AGENT in a multi-agent agricultural system.

    INPUTS:
    - Location (District, State)
    - Crop Name, Variety, Sowing Date, Area

    YOUR TASK:
    Provide baseline soil characteristics for the given location. Use actual report if provided, otherwise estimate from regional soil data.

    OUTPUT FORMAT:

    SOIL ANALYSIS REPORT
    Location: {location}
    Crop: {crop}
    Data Source: [From Soil Test Report / Estimated from regional data]

    1. SOIL TYPE: [Black/Red/Alluvial/Laterite/Sandy/Clayey]

    2. pH: [X.X] - [Acidic (<6.5) / Neutral (6.5-7.5) / Alkaline (>7.5)]

    3. SOIL TEXTURE: [Sandy/Sandy Loam/Loam/Clay Loam/Clay]
    - Water Holding Capacity: [XX%] - [Poor/Moderate/Good]

    4. MAJOR NUTRIENTS (kg/ha):
    - Nitrogen (N): [XXX] - [Low (<280) / Medium (280-560) / High (>560)]
    - Phosphorus (P₂O₅): [XX] - [Low (<11) / Medium (11-22) / High (>22)]
    - Potassium (K₂O): [XXX] - [Low (<110) / Medium (110-280) / High (>280)]

    5. ORGANIC CARBON: [X.X%] - [Low (<0.5) / Medium (0.5-0.75) / High (>0.75)]

    6. CRITICAL MICRONUTRIENTS (ppm):
    - Zinc (Zn): [X.X] - [Deficient (<0.6) / Adequate (>0.6)]
    - Iron (Fe): [X.X] - [Deficient (<4.5) / Adequate (>4.5)]

    7. SALINITY (EC): [X.X dS/m] - [Normal (<1) / Slight (1-2) / Moderate (2-4) / High (>4)]

    8. SOIL HEALTH SCORE: [X.X/5]
    (Based on pH, nutrients, organic matter, and texture balance)

    9. CRITICAL DEFICIENCIES (if any):
    - [List specific nutrients below optimal OR "None detected"]

    ESTIMATION NOTES (only if estimated):
    - Values based on typical {soil_type} soils of {district} region
    - Actual testing recommended for precise nutrient management
    - Confidence level: [High/Medium/Low] based on regional data quality

    RULES:
    ✅ 
    * Regional soil survey data
    * Typical characteristics of soil type in that district
    * Conservative middle-range values
    ✅ For estimates, provide realistic ranges (e.g., N: 220-260 kg/ha)
    ✅ Always show units (kg/ha, ppm, %, dS/m)
    ✅ Mark clearly if "Estimated" vs "From Report"
    ❌ NO fertilizer recommendations
    ❌ NO crop suitability advice
    ❌ NO irrigation information
    ❌ Keep output factual and structured

    This baseline data feeds into nutrient, irrigation, and pest management agents.
    """


def run_soil_agent(
    location: str,
    crop_name: str = "",
    crop_variety: str = "",
    sowing_date: str = "",
    area: float = 0.0,
    latitude: float = None,
    longitude: float = None,
    soil_type: str = "",
    custom_prompt: str = None,
    model: str = None,
    temperature: float = 0.1,
    max_tokens: int = 1200,
    save_to_db: bool = True
    ) -> dict:  # returns {'output': ..., 'id': ...}

    """
    Calls the SOIL AGENT and returns soil analysis report.
    
    Args:
        location: Location name (district, state)
        crop_name: Name of the crop
        crop_variety: Variety of the crop
        sowing_date: Sowing date (YYYY-MM-DD)
        area: Farm area in hectares
        latitude: Latitude coordinate (optional)
        longitude: Longitude coordinate (optional)
        soil_type: Soil type if know
        custom_prompt: Custom system prompt
        model: Model name to use
    """

    # Build detailed user message with all context
    location_info = location
    if latitude and longitude:
        location_info += f" (Coordinates: {latitude:.4f}, {longitude:.4f})"
    
    user_msg = f"""
    Please provide soil analysis for the following:

    LOCATION: {location_info}
    CROP: {crop_name} ({crop_variety})
    SOWING DATE: {sowing_date}
    AREA: {area} hectares

    SOIL INFORMATION:
    - Soil Type (if known): {soil_type if soil_type else "Unknown - please estimate"}
    """
    
    system_prompt = custom_prompt if custom_prompt else SOIL_SYSTEM_PROMPT
    chosen_model = model if model else llama_model_name

    if chosen_model == "gpt-4.1":
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Error: OPENAI_API_KEY not set in environment."
        openai_client = OpenAI(api_key=api_key)
        try:
            resp = openai_client.chat.completions.create(
                model=chosen_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Error calling OpenAI GPT-4.1: {e}"
    else:
        # Use Together API  
        resp = client.chat.completions.create(
            model=chosen_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=max_tokens,  # Increased for full report
            temperature=temperature,
        )
        text = resp.choices[0].message.content.strip()
    if save_to_db:
        print(" ----------------soil agent")
        try:
            from backend.init_db import SessionLocal
            from backend.data_store import save_soil
            with SessionLocal() as session:
                output_str = text['output'] if isinstance(text, dict) and 'output' in text else text
                if isinstance(output_str, dict):
                    import json
                    output_str = json.dumps(output_str, ensure_ascii=False)
                print('[DEBUG][run_soil_agent] output_str type:', type(output_str))
                obj = save_soil(session, location, crop_name, chosen_model, system_prompt, output_str)
                print("TYPE of obj:", type(obj))
                print("obj.id =", obj.id)
                print("-----------------------object>",obj)
                return {'output': output_str, 'id': obj.id}
        except Exception as ex:
            print(f'[run_soil_agent] Warning: Could not save to DB: {ex}')
    return {'output': text, 'id': None}
