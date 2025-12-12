import streamlit as st
import json
import zipfile
from io import BytesIO
from datetime import datetime
from soil import run_soil_agent, SOIL_SYSTEM_PROMPT
from user_input import FarmerInput
from water import water_agent, water_system_prompt
from weather import weather_7day_compact
from stage_agent import stage_system_prompt, stage_generation
from nutrient_agent import nutrient_agent, nutrient_system_prompt
from pest import Pest_system_prompt, pest_agent
from disease import Disease_system_prompt, disease_agent
from irrigation import irrigation_agent, irrigation_system_prompt
from merge_agent import Merge_system_prompt, merge_agent
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Fullscreen

import sys
from pathlib import Path

# Ensure project root (Ai_agent_langgraph) is on sys.path so sibling packages like `backend` are importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]   # Agents/.. => project root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Page config
st.set_page_config(
    page_title="Crop Advisory System",
    page_icon="🌾",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 1rem;
    }
    .agent-pill {
        display: inline-block;
        padding: 12px 24px;
        margin: 8px;
        border-radius: 25px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .agent-pill:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .agent-pill.selected {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        transform: scale(1.05);
    }
    .output-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #2E7D32;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 14px;
    }
    .prompt-box {
        background-color: #fff3cd;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #ffc107;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 13px;
    }
    .run-button {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        cursor: pointer;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🌾 Crop Advisory System</h1>', unsafe_allow_html=True)

# Initialize session state
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None
if 'agent_outputs' not in st.session_state:
    st.session_state.agent_outputs = {}
if 'custom_prompts' not in st.session_state:
    st.session_state.custom_prompts = {}
if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.2
if 'max_tokens' not in st.session_state:
    st.session_state.max_tokens = 1500
if 'location_coords' not in st.session_state:
    st.session_state.location_coords = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "claude-sonnet-4-20250514"

# Default prompts
DEFAULT_PROMPTS = {
    'soil': SOIL_SYSTEM_PROMPT,
    'water': water_system_prompt,
    'stage': stage_system_prompt,
    'nutrient': nutrient_system_prompt,
    'pest': Pest_system_prompt,
    'disease': Disease_system_prompt,
    'irrigation': irrigation_system_prompt,
    'merge': Merge_system_prompt
}

# Initialize custom prompts
for key, value in DEFAULT_PROMPTS.items():
    if key not in st.session_state.custom_prompts:
        st.session_state.custom_prompts[key] = value

# Agent definitions
AGENTS = [
    {'id': 'soil', 'name': '🌱 Soil', 'icon': '🌱'},
    {'id': 'water', 'name': '💧 Water', 'icon': '💧'},
    {'id': 'weather', 'name': '🌤️ Weather', 'icon': '🌤️'},
    {'id': 'stage', 'name': '📊 Stage', 'icon': '📊'},
    {'id': 'nutrient', 'name': '🧪 Nutrient', 'icon': '🧪'},
    {'id': 'pest', 'name': '🐛 Pest', 'icon': '🐛'},
    {'id': 'disease', 'name': '🦠 Disease', 'icon': '🦠'},
    {'id': 'irrigation', 'name': '💦 Irrigation', 'icon': '💦'},
    {'id': 'merge', 'name': '📋 Merge', 'icon': '📋'}
]

# Sidebar - User Input
with st.sidebar:
    st.header("📝 User Input")
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
    with st.form("input_form"):
    # Model Selection
        st.subheader("🤖 AI Model")
        model_options = {
            "Qwen2.5-72B-Turbo (Together)": "Qwen/Qwen2.5-72B-Instruct-Turbo",
            "Meta-Llama-3.1-70B-Instruct-Turbo (Together)": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "Sonnet 4.5 (API)": "sonnet-4.5",
            "GPT-4.1 (API)": "gpt-4.1",
        }
        selected_model_name = st.selectbox(
            "Select Model",
            options=list(model_options.keys()),
            index=0
        )

        st.subheader("⚙️ Generation Settings")
        st.session_state.temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.temperature),
            step=0.01,
        )
        st.session_state.max_tokens = st.number_input(
            "Max Tokens",
            min_value=256,
            max_value=8192,
            value=int(st.session_state.max_tokens),
            step=100,
        )
        
        st.markdown("---")
        
        # Location with Map
        st.subheader("📍 Location")
        location_name = st.text_input("Location Name (optional)", key="location_name_input", value=st.session_state.get("location_name", ""), help="Used only if map coordinates not selected")
        
        st.markdown("**📌 Draw polygon or place marker on map:**")
        
        # Initialize map
        if st.session_state.location_coords is None:
            center = [22.5937, 75.0949]  # Default: Dhar
        else:
            center = st.session_state.location_coords
        
        m = folium.Map(location=center, zoom_start=12)

        # Add fullscreen control
        Fullscreen(position='topright', title='Full Screen', title_cancel='Exit Full Screen', force_separate_button=True).add_to(m)

        # Add drawing tools
        draw = Draw(
            draw_options={
                'polyline': False,
                'rectangle': True,
                'polygon': True,
                'circle': False,
                'marker': True,
                'circlemarker': False
            },
            edit_options={'edit': True}
        )
        draw.add_to(m)

        map_data = st_folium(m, width=400, height=400, key="location_map")

        # Extract coordinates from drawn shapes and update location_name via reverse geocode
        if map_data and map_data.get('all_drawings'):
            drawings = map_data['all_drawings']
            if drawings and len(drawings) > 0:
                last_drawing = drawings[-1]
                coords = None
                if last_drawing['geometry']['type'] == 'Polygon':
                    coords = last_drawing['geometry']['coordinates'][0]
                    lats = [c[1] for c in coords]
                    lngs = [c[0] for c in coords]
                    center_lat = sum(lats) / len(lats)
                    center_lng = sum(lngs) / len(lngs)
                    st.session_state.location_coords = [center_lat, center_lng]
                    st.info(f"📍 Polygon center: {center_lat:.4f}, {center_lng:.4f}")
                elif last_drawing['geometry']['type'] == 'Point':
                    coords = last_drawing['geometry']['coordinates']
                    st.session_state.location_coords = [coords[1], coords[0]]
                    st.info(f"📍 Marker: {coords[1]:.4f}, {coords[0]:.4f}")
                # Live reverse geocode and update location_name
                if st.session_state.location_coords:
                    try:
                        from weather import reverse_geocode
                        geo = reverse_geocode(st.session_state.location_coords[0], st.session_state.location_coords[1])
                        if geo and geo.get('name'):
                            st.session_state.location_name = geo['name']
                            # if 'form_data' in st.session_state:
                            #     st.session_state.form_data['location_name'] = geo['name']
                            st.info(f"📍 Place: {geo['name']}")
                    except Exception as e:
                        st.warning(f"Reverse geocode failed: {e}")
        
        st.markdown("---")
        
        # Crop Details
        st.subheader("🌾 Crop Details")
        crop_name = st.text_input("Crop Name", value="Wheat")
        crop_variety = st.text_input("Crop Variety", value="HD-2967")
        sowing_date = st.date_input("Sowing Date", value=datetime(2025, 11, 11))
        previous_crop_sowed = st.text_input("Previous Crop Sowed", value="maize")
        area = st.number_input("Area (hectares)", min_value=0.1, value=2.0, step=0.1)

        st.markdown("---")

        st.subheader("🚜 Farm Practices")
        irrigation_type = st.selectbox(
            "Irrigation Type",
            options=["rainfed", "borewell", "canal", "drip"],
            index=0,
        )
        irrigation_method = st.selectbox(
            "Irrigation Method",
            options=["rainfed", "drip", "sprinkler", "flood", "furrow", "basin", "other"],
            index=0,
        )
        water_source = st.selectbox(
            "Water Source",
            options=["rainfed", "borewell", "canal", "river", "pond", "tank", "other"],
            index=0,
        )
        farming_method = st.selectbox(
            "Farming Method",
            options=["traditional", "organic", "integrated", "precision", "natural", "mixed"],
            index=0,
        )
        planting_method = st.selectbox(
            "Planting Method",
            options=["direct_seeding", "transplanting", "dibbling", "broadcasting", "ridge_furrow", "other"],
            index=0,
        )

        fertilizer_options = [
            "Urea",
            "DAP",
            "MOP (Potash)",
            "SSP",
            "NPK (complex)",
            "FYM/Compost",
            "Vermicompost",
            "Micronutrient mix",
            "Gypsum",
            "Lime",
            "Other",
        ]
        last_fertilizers_used = st.multiselect(
            "Last Fertilizer(s) Used",
            options=fertilizer_options,
            default=[],
        )
        has_last_fertilizer_date = st.checkbox("I remember the last fertilizer date", value=False)
        last_fertilizer_date = None
        if has_last_fertilizer_date:
            last_fertilizer_date = st.date_input(
                "Last Fertilizer Date",
                value=datetime.today(),
            )
        
        st.markdown("---")
        
        st.subheader("👀 Field Observations (No report)")
        soil_texture = st.selectbox(
            "Soil Texture (your observation)",
            options=["unknown", "sandy", "loamy", "clayey", "silty", "black_cotton"],
            index=0,
        )
        drainage = st.selectbox(
            "Drainage",
            options=["unknown", "good", "medium", "poor"],
            index=0,
        )
        waterlogging = st.selectbox(
            "Waterlogging in field",
            options=["unknown", "never", "sometimes", "often"],
            index=0,
        )
        salinity_signs = st.selectbox(
            "Salinity signs (white crust / salty patches)",
            options=["unknown", "none", "suspected", "confirmed"],
            index=0,
        )
        field_slope = st.selectbox(
            "Field slope",
            options=["unknown", "flat", "gentle", "steep"],
            index=0,
        )
        hardpan_crusting = st.selectbox(
            "Hardpan / Crusting issues",
            options=["unknown", "no", "yes"],
            index=0,
        )
        irrigation_water_quality = st.selectbox(
            "Irrigation water quality (your observation)",
            options=["unknown", "good", "salty"],
            index=0,
        )
        water_reliability = st.selectbox(
            "Water availability reliability",
            options=["unknown", "reliable", "sometimes_short", "often_short"],
            index=0,
        )
        last_season_pest_pressure = st.selectbox(
            "Last season pest pressure",
            options=["unknown", "low", "medium", "high"],
            index=0,
        )
        last_season_disease_pressure = st.selectbox(
            "Last season disease pressure",
            options=["unknown", "low", "medium", "high"],
            index=0,
        )
        
        st.markdown("---")
        
        # Soil Report (Optional)
        st.subheader("📄 Soil Report (Optional)")
        has_soil_report = st.checkbox("I have a soil test report")
        soil_report_text = ""
        if has_soil_report:
            soil_report_text = st.text_area(
                "Paste soil report",
                height=100,
                placeholder="pH: 7.8, N: 245 kg/ha..."
            )
        
        # SUBMIT BUTTON - This captures all form data
        submit_form = st.form_submit_button("✅ Submit & Save Inputs", use_container_width=True, type="primary")

