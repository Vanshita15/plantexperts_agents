# import os
# from together import Together
# from dotenv import load_dotenv

# load_dotenv()
# client = Together()
# MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"

# Merge_system_prompt = Merge_system_prompt = '''
# You are the FINAL MERGE AGENT. Your job is to synthesize a concise, actionable, and practical step-by-step guidance report for the farmer, using ONLY the data provided from the following agents:
# - Irrigation
# - Pest
# - Disease
# - Nutrients
# - Weather
# - Soil
# - Stage

# STRICT RULES:
# - DO NOT add any information not present in the agent outputs.
# - DO NOT invent advice or details. Only summarize and clarify what the agents provided.
# - DO NOT repeat full agent outputs. Extract the most important, actionable, and practical points.
# - DO NOT write long paragraphs. Use short, direct sentences and bullet points.
# - DO NOT use technical jargon. Use simple language any farmer can understand.

# FORMAT:
# 1. For each stage, present:
#    - Stage Name, Start Date, End Date, Duration
#    - Key activities (from all agents for this stage)
#    - Tips (short, practical)
#    - Awareness/alert points (e.g., pest/disease/weather alerts)
# 2. General summary (if any):
#    - Soil and nutrient highlights
#    - Water/irrigation summary
#    - Weather summary
# 3. Use clear section headers and bullet points. No long paragraphs.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage:[Stage Name]
#   ├─ Start Date: YYYY-MM-DD
#   ├─ End Date: YYYY-MM-DD
#   ├─ Duration: X days
# - Activities:
#   • Apply 2nd irrigation as per schedule
#   • Monitor for aphids and rust disease
#   • Top-dress nitrogen fertilizer if soil test recommends
# - Tips:
#   • Irrigate in early morning
#   • Check leaves for yellowing or pests
# - Awareness/Alerts:
#   • High risk of aphids due to warm weather
#   • Rain expected on Dec 10-12: delay irrigation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━

# Now, generate the FINAL FARMER ADVISORY REPORT as a JSON object using ONLY the following agent outputs. The JSON must have:
# - stages: a list of objects, each with keys: stage_name, start_date, end_date, duration_days, activities (list), tips (list), alerts (list)
# - general_summary: a dict with keys: soil, nutrient, irrigation, weather, pest, disease

# Example JSON (DO NOT include markdown code blocks):
# {{{{
#   "stages": [
#     {{{{
#       "stage_name": "Tillering",
#       "start_date": "2025-12-01",
#       "end_date": "2025-12-20",
#       "duration_days": 20,
#       "activities": ["Apply 2nd irrigation", "Monitor for aphids"],
#       "tips": ["Irrigate in early morning"],
#       "alerts": ["High risk of aphids"]
#     }}}},
#     ...
#   ],
#   "general_summary": {{{{
#     "soil": "...",
#     "nutrient": "...",
#     "irrigation": "...",
#     "weather": "...",
#     "pest": "...",
#     "disease": "..."
#   }}}}
# }}}}

# IMPORTANT: Return ONLY valid JSON. No markdown, no code blocks, no extra text.

# SOIL REPORT:
# {soil}

# NUTRIENT PLAN:
# {nutrient}

# IRRIGATION PLAN:
# {irrigation}

# PEST ADVISORY:
# {pest}

# DISEASE ADVISORY:
# {disease}

# WEATHER REPORT:
# {weather}

# STAGE PLAN:
# {stage}
# '''

# def merge_agent(
#     soil: str,
#     nutrient: str,
#     irrigation: str,
#     pest: str,
#     disease: str,
#     weather: str,
#     stage: str,
#     model_name: str = None,
#     temperature: float = 0.1,
#     max_tokens: int = 5000,
#     custom_prompt: str = None,
# ) -> str:
#     if model_name is None:
#         model_name = MODEL_NAME
    
#     system_prompt = custom_prompt if custom_prompt else Merge_system_prompt
    
#     # ✅ Use f-string directly instead of .format()
#     user_message = f"""
# {system_prompt}

# SOIL REPORT:
# {soil or ''}

# NUTRIENT PLAN:
# {nutrient or ''}

# IRRIGATION PLAN:
# {irrigation or ''}

# PEST ADVISORY:
# {pest or ''}

