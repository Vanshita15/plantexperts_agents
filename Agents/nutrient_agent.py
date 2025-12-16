import os
from typing import Any
from dotenv import load_dotenv
from together import Together
from soil import FarmerInput
from soil import run_soil_agent
from water import water_agent
from weather import weather_7day_compact
from llm_router import call_llm

load_dotenv()

MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"

nutrient_system_prompt= """You are the NUTRIENT PLANNER AGENT.

    You will receive:
    - Crop name
    - All stage data (with start & end dates)
    - Soil report (NPK, OC, micronutrients)
    - Weather forecast risk summary (temperature + rainfall pattern)

    Your job: Create a full-season nutrient schedule.

    Your Output MUST follow these rules:

    1) For EVERY stage:
    - Which nutrients are required (N, P, K, micronutrients)
    - Approximate dose (low, moderate, high, or a percentage split)
    - Clear timing ("at sowing", "20-25 DAS", "early flowering")
    - WHERE to apply (soil or foliar)
    - HOW to apply (1 short step)
    - Forecast note: "If rain expected, delay by 3 days" (ONLY if useful)
    - Do NOT give fertilizer product names (urea/mop/dap) — just nutrient needs

    2) Keep TOTAL season overview at the end:
    - Total % nitrogen planned (e.g., 100%)
    - Total % phosphorus usage (e.g., 100% basal)
    - Total % potassium usage
    - Micronutrient summary (if needed)

    3) NO long agronomy theory. NO technical charts.

    4) Output Format EXACTLY:

    -------------------------------------
    CROP: <crop>
    FULL-SEASON NUTRIENT PLAN

    Stage: <stage name> (<start> to <end>)
    Required Nutrients:
    - N: <low/moderate/high or %>
    - P: <basal or none>
    - K: <basal or none>
    - Micronutrients: <only if needed>
    Timing:
    - <when to apply>
    Application:
    - <soil or foliar + simple step>
    Forecast Note:
    - <short actionable note, or "None">

    Stage: <stage name>
    ... (repeat for next stage)

    -------------------------------------
    SEASON SUMMARY:
    - Total N distributed: <100% split across stages>
    - Total P applied: <when>
    - Total K applied: <when>
    - Micronutrient key notes: <list or "None">
    -------------------------------------

    FINAL CONFIDENCE: <0.0–1.0>
    -------------------------------------
    """
def nutrient_agent(
    farmer_input,
    temperature: float = 0.2,
    max_tokens: int = 2500,
    model: str = None,
    soil_text: str = None,
    water_text: str = None,
    weather_text: str = None,
    stages_text: str = None,
    custom_prompt: str = None,
    session_state=None,  # NEW: pass session_state
    latitude: float = None,
    longitude: float = None,
    save_to_db: bool = True,
    run_id: int = None,
) -> Any:
    """
    Generate stage-wise nutrient management plan.
    Uses cached data from session_state or database before making new API calls.
    """
    from agent_helper import (
        get_or_fetch_soil, 
        get_or_fetch_water, 
        get_or_fetch_weather, 
        get_or_fetch_stage,
        extract_output_text
    )
    
    # Fetch dependencies intelligently (checks session/DB first)
    if soil_text is None:
        soil_data = get_or_fetch_soil(farmer_input, session_state or {}, model, latitude, longitude, run_id=run_id)
        print("------------------------------get_or_fetch_soil",soil_data)
        soil_text = extract_output_text(soil_data)
    
    if water_text is None:
        water_data = get_or_fetch_water(farmer_input, session_state or {}, model, run_id=run_id)
        print("------------------------------get_or_fetch_water",water_data)
        water_text = extract_output_text(water_data)
    
    if weather_text is None:
        weather_data = get_or_fetch_weather(farmer_input, session_state or {}, latitude, longitude, run_id=run_id)
        print("------------------------------get_or_fetch_weather",weather_data)
        weather_text = extract_output_text(weather_data)
    
    if stages_text is None:
        stages_text = get_or_fetch_stage(
            farmer_input, 
            session_state or {}, 
            model, 
            latitude, 
            longitude,
            soil_data=soil_data,
            water_data=water_data,
            weather_data=weather_data,
            run_id=run_id,
        )
        print("------------------------------get_or_fetch_stage",stages_text)


    system_prompt = custom_prompt if custom_prompt else nutrient_system_prompt
    prompt = f"""
    {system_prompt}

    INPUTS PROVIDED:

    Crop: {farmer_input.crop_name}
    Variety: {farmer_input.crop_variety}
    Location: {farmer_input.location}
    Area: {farmer_input.area} hectares

    FARMER CONTEXT:
    Previous crop: {getattr(farmer_input, 'previous_crop_sowed', None)}
    Farming method: {getattr(farmer_input, 'farming_method', None)}
    Planting method: {getattr(farmer_input, 'planting_method', None)}
    Irrigation type: {getattr(farmer_input, 'irrigation_type', None)}
    Irrigation method: {getattr(farmer_input, 'irrigation_method', None)}
    Water source: {getattr(farmer_input, 'water_source', None)}
    Last fertilizers used: {getattr(farmer_input, 'last_fertilizers_used', None)}
    Last fertilizer date: {getattr(farmer_input, 'last_fertilizer_date', None)}

    GROWTH STAGES (from Stage Agent):
    {stages_text}

    SOIL DATA (from Soil Agent):
    {soil_text}

    WATER DATA (from Water Agent):
    {water_text}

    WEATHER DATA (from Weather Agent):
    {weather_text}

    ---
    IMPORTANT:
    - Use ONLY the data provided above for soil, water, and weather. DO NOT generate or assume any additional information.
    - Explain all recommendations in simple, farmer-friendly language, not just numbers.
    - If any information is missing, state clearly that the data is not available and do not attempt to estimate or hallucinate.
    - Focus only on nutrient management, using the provided data.
    ---

    Generate a complete stage-wise nutrient management plan as per the format above, ensuring all explanations are clear and actionable for a farmer.
    """
    
    chosen_model = model if model else MODEL_NAME
    try:
        text_out = call_llm(
            model=chosen_model,
            system_prompt="You are an expert agricultural nutrient management specialist.",
            user_message=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if save_to_db:
            try:
                from backend.init_db import SessionLocal
                from backend.data_store import save_nutrient

                stage_id = stages_text.get('id') if isinstance(stages_text, dict) else None
                soil_id = soil_data.get('id') if 'soil_data' in locals() and isinstance(soil_data, dict) else None
                water_id = water_data.get('id') if 'water_data' in locals() and isinstance(water_data, dict) else None
                weather_id = weather_data.get('id') if 'weather_data' in locals() and isinstance(weather_data, dict) else None

                with SessionLocal() as session:
                    obj = save_nutrient(session=session,crop_name=getattr(farmer_input, 'crop_name', None),crop_variety=getattr(farmer_input, 'crop_variety', None),
                        location=getattr(farmer_input, 'location', None),
                        area=getattr(farmer_input, 'area', None),
                        stage_id=stage_id,
                        soil_id=soil_id,
                        water_id=water_id,
                        weather_id=weather_id,
                        model_name=chosen_model,
                        prompt=system_prompt,
                        output=text_out,
                        run_id=run_id,
                    )
                    return {'id': obj.id, 'output': text_out}
            except Exception as ex:
                print(f"[nutrient_agent] Warning: Could not save to DB: {ex}")

        return text_out
    except Exception as e:
        return f"Error generating nutrient plan: {e}"
