import os
import json
from datetime import datetime
from dotenv import load_dotenv
from together import Together
from user_input import FarmerInput
from llm_router import call_llm

load_dotenv()

client = Together()
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"

# ==================== IRRIGATION AGENT PROMPT (GENERIC) ====================
irrigation_system_prompt = """
    You are the IRRIGATION PLANNER AGENT for precision agriculture.

    INPUTS:
    - Location: {location}
    - Crop: {crop}
    - Sowing Date: {sowing_date}
    - Area: {area} hectares
    - Farmer Inputs:
      - Irrigation Type: {irrigation_type}
      - Irrigation Method: {irrigation_method}
      - Water Source: {water_source}
      - Water Reliability: {water_reliability}
      - Irrigation Water Quality: {irrigation_water_quality}
      - Soil Texture (observation): {soil_texture}
      - Drainage: {drainage}
      - Waterlogging: {waterlogging}
      - Salinity Signs: {salinity_signs}
      - Field Slope: {field_slope}
      - Hardpan / Crusting: {hardpan_crusting}
      - Farming Method: {farming_method}
      - Planting Method: {planting_method}
    - Soil Report: {soil_report}
    - Water Report: {water_report}
    - Weather Report: {weather_report}
    - Growth Stages: {growth_stages}

    YOUR TASK:
    Create a detailed stage-wise irrigation plan for {crop} crop considering:
    1. Crop-specific water requirements at each growth stage
    2. Soil type and water holding capacity
    3. Weather patterns (rainfall, temperature, humidity)
    4. Available water sources and infrastructure
    5. Irrigation efficiency and method

    IRRIGATION PLANNING RULES:

    1. CROP-SPECIFIC WATER NEEDS:
    - Research and apply scientifically accurate water requirements for {crop}
    - Identify CRITICAL water-sensitive stages (flowering, grain filling, etc.)
    - Early stages: Light irrigation for establishment
    - Vegetative growth: Moderate irrigation
    - Reproductive stages: Usually CRITICAL - higher water needs
    - Maturity: Reduce or stop irrigation before harvest
    - Adjust quantities based on crop type (cereal/pulse/vegetable/cash crop)

    2. SOIL-BASED ADJUSTMENTS:
    - Sandy soil: More frequent (every 3-5 days), lighter irrigation (20-30mm)
    - Loamy soil: Optimal - moderate frequency (every 7-10 days), 40-60mm
    - Clay soil: Less frequent (every 10-15 days), heavier irrigation (60-80mm)
    - Adjust based on actual soil water holding capacity from soil report

    3. WEATHER-BASED ADJUSTMENTS:
    - Rainfall > 20mm: Skip next irrigation
    - High temperature (>35°C): Increase frequency by 20-30%
    - Low humidity (<40%): Increase water by 10-15%
    - Cloudy/humid weather: Reduce frequency by 20-30%
    - Windy conditions: Increase water by 10% (higher evaporation)

    4. WATER SOURCE CONSIDERATIONS:
    - Canal: Schedule based on water availability windows
    - Tubewell: Flexible scheduling, consider electricity/diesel cost
    - Rainfed: Plan for supplementary irrigation during dry spells
    - Drip: Reduce water quantity by 30-40%, increase frequency
    - Sprinkler: Reduce quantity by 20-30%

    If farmer-provided inputs conflict with generic assumptions, prefer the farmer inputs.

    5. CROP-SPECIFIC GUIDELINES:
    - For cereals (wheat/rice/maize): Focus on tillering, flowering, grain filling
    - For pulses (chickpea/lentil): Critical at flowering and pod formation
    - For vegetables: Consistent moisture throughout, critical at fruiting
    - For cash crops (cotton/sugarcane): Stage-specific heavy irrigation
    - For oilseeds: Critical at flowering and seed formation

    OUTPUT FORMAT (STRICT):

    Location: {location}
    Crop: {crop}
    Total Area: {area} hectares
    Irrigation Method: [Based on water source - Drip/Sprinkler/Flood/Furrow]

    STAGE-WISE IRRIGATION PLAN:
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Stage 1: [Stage Name from Growth Stages]
    ├─ Period: YYYY-MM-DD to YYYY-MM-DD (X days)
    ├─ Number of Irrigations: X
    ├─ Water per Irrigation: XX mm (or liters/hectare)
    ├─ Total Water for Stage: XXX mm
    ├─ Irrigation Interval: Every X-Y days
    ├─ Critical Notes: [Crop-specific importance of this stage]
    └─ Weather Adjustments: [Based on weather report]

    Stage 2: [Stage Name]
    ├─ Period: YYYY-MM-DD to YYYY-MM-DD
    ├─ Number of Irrigations: X
    ├─ Water per Irrigation: XX mm
    ├─ Total Water for Stage: XXX mm
    ├─ Irrigation Interval: Every X-Y days
    ├─ Critical Notes: [e.g., "CRITICAL STAGE for {crop} - do not skip"]
    └─ Weather Adjustments: [Rainfall compensation if any]

    [Continue for all stages from Growth Stages report...]

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    IRRIGATION SUMMARY:
    ├─ Total Irrigations Required: XX times
    ├─ Total Water Requirement: XXXX mm (or X lakh liters for {area} hectares)
    ├─ Water per Hectare: XXXX mm
    ├─ Peak Water Demand Period: [Stage name] (YYYY-MM-DD to YYYY-MM-DD)
    └─ Estimated Cost: ₹XXXX (if tubewell/electricity/diesel cost can be estimated)

    CRITICAL IRRIGATION DATES (Do Not Miss):
    1. [Date]: [Stage] - [Why critical for {crop}]
    2. [Date]: [Stage] - [Why critical]
    3. [Date]: [Stage] - [Why critical]

    SOIL-SPECIFIC RECOMMENDATIONS:
    - Soil Type: [From soil report]
    - Water Holding Capacity: [High/Medium/Low]
    - Irrigation Depth: [Shallow/Medium/Deep - based on soil and crop roots]
    - Recommendation: [Specific advice for this soil-crop combination]

    WEATHER-BASED ALERTS:
    - Expected Rainfall: [Total mm during crop season from weather report]
    - Irrigation Savings from Rainfall: XX mm (approximately)
    - High Temperature Periods: [Dates when extra water needed]
    - Extreme Weather Risks: [Frost/heatwave/drought periods if any]

    WATER SOURCE OPTIMIZATION:
    - Primary Source: [From water report - Canal/Tubewell/Rainfed/Other]
    - Backup Plan: [If primary source fails]
    - Water Availability Pattern: [When water is available/scarce]
    - Recommended Method: [Best irrigation method for this source and crop]

    IRRIGATION EFFICIENCY TIPS FOR {crop}:
    ✅ [3-5 practical, crop-specific tips based on soil, weather, and water source]

    CRITICAL WARNINGS:
    ⚠️ [Any water stress periods, deficit irrigation risks, over-irrigation risks for this crop]

    RULES:
    ✅ Be specific with numbers (mm, liters, dates, intervals)
    ✅ Use EXACT stages and dates from Growth Stages report
    ✅ Apply scientifically accurate water needs for {crop}
    ✅ Mark CRITICAL irrigation stages clearly for {crop}
    ✅ Account for expected rainfall from weather report
    ✅ Adjust for soil type from soil report
    ✅ Consider water source constraints from water report
    ❌ NO vague advice like "irrigate regularly" or "water as needed"
    ❌ NO generic recommendations - be crop-specific
    ❌ NO fertilizer/pesticide advice (handled by other agents)
    ❌ DO NOT assume crop type - use the provided {crop} information
"""