# Handle form submission OUTSIDE the form
if submit_form:
    loc_name_to_save = st.session_state.get("location_name") or location_name

    st.session_state.crop_name = crop_name
    st.session_state.crop_variety = crop_variety
    st.session_state.sowing_date = sowing_date.strftime("%Y-%m-%d") if hasattr(sowing_date, 'strftime') else str(sowing_date)
    st.session_state.previous_crop_sowed = previous_crop_sowed
    st.session_state.area = area
    st.session_state.irrigation_method = irrigation_method
    st.session_state.irrigation_type = irrigation_type
    st.session_state.water_source = water_source
    st.session_state.farming_method = farming_method
    st.session_state.planting_method = planting_method
    st.session_state.last_fertilizers_used = last_fertilizers_used
    st.session_state.last_fertilizer_date = last_fertilizer_date.strftime("%Y-%m-%d") if hasattr(last_fertilizer_date, 'strftime') and last_fertilizer_date else None

    st.session_state.soil_texture = soil_texture
    st.session_state.drainage = drainage
    st.session_state.waterlogging = waterlogging
    st.session_state.salinity_signs = salinity_signs
    st.session_state.field_slope = field_slope
    st.session_state.hardpan_crusting = hardpan_crusting
    st.session_state.irrigation_water_quality = irrigation_water_quality
    st.session_state.water_reliability = water_reliability
    st.session_state.last_season_pest_pressure = last_season_pest_pressure
    st.session_state.last_season_disease_pressure = last_season_disease_pressure

    # Store all form data in session state
    st.session_state.form_data = {
        'model': model_options[selected_model_name],
        'location_name': loc_name_to_save,
        'crop_name': crop_name,
        'crop_variety': crop_variety,
        'sowing_date': sowing_date.strftime("%Y-%m-%d") if hasattr(sowing_date, 'strftime') else str(sowing_date),
        'previous_crop_sowed':previous_crop_sowed,
        'area': area,
        'irrigation_type': irrigation_type,
        'irrigation_method': irrigation_method,
        'water_source': water_source,
        'farming_method': farming_method,
        'planting_method': planting_method,
        'last_fertilizers_used': last_fertilizers_used,
        'last_fertilizer_date': last_fertilizer_date.strftime("%Y-%m-%d") if hasattr(last_fertilizer_date, 'strftime') and last_fertilizer_date else None,
        'soil_texture': soil_texture,
        'drainage': drainage,
        'waterlogging': waterlogging,
        'salinity_signs': salinity_signs,
        'field_slope': field_slope,
        'hardpan_crusting': hardpan_crusting,
        'irrigation_water_quality': irrigation_water_quality,
        'water_reliability': water_reliability,
        'last_season_pest_pressure': last_season_pest_pressure,
        'last_season_disease_pressure': last_season_disease_pressure,
        # 'has_soil_report': has_soil_report,
        # 'soil_report_text': soil_report_text,
        'location_coords': st.session_state.location_coords
    }
    
    # Save to database
    from backend.init_db import SessionLocal
    from backend.user_store import save_previous_crop_sowed
    from backend.data_store import save_soil, save_water, save_weather
    with SessionLocal() as session:
        save_previous_crop_sowed(
            session,
            crop_name=crop_name,
            crop_variety=crop_variety,
            sowing_date=sowing_date.strftime("%Y-%m-%d") if hasattr(sowing_date, 'strftime') else str(sowing_date),
            previous_crop_sowed=previous_crop_sowed,
            location=loc_name_to_save,
            area=str(area),
            model_name=model_options[selected_model_name],
            latitude=str(st.session_state.location_coords[0]) if st.session_state.location_coords else None,
            longitude=str(st.session_state.location_coords[1]) if st.session_state.location_coords else None,
        )
    st.session_state.form_submitted = True
    st.session_state.selected_model = model_options[selected_model_name]
    st.success("✅ Form submitted successfully! You can now run agents.")
    st.rerun()