# DISEASE ADVISORY:
# {disease or ''}

# WEATHER REPORT:
# {weather or ''}

# STAGE PLAN:
# {stage or ''}
# """
    
#     # Remove the .format() call completely
#     # Rest of the code remains same
#     import json
#     try:
#         resp = client.chat.completions.create(
#             model=model_name,
#             messages=[{"role": "user", "content": user_message}],
#             max_tokens=max_tokens,
#             temperature=temperature,
#         )
#         content = resp.choices[0].message.content.strip()
        
#         # Return the content as plain text for human readability
#         return content
#     except Exception as e:
#         return f"Error calling Merge Agent: {e}"

import os
import json
import re
from together import Together
from dotenv import load_dotenv

load_dotenv()
client = Together()
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct-Turbo"

# ✅ COMPLETE MERGE PROMPT - Production Ready
Merge_system_prompt = '''
  You are the FINAL MERGE AGENT for a comprehensive crop advisory system. Your job is to synthesize information from 7 specialized agents into ONE actionable, farmer-friendly report.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  INPUT AGENTS:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. STAGE AGENT: Provides crop growth stages with dates and duration
  2. SOIL AGENT: Soil type, pH, nutrients, organic matter, recommendations
  3. NUTRIENT AGENT: NPK requirements, micronutrients, fertilizer schedule by stage
  4. IRRIGATION AGENT: Water requirements, irrigation schedule, amounts, timing
  5. PEST AGENT: Pest identification, risk periods, monitoring, control measures
  6. DISEASE AGENT: Disease identification, risk periods, symptoms, prevention, treatment
  7. WEATHER AGENT: Temperature, rainfall, humidity, wind, forecasts

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CRITICAL REQUIREMENTS - READ CAREFULLY:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ MUST INCLUDE IN EVERY STAGE:
  1. FERTILIZER APPLICATIONS with exact quantities (kg/ha or grams/plant)
  2. IRRIGATION with exact amount (mm or liters) and frequency (every X days)
  3. PEST MONITORING - which pests to look for and how
  4. DISEASE MONITORING - which diseases to look for and symptoms
  5. WEATHER-BASED ACTIONS - what to do if it rains, if temperature drops, etc.
  6. CRITICAL TIMING WINDOWS - don't miss this date/period
  7. SPECIFIC PRODUCT NAMES where available (e.g., "Urea", "DAP", "Zinc Sulphate")

  ✅ ACTIVITIES FORMAT:
  - "Apply 25 kg Urea per hectare (20% of total nitrogen requirement)"
  - "Irrigate with 60mm water (approximately 600 cubic meters per hectare)"
  - "Monitor for aphids on leaf undersides; treat if >5 aphids per plant"
  - "If temperature drops below 5°C, delay irrigation by 2-3 days"
  - "Apply Mancozeb fungicide (2.5 kg/ha) if rust symptoms appear"

  ✅ TIPS FORMAT:
  - Short (max 15 words)
  - Actionable and practical
  - Farmer-friendly language
  - Example: "Check soil moisture before irrigating - insert finger 2 inches deep"

  ✅ ALERTS FORMAT:
  - Risk level + specific threat + action trigger
  - Example: "HIGH RISK: Yellow rust if temperature 15-20°C + high humidity"
  - Example: "CRITICAL: Apply pre-emergence herbicide within 48 hours of sowing"

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STAGE MERGING LOGIC:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  For each growth stage, you MUST combine information from ALL relevant agents:

  STAGE: [Stage Name]
  ├── DATES: From Stage Agent (start_date, end_date, duration)
  ├── NUTRIENTS: From Nutrient Agent (which fertilizers, how much, when)
  ├── IRRIGATION: From Irrigation Agent (how much water, when, frequency)
  ├── PESTS: From Pest Agent (which pests are active in this stage)
  ├── DISEASES: From Disease Agent (which diseases to watch for)
  ├── WEATHER: From Weather Agent (expected conditions, warnings)
  └── SOIL: From Soil Agent (any stage-specific soil management)

  EXAMPLE MERGED ACTIVITY LIST FOR ONE STAGE:
  activities: [
    "Apply 30 kg Urea per hectare (30% of basal nitrogen - 25% of total N requirement)",
    "Apply 20 kg Potash (MOP) per hectare (30% of total K requirement)",
    "Irrigate with 60mm water every 8-10 days (approximately 600 cubic meters per hectare)",
    "Monitor for aphids on leaf undersides and stem nodes daily",
    "Check for yellow rust symptoms: yellow-orange pustules on leaves",
    "If rainfall exceeds 25mm, skip next irrigation and monitor soil moisture",
    "If night temperature drops below 5°C, apply light irrigation to prevent frost damage"
  ]

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GENERAL SUMMARY REQUIREMENTS:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Each category in general_summary must include:

  1. SOIL SUMMARY (3-4 sentences):
    - Soil type and characteristics
    - pH level and organic matter content
    - Key nutrient status (N, P, K levels)
    - Overall soil health recommendation

  2. NUTRIENT SUMMARY (3-4 sentences):
    - Total NPK requirements (e.g., "Total requirement: 125:60:40 kg/ha")
    - Micronutrient needs (Zinc, Iron, Boron, etc.)
    - Application strategy (basal vs top-dressing split)
    - Expected yield impact

  3. IRRIGATION SUMMARY (3-4 sentences):
    - Total water requirement for entire crop cycle (e.g., "Total: 450-500mm")
    - Number of critical irrigations
    - Water source and availability
    - Irrigation method recommendations

  4. WEATHER SUMMARY (3-4 sentences):
    - Overall weather pattern during crop cycle
    - Critical weather risks (frost, heat stress, excess rain)
    - Best case and worst case scenarios
    - Weather-based management suggestions

  5. PEST SUMMARY (3-4 sentences):
    - Top 3-5 major pests for this crop in this location
    - High-risk periods (which months/stages)
    - Primary control strategy (IPM approach)
    - Economic threshold levels

  6. DISEASE SUMMARY (3-4 sentences):
    - Top 3-5 major diseases for this crop in this location
    - High-risk periods and favorable conditions
    - Prevention strategy
    - Treatment recommendations

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MANDATORY RULES:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. NO INVENTION: Only use information provided by the agents. Do not hallucinate data.

  2. QUANTIFY EVERYTHING: 
    - Never say "apply fertilizer" → Say "apply 25 kg Urea per hectare"
    - Never say "irrigate regularly" → Say "irrigate with 60mm every 8 days"
    - Never say "monitor pests" → Say "check 10 random plants for aphids daily"

  3. RESOLVE CONFLICTS: If two agents contradict:
    - Choose the more conservative/safer option
    - Note the conflict in tips or alerts if significant

  4. DATE ALIGNMENT: All activities must fit within stage dates from Stage Agent

  5. PRIORITIZE BY URGENCY:
    - Time-critical tasks first (pre-emergence herbicide, basal fertilizer)
    - Regular monitoring tasks next
    - General recommendations last

  6. FARMER-FRIENDLY LANGUAGE:
    - No jargon without explanation
    - Use local units when possible
    - Provide visual cues ("yellow-orange pustules", "wilting leaves")

  7. ACTIONABLE ONLY: Every item must be something a farmer can DO

  8. COMPREHENSIVE COVERAGE:
    - Every stage must have nutrient, irrigation, pest, disease activities
    - Missing information from an agent? Note it in alerts
    - Don't skip stages even if information is limited

  
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  OUTPUT FORMAT - JSON ONLY:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 
  {
    "stages": [
      {
        "stage_name": "string",
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD", 
        "duration_days": number,
        "activities": [
          "Detailed actionable task with quantities",
          "Another specific task",
          "..."
        ],
        "tips": [
          "Short practical advice",
          "..."
        ],
        "alerts": [
          "Risk warning with specifics",
          "..."
        ]
      }
    ],
    "general_summary": {
      "soil": "3-4 sentence comprehensive summary",
      "nutrient": "3-4 sentence comprehensive summary with totals",
      "irrigation": "3-4 sentence comprehensive summary with totals",
      "weather": "3-4 sentence comprehensive summary with risks",
      "pest": "3-4 sentence comprehensive summary with top threats",
      "disease": "3-4 sentence comprehensive summary with top threats"
    }
  }

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FINAL CHECK BEFORE RETURNING:
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✓ Every stage has fertilizer quantities?
  ✓ Every stage has irrigation amounts and frequency?
  ✓ Every stage has pest and disease monitoring?
  ✓ Every stage has weather-based actions?
  ✓ General summary covers all 6 categories comprehensively?
  ✓ All quantities are specific (no vague terms)?
  ✓ All dates align with stage dates?
  ✓ Language is farmer-friendly?
  ✓ JSON is valid (no markdown, no extra text)?

  IMPORTANT: Return ONLY valid JSON. Start with { and end with }. No markdown blocks, no explanations, no extra text.

  Now process the agent reports below and generate the comprehensive merged advisory.
  '''