def irrigation_agent(
    farmer_input: FarmerInput = None,
    location: str = None,
    crop: str = None,
    sowing_date: str = None,
    area: float = None,
    soil_report: str = None,
    water_report: str = None,
    weather_report: str = None,
    growth_stages: str = None,
    model_name: str = None,
    temperature: float = 0.1,
    max_tokens: int = 2000,
    custom_prompt: str = None,
    session_state=None,
    latitude: float = None,
    longitude: float = None,
    save_to_db: bool = True,
    run_id: int = None,
) -> str:
    """
    Generate detailed stage-wise irrigation plan for any crop.
    
    Args:
        location: Farm location
        crop: Crop name (wheat/rice/maize/cotton/any crop)
        sowing_date: Sowing date (YYYY-MM-DD)
        area: Area in hectares
        soil_report: Soil analysis report
        water_report: Water availability report
        weather_report: Weather data
        growth_stages: Growth stage plan from stage_planner_agent
        custom_prompt: Optional custom prompt
    
    Returns:
        Detailed irrigation plan as string
    """
    from agent_helper import (
        get_or_fetch_soil,
        get_or_fetch_water,
        get_or_fetch_weather,
        get_or_fetch_stage,
        extract_output_text,
    )

    # Backward compatibility: allow calling with explicit args
    if farmer_input is None:
        farmer_input = FarmerInput(
            location=location,
            crop_name=crop,
            sowing_date=sowing_date,
            area=area,
        )

    location = getattr(farmer_input, 'location', location)
    crop = getattr(farmer_input, 'crop_name', crop)
    sowing_date = getattr(farmer_input, 'sowing_date', sowing_date)
    area = getattr(farmer_input, 'area', area)

    chosen_model = model_name if model_name else MODEL_NAME

    # Escape braces in inputs
    def esc(s: str) -> str:
        return (s or "").replace("{", "{{").replace("}", "}}")

    # Use custom prompt if provided
    system_prompt = custom_prompt if custom_prompt else irrigation_system_prompt

    # Fetch dependencies intelligently (session/DB first)
    soil_data = None
    water_data = None
    weather_data = None
    stage_data = None

    if soil_report is None:
        soil_data = get_or_fetch_soil(farmer_input, session_state or {}, chosen_model, latitude, longitude, run_id=run_id)
        soil_report = extract_output_text(soil_data)
    if water_report is None:
        water_data = get_or_fetch_water(farmer_input, session_state or {}, chosen_model, run_id=run_id)
        water_report = extract_output_text(water_data)
    if weather_report is None:
        weather_data = get_or_fetch_weather(farmer_input, session_state or {}, latitude, longitude, model_name=chosen_model, run_id=run_id)
        weather_report = extract_output_text(weather_data)
    if growth_stages is None:
        stage_data = get_or_fetch_stage(farmer_input, session_state or {}, chosen_model, latitude, longitude, run_id=run_id)
        growth_stages = extract_output_text(stage_data)

    # Format prompt with actual data
    user_message = system_prompt.format(
        location=esc(location),
        crop=esc(crop),
        sowing_date=esc(sowing_date),
        area=esc(str(area)),
        irrigation_type=esc(getattr(farmer_input, 'irrigation_type', '') or ''),
        irrigation_method=esc(getattr(farmer_input, 'irrigation_method', '') or ''),
        water_source=esc(getattr(farmer_input, 'water_source', '') or ''),
        water_reliability=esc(getattr(farmer_input, 'water_reliability', '') or ''),
        irrigation_water_quality=esc(getattr(farmer_input, 'irrigation_water_quality', '') or ''),
        soil_texture=esc(getattr(farmer_input, 'soil_texture', '') or ''),
        drainage=esc(getattr(farmer_input, 'drainage', '') or ''),
        waterlogging=esc(getattr(farmer_input, 'waterlogging', '') or ''),
        salinity_signs=esc(getattr(farmer_input, 'salinity_signs', '') or ''),
        field_slope=esc(getattr(farmer_input, 'field_slope', '') or ''),
        hardpan_crusting=esc(getattr(farmer_input, 'hardpan_crusting', '') or ''),
        farming_method=esc(getattr(farmer_input, 'farming_method', '') or ''),
        planting_method=esc(getattr(farmer_input, 'planting_method', '') or ''),
        soil_report=esc(soil_report),
        water_report=esc(water_report),
        weather_report=esc(weather_report),
        growth_stages=esc(growth_stages),
    )

    try:
        text = call_llm(
            model=chosen_model,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if save_to_db:
            try:
                from backend.init_db import SessionLocal
                from backend.data_store import save_irrigation

                stage_id = None
                soil_id = None
                water_id = None
                weather_id = None
                if isinstance(stage_data, dict) and 'id' in stage_data:
                    stage_id = stage_data.get('id')
                if isinstance(soil_data, dict) and 'id' in soil_data:
                    soil_id = soil_data.get('id')
                if isinstance(water_data, dict) and 'id' in water_data:
                    water_id = water_data.get('id')
                if isinstance(weather_data, dict) and 'id' in weather_data:
                    weather_id = weather_data.get('id')

                with SessionLocal() as session:
                    obj = save_irrigation(
                        session=session,
                        location=location,
                        crop_name=crop,
                        sowing_date=sowing_date,
                        area=area,
                        stage_id=stage_id,
                        soil_id=soil_id,
                        water_id=water_id,
                        weather_id=weather_id,
                        model_name=chosen_model,
                        prompt=system_prompt,
                        output=final_text,
                        run_id=run_id,
                    )
                    return {"id": obj.id, "output": final_text}
            except Exception as ex:
                print(f"[irrigation_agent] Warning: Could not save to DB: {ex}")

        return final_text
    except Exception as e:
        return f"Error calling Irrigation Agent: {e}"

