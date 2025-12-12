from user_input import FarmerInput
import os
import json
from typing import TypedDict, Optional, Literal, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from together import Together
from dataclasses import dataclass
from openai import OpenAI
from langgraph.graph import StateGraph

load_dotenv()

Together_api_key=os.getenv("TOGETHER_API_KEY")
client=Together()
MODEL_NAME="Qwen/Qwen2.5-72B-Instruct-Turbo"


# water_system_prompt = """
#     You are the WATER AGENT.

#     Task:
#     Given only a location, a crop name, and an optional water source, return a concise plain-text regional water-quality summary useful for farmers. Do NOT use soil data, do NOT create irrigation schedules, and do NOT output JSON.

#     Important behavior:
#     - Return only the water-related information that can be reasonably inferred from the given location and water source. 
#     - If a specific field cannot be inferred regionally, do NOT include that field in the output at all (do NOT write 'Unknown' or placeholders).
#     - Be conservative: when you must guess from regional trends, use lower confidence (<=0.6) and keep language tentative (e.g., "often", "commonly", "may").
#     - Keep output concise and practical for farmers. Maximum ~15 lines.

#     Preferred labels (print only those that have values):
#     Location: <location>
#     Crop: <crop>

#     Suitability for irrigation: <Good / Moderate / Poor>
#     Water availability: <High / Medium / Low>
#     Water source type: <groundwater / canal / river / rainfed>
#     Common local water issues: <short list, e.g., "Fluoride; Salinity">
#     General EC tendency: <Low / Moderate / High>
#     TDS (typical range): <e.g., 200–600 mg/L>
#     Hardness (Ca+Mg): <Soft / Moderate / Hard>

#     Confidence: <0.0–1.0>

#     Rules:
#     - Plain text only, no JSON.
#     - Only include labels/lines for which you can provide a meaningful, regionally-informed answer. Omit others completely.
#     - Do NOT mention soil, fertilizers, nutrients, or create irrigation schedules.
#     - If you are iWatwer

water_system_prompt = """
    You are the WATER AGENT in a multi-agent agricultural system.

    INPUTS:
    - Location (District, State)
    - Crop Name
    - Water Source (Optional: Borewell/Canal/River/Pond/Rainfed)

    YOUR TASK:
    Provide regional water quality and availability information based on location. Keep it practical and farmer-friendly.

    OUTPUT FORMAT:

    WATER INFORMATION
    Location: {location}
    Crop: {crop}

    1. PRIMARY WATER SOURCE (typical for region): [Groundwater/Canal/River/Rainfed]

    2. WATER AVAILABILITY: [Adequate/Moderate/Scarce]
    - Seasonal pattern: [Year-round/Monsoon-dependent/Summer-scarce]

    3. WATER QUALITY (regional typical):
    - Salinity (EC): [Low (<1 dS/m) / Moderate (1-2) / High (>2)]
    - Hardness: [Soft/Moderate/Hard]
    - pH: [X.X] - [Acidic/Neutral/Alkaline]
    - Suitability: [Good/Moderate/Poor for irrigation]

    4. COMMON WATER ISSUES (if any):
    - [e.g., High fluoride, Iron content, Salinity]
    - Impact: [Brief farmer-friendly explanation]

    5. IRRIGATION INFRASTRUCTURE (typical):
    - Method: [Flood/Drip/Sprinkler/Rainfed]
    - Efficiency: [XX%]

    6. WATER QUALITY CONFIDENCE: [X.X/5]
    (Based on regional data availability)

    RULES:
    ✅ Use regional groundwater/surface water data for that district
    ✅ If specific data unavailable → use state/zone averages
    ✅ Keep language simple and direct (avoid "may", "often", "commonly")
    ✅ If a parameter truly unknown → write "Data not available for this region"
    ✅ Mark output as: [Estimated from regional data] or [From water test report]
    ❌ NO soil information
    ❌ NO irrigation schedules (that's for irrigation agent)
    ❌ NO fertilizer advice
    ❌ Keep output under 15 lines

    This data feeds into irrigation and crop planning agents.
    """


def water_agent(farmer: FarmerInput, 
    custom_prompt: str = None, 
    model: str = None,  
    temperature: float = 0.1, 
    max_tokens: int = 1200, 
    save_to_db: bool = True) -> dict:  # returns {'output': ..., 'id': ...}
    """
    Water Agent that uses FarmerInput dataclass.
    """
    location = farmer.location
    crop = farmer.crop_name
    water_source = farmer.irrigation_type if farmer.irrigation_type else ""
    user_msg = f"""
    location: {location}
    crop: {crop}
    water_source: {water_source}

    Please respond only with the plain-text water-quality summary following the system prompt format.
    """

    system_prompt = custom_prompt if custom_prompt else water_system_prompt
    chosen_model = model if model else MODEL_NAME

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
        try:
            from backend.init_db import SessionLocal
            from backend.data_store import save_water
            with SessionLocal() as session:
                obj = save_water(session, location, crop, chosen_model, system_prompt, text)
                return {'output': text, 'id': obj.id}
        except Exception as ex:
            print(f'[water_agent] Warning: Could not save to DB: {ex}')
    return {'output': text, 'id': None}