# Show submitted data
if st.session_state.form_submitted:
    st.success("✅ Form Data Submitted")
    with st.expander("📋 View Submitted Data"):
        data = st.session_state.form_data
        st.write(f"**Crop:** {data['crop_name']} ({data['crop_variety']})")

        loc_display = data.get('location_name') or "Unknown"
        st.write(f"**Location:** {loc_display}")
        if data.get('location_coords'):
            st.write(f"**Coordinates:** {data['location_coords'][0]:.4f}, {data['location_coords'][1]:.4f}")
        st.write(f"**Sowing Date:** {data['sowing_date']}")
        st.write(f"**Area:** {data['area']} ha")
        st.write(f"**Model:** {data['model']}")
        if data.get('farming_method'):
            st.write(f"**Farming Method:** {data['farming_method']}")
        if data.get('water_source'):
            st.write(f"**Water Source:** {data['water_source']}")
        if data.get('irrigation_type'):
            st.write(f"**Irrigation Type:** {data['irrigation_type']}")
        if data.get('irrigation_method'):
            st.write(f"**Irrigation Method:** {data['irrigation_method']}")
        if data.get('planting_method'):
            st.write(f"**Planting Method:** {data['planting_method']}")
        if data.get('last_fertilizers_used'):
            st.write(f"**Last Fertilizers:** {', '.join(data['last_fertilizers_used'])}")
        if data.get('last_fertilizer_date'):
            st.write(f"**Last Fertilizer Date:** {data['last_fertilizer_date']}")
        if data.get('soil_texture'):
            st.write(f"**Soil Texture:** {data['soil_texture']}")
        if data.get('drainage'):
            st.write(f"**Drainage:** {data['drainage']}")
        if data.get('waterlogging'):
            st.write(f"**Waterlogging:** {data['waterlogging']}")
        if data.get('salinity_signs'):
            st.write(f"**Salinity Signs:** {data['salinity_signs']}")
        if data.get('field_slope'):
            st.write(f"**Field Slope:** {data['field_slope']}")
        if data.get('hardpan_crusting'):
            st.write(f"**Hardpan/Crusting:** {data['hardpan_crusting']}")
        if data.get('irrigation_water_quality'):
            st.write(f"**Water Quality:** {data['irrigation_water_quality']}")
        if data.get('water_reliability'):
            st.write(f"**Water Reliability:** {data['water_reliability']}")
        if data.get('last_season_pest_pressure'):
            st.write(f"**Last Season Pest Pressure:** {data['last_season_pest_pressure']}")
        if data.get('last_season_disease_pressure'):
            st.write(f"**Last Season Disease Pressure:** {data['last_season_disease_pressure']}")
    
    if st.button("🚀 Run All Agents", use_container_width=True, type="primary"):
        with st.spinner("Running all agents..."):
            try:
                from user_input import get_farmer_input_from_session
                farmer_input = get_farmer_input_from_session(st.session_state)
                
                agent_id = st.session_state.selected_agent
                
                # Get coordinates
                lat = st.session_state.location_coords[0] if st.session_state.location_coords else None
                lon = st.session_state.location_coords[1] if st.session_state.location_coords else None
                
                if agent_id == 'soil':
                    output = run_soil_agent(
                        location=farmer_input.location,
                        crop_name=farmer_input.crop_name,
                        crop_variety=farmer_input.crop_variety,
                        sowing_date=farmer_input.sowing_date,
                        area=farmer_input.area,
                        latitude=lat,
                        longitude=lon,
                        soil_type="",
                        custom_prompt=st.session_state.custom_prompts['soil'],
                        model=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                    )
                    
                elif agent_id == 'water':
                    output = water_agent(
                        farmer_input,
                        custom_prompt=st.session_state.custom_prompts['water'],
                        model=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                    )
                    
                elif agent_id == 'weather':
                    output = weather_7day_compact(
                        location=farmer_input.location,
                        latitude=lat,
                        longitude=lon,
                        days=7,
                        save_to_db=True,
                        model_name=st.session_state.selected_model
                    )
                    
                elif agent_id == 'stage':
                    output = stage_generation(
                        farmer_input,
                        model=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                        latitude=lat,
                        longitude=lon,
                        session_state=st.session_state  # PASS SESSION STATE
                    )
                    
                elif agent_id == 'nutrient':
                    output = nutrient_agent(
                        farmer_input,
                        custom_prompt=st.session_state.custom_prompts['nutrient'],
                        model=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                        session_state=st.session_state,  # PASS SESSION STATE
                        latitude=lat,
                        longitude=lon
                    )
                    
                elif agent_id == 'pest':
                    output = pest_agent(
                        farmer_input,
                        custom_prompt=st.session_state.custom_prompts['pest'],
                        model=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                        session_state=st.session_state,
                        latitude=lat,
                        longitude=lon
                    )
                    
                elif agent_id == 'disease':
                    output = disease_agent(
                        farmer_input,
                        custom_prompt=st.session_state.custom_prompts['disease'],
                        model=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                        latitude=lat,
                        longitude=lon
                    )
                    
                elif agent_id == 'irrigation':
                    output = irrigation_agent(
                        farmer_input,
                        custom_prompt=st.session_state.custom_prompts['irrigation'],
                        model_name=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                        latitude=lat,
                        longitude=lon,
                    )
                    
                elif agent_id == 'merge':
                    output = merge_agent(
                        soil=st.session_state.agent_outputs.get('soil'),
                        nutrient=st.session_state.agent_outputs.get('nutrient'),
                        irrigation=st.session_state.agent_outputs.get('irrigation'),
                        pest=st.session_state.agent_outputs.get('pest'),
                        disease=st.session_state.agent_outputs.get('disease'),
                        weather=st.session_state.agent_outputs.get('weather'),
                        stage=st.session_state.agent_outputs.get('stage'),
                        custom_prompt=st.session_state.custom_prompts['merge'],
                        model_name=st.session_state.selected_model,
                        temperature=st.session_state.temperature,
                        max_tokens=st.session_state.max_tokens,
                    )
                
                st.session_state.agent_outputs[agent_id] = output
                st.success("✅ Agent completed successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
# Main Content Area - Agent Selection Pills
st.markdown("### Select an Agent")

# Create agent pills
cols = st.columns(len(AGENTS))
for idx, agent in enumerate(AGENTS):
    with cols[idx]:
        if st.button(
            f"{agent['icon']} {agent['name'].split()[-1]}",
            key=f"agent_{agent['id']}",
            use_container_width=True
        ):
            st.session_state.selected_agent = agent['id']
            st.rerun()

st.markdown("---")

# Display Prompt and Output
if st.session_state.selected_agent:
    selected = next(a for a in AGENTS if a['id'] == st.session_state.selected_agent)
    
    st.markdown(f"## {selected['name']} Agent")
    
    # Create two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📝 Prompt")
        
        # Editable prompt
        prompt_key = st.session_state.selected_agent
        if prompt_key == 'weather':
            st.info("Weather agent uses API - no custom prompt available")
            current_prompt = "Weather data fetched from API"
        else:
            current_prompt = st.session_state.custom_prompts.get(
                prompt_key,
                DEFAULT_PROMPTS.get(prompt_key, "")
            )
            
            edited_prompt = st.text_area(
                "Edit Prompt:",
                value=current_prompt,
                height=400,
                key=f"prompt_editor_{prompt_key}"
            )
            
            st.session_state.custom_prompts[prompt_key] = edited_prompt
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 Reset to Default", key=f"reset_{prompt_key}"):
                    st.session_state.custom_prompts[prompt_key] = DEFAULT_PROMPTS[prompt_key]
                    st.rerun()
            with col_b:
                st.download_button(
                    "📥 Download",
                    data=edited_prompt,
                    file_name=f"{prompt_key}_prompt.txt",
                    mime="text/plain"
                )
    
    with col2:
        st.markdown("### 🎯 Output")
        
        # Run button
        if st.button(f"▶️ Run {selected['name']} Agent", type="primary", use_container_width=True):
            with st.spinner(f"Running {selected['name']} agent..."):
                try:
                    farmer_input = FarmerInput(
                        location=st.session_state.get("location_name") or location_name,
                        crop_name=crop_name,
                        crop_variety=crop_variety,
                        sowing_date=sowing_date.strftime("%Y-%m-%d"),
                        area=area,
                        previous_crop_sowed=previous_crop_sowed,
                        irrigation_type=st.session_state.get('irrigation_type', 'rainfed'),
                        irrigation_method=st.session_state.get('irrigation_method', None),
                        water_source=st.session_state.get('water_source', None),
                        farming_method=st.session_state.get('farming_method', None),
                        planting_method=st.session_state.get('planting_method', None),
                        last_fertilizers_used=st.session_state.get('last_fertilizers_used', None),
                        last_fertilizer_date=st.session_state.get('last_fertilizer_date', None),
                        soil_type=None,
                    )
                    
                    agent_id = st.session_state.selected_agent
                    
                    if agent_id == 'soil':
                        output = run_soil_agent(
                            location=farmer_input.location,
                            crop_name=farmer_input.crop_name,
                            crop_variety=farmer_input.crop_variety,
                            sowing_date=farmer_input.sowing_date,
                            area=farmer_input.area,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            soil_type="",
                            custom_prompt=st.session_state.custom_prompts['soil'],
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                        )
                        
                        from backend.init_db import SessionLocal
                        from backend.data_store import save_soil
                        with SessionLocal() as session:
                            save_soil(
                                session,
                                location=farmer_input.location,
                                crop_name=farmer_input.crop_name,
                                model_name=st.session_state.selected_model,
                                prompt=st.session_state.custom_prompts['soil'],
                                output=output
                            )
                    elif agent_id == 'water':
                        output = water_agent(
                            farmer_input,
                            custom_prompt=st.session_state.custom_prompts['water'],
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                        )
                        
                        from backend.init_db import SessionLocal
                        from backend.data_store import save_water
                        with SessionLocal() as session:
                            save_water(
                                session,
                                location=farmer_input.location,
                                crop_name=farmer_input.crop_name,
                                model_name=st.session_state.selected_model,
                                prompt=st.session_state.custom_prompts['water'],
                                output=output
                            )
                    elif agent_id == 'weather':
                        output = weather_7day_compact(
                            location=location_name,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            days=7,
                            save_to_db=True,
                            model_name=st.session_state.selected_model
                        )
                        # from backend.init_db import SessionLocal
                        # from backend.data_store import save_weather
                        # import json
                        # with SessionLocal() as session:
                        #     output_to_save = json.dumps(output, ensure_ascii=False) if isinstance(output, dict) else output
                        #     save_weather(
                        #         session,
                        #         location=farmer_input.location,
                        #         crop_name=farmer_input.crop_name,
                        #         prompt="Weather agent uses API - no custom prompt available",
                        #         output=output_to_save
                        #     )
                    elif agent_id == 'stage':
                        output = stage_generation(
                            farmer_input,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None
                        )
                    elif agent_id == 'nutrient':
                        output = nutrient_agent(
                            farmer_input,
                            custom_prompt=st.session_state.custom_prompts['nutrient'],
                            # soil_text=soil_text,
                            # water_text=water_text,
                            # weather_text=weather_text,
                            # stages_text=stage_output,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            session_state=st.session_state,  # PASS SESSION STATE
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None
                        )
                    elif agent_id == 'pest':
                        output = pest_agent(
                            farmer_input,
                            custom_prompt=st.session_state.custom_prompts['pest'],
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            session_state=st.session_state,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None
                        )
                    elif agent_id == 'disease':
                        output = disease_agent(
                            farmer_input,
                            custom_prompt=st.session_state.custom_prompts['disease'],
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None
                        )
                    elif agent_id == 'irrigation':
                        output = irrigation_agent(
                            farmer_input,
                            custom_prompt=st.session_state.custom_prompts['irrigation'],
                            model_name=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                        )
                    elif agent_id == 'merge':
                        output = merge_agent(
                            soil=st.session_state.agent_outputs.get('soil'),
                            nutrient=st.session_state.agent_outputs.get('nutrient'),
                            irrigation=st.session_state.agent_outputs.get('irrigation'),
                            pest=st.session_state.agent_outputs.get('pest'),
                            disease=st.session_state.agent_outputs.get('disease'),
                            weather=st.session_state.agent_outputs.get('weather'),
                            stage=st.session_state.agent_outputs.get('stage'),
                            custom_prompt=st.session_state.custom_prompts['merge'],
                            model_name=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                        )
                    
                    st.session_state.agent_outputs[agent_id] = output
                    st.success("✅ Agent completed successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        
        # Display output
        output = st.session_state.agent_outputs.get(st.session_state.selected_agent, "")
        if isinstance(output, dict) and 'output' in output:
            output_text = (output['output'] or "").strip()
        else:
            output_text = (output or "").strip()
        if output_text:
            st.code(output_text, language="text")
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button(
                "📥 Download Output",
                data=output_text,
                file_name=f"{st.session_state.selected_agent}_output.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("👆 Click 'Run Agent' button to generate output")

else:
    # Welcome screen
    st.info("👆 Click on any agent above to view its prompt and generate output")
    
    st.markdown("""
    ### 🎯 How to Use:
    
    1. **Fill Sidebar Form**: Enter location, crop details, and select AI model
    2. **Select Location on Map**: Draw polygon or place marker to set coordinates
    3. **Click Agent Button**: Choose any agent from the pills above
    4. **Edit Prompt** (optional): Customize the agent's behavior
    5. **Run Agent**: Click the "Run" button to generate output
    6. **Run All**: Use "Run All Agents" button in sidebar for batch execution
    
    ### ✨ Features:
    - 🗺️ **Interactive Map**: Draw polygons or place markers to select your farm location
    - 🤖 **Model Selection**: Choose from multiple Claude AI models
    - ✏️ **Editable Prompts**: Customize each agent's behavior
    - 📥 **Download**: Save prompts and outputs individually
    - 🚀 **Batch Mode**: Run all agents at once from sidebar
    """)

st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>🌾 Crop Advisory System | Powered by AI</p>",
    unsafe_allow_html=True
)