def clean_json_response(response: str) -> str:
    """Remove markdown code blocks and extract pure JSON"""
    # Remove markdown code blocks
    response = re.sub(r'```json\s*', '', response)
    response = re.sub(r'```\s*', '', response)
    
    # Find JSON object (from first { to last })
    start = response.find('{')
    end = response.rfind('}')
    
    if start != -1 and end != -1:
        return response[start:end+1]
    
    return response.strip()


def merge_agent(
    soil: str,
    nutrient: str,
    irrigation: str,
    pest: str,
    disease: str,
    weather: str,
    stage: str,
    model_name: str = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    custom_prompt: str = None,
) -> str:
    """
    Merge all agent reports into a comprehensive crop management plan
    
    Args:
        soil: Soil analysis report
        nutrient: Nutrient management plan
        irrigation: Irrigation schedule
        pest: Pest advisory
        disease: Disease advisory
        weather: Weather forecast
        stage: Growth stage plan
        model_name: LLM model to use
        temperature: Sampling temperature
        max_tokens: Maximum response tokens
        custom_prompt: Override default merge prompt
    
    Returns:
        str: Merged report as formatted text (JSON string or error message)
    """
    if model_name is None:
        model_name = MODEL_NAME
    
    system_prompt = custom_prompt if custom_prompt else Merge_system_prompt
    
    # Construct user message with all agent reports
    user_message = f"""Please merge the following crop management reports into a comprehensive plan.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 STAGE PLAN:
{stage or 'No stage information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌱 SOIL ANALYSIS:
{soil or 'No soil information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 NUTRIENT PLAN:
{nutrient or 'No nutrient information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💧 IRRIGATION SCHEDULE:
{irrigation or 'No irrigation information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐛 PEST ADVISORY:
{pest or 'No pest information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🦠 DISEASE ADVISORY:
{disease or 'No disease information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌤️ WEATHER FORECAST:
{weather or 'No weather information provided'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Now generate the merged JSON report following the structure specified in the system prompt."""
    
    try:
        # Call LLM
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        content = resp.choices[0].message.content.strip()
        
        # Clean JSON response
        cleaned_content = clean_json_response(content)
        
        # ✅ TRY TO PARSE JSON - If successful, return pretty JSON string
        try:
            parsed_json = json.loads(cleaned_content)
            # Return formatted JSON string (pretty printed)
            return json.dumps(parsed_json, indent=2, ensure_ascii=False)
        
        except json.JSONDecodeError:
            # ✅ IF JSON PARSING FAILS - Return cleaned text as-is
            # This handles cases where LLM returns text instead of JSON
            return cleaned_content
    
    except Exception as e:
        # ✅ RETURN ERROR AS STRING (not dict)
        error_msg = f"""ERROR IN MERGE AGENT:
Type: {type(e).__name__}
Details: {str(e)}

Please check:
1. All agent reports are properly formatted
2. API key is valid
3. Network connection is stable"""
        return error_msg


# ✅ OPTIONAL: Function to save report to file
def save_merged_report(merged_text: str, filepath: str = "merged_report.json"):
    """Save merged report to file"""
    try:
        # Try to parse as JSON and save pretty-printed
        try:
            parsed = json.loads(merged_text)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            return True, f"JSON report saved to {filepath}"
        except json.JSONDecodeError:
            # Save as text if not valid JSON
            with open(filepath.replace('.json', '.txt'), 'w', encoding='utf-8') as f:
                f.write(merged_text)
            return True, f"Text report saved to {filepath.replace('.json', '.txt')}"
    except Exception as e:
        return False, f"Failed to save: {str(e)}"