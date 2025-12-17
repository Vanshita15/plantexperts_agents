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

try:
    from backend.init_db import init_db
    init_db()
except Exception:
    pass

def _load_prompt_preference(agent_id: str):
    try:
        from backend.init_db import SessionLocal
        from backend.data_store import get_prompt_preference
        with SessionLocal() as session:
            pref = get_prompt_preference(session, agent_id)
            if pref is None:
                return None
            return {
                'selected_source': pref.selected_source,
                'selected_prompt': pref.selected_prompt,
            }
    except Exception:
        return None


def _save_prompt_preference(agent_id: str, selected_source: str, selected_prompt: str = None):
    try:
        from backend.init_db import SessionLocal
        from backend.data_store import upsert_prompt_preference
        with SessionLocal() as session:
            upsert_prompt_preference(
                session,
                agent_id=agent_id,
                selected_source=selected_source,
                selected_prompt=selected_prompt,
            )
    except Exception:
        pass


def _save_prompt_event(agent_id: str, prompt_source: str, event_type: str, prompt: str):
    try:
        from backend.init_db import SessionLocal
        from backend.data_store import save_prompt_event
        with SessionLocal() as session:
            save_prompt_event(
                session,
                agent_id=agent_id,
                prompt_source=prompt_source,
                event_type=event_type,
                prompt=prompt,
            )
    except Exception:
        pass


def _get_recent_prompt_events(agent_id: str, limit: int = 5):
    try:
        from backend.init_db import SessionLocal
        from backend.data_store import get_recent_prompt_events
        with SessionLocal() as session:
            return get_recent_prompt_events(session, agent_id, limit=limit)
    except Exception:
        return []


def _orm_to_dict(obj):
    if obj is None:
        return None
    try:
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    except Exception:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith('_')}


def _fetch_latest_db_snapshot(limit: int = 20):
    try:
        from backend.init_db import SessionLocal
        from backend.db_models import Soil, Water, Weather, Stage, Nutrient, Pest, Disease, Irrigation, Merge
        with SessionLocal() as session:
            def _q(model):
                q = session.query(model).order_by(model.created_at.desc())
                if limit is None:
                    return q.all()
                return q.limit(limit).all()
            return {
                'soil': _q(Soil),
                'water': _q(Water),
                'weather': _q(Weather),
                'stage': _q(Stage),
                'nutrient': _q(Nutrient),
                'pest': _q(Pest),
                'disease': _q(Disease),
                'irrigation': _q(Irrigation),
                'merge': _q(Merge),
            }
    except Exception:
        return None


def _render_db_snapshot(snapshot, title: str = "Database (latest rows)"):
    st.markdown(f"## {title}")
    if not snapshot:
        st.caption("No snapshot available.")
        return

    def _df(rows):
        return [_orm_to_dict(r) for r in (rows or [])]

    tab_soil, tab_water, tab_weather, tab_stage, tab_nutrient, tab_pest, tab_disease, tab_irrigation, tab_merge = st.tabs([
        "Soil",
        "Water",
        "Weather",
        "Stage",
        "Nutrient",
        "Pest",
        "Disease",
        "Irrigation",
        "Merge",
    ])

    with tab_soil:
        st.dataframe(_df(snapshot.get('soil')), use_container_width=True)
    with tab_water:
        st.dataframe(_df(snapshot.get('water')), use_container_width=True)
    with tab_weather:
        st.dataframe(_df(snapshot.get('weather')), use_container_width=True)
    with tab_stage:
        st.dataframe(_df(snapshot.get('stage')), use_container_width=True)
    with tab_nutrient:
        st.dataframe(_df(snapshot.get('nutrient')), use_container_width=True)
    with tab_pest:
        st.dataframe(_df(snapshot.get('pest')), use_container_width=True)
    with tab_disease:
        st.dataframe(_df(snapshot.get('disease')), use_container_width=True)
    with tab_irrigation:
        st.dataframe(_df(snapshot.get('irrigation')), use_container_width=True)
    with tab_merge:
        st.dataframe(_df(snapshot.get('merge')), use_container_width=True)


def _estimate_tokens(text: str, model_name: str = "") -> int:
    if not text:
        return 0

    try:
        import tiktoken

        m = (model_name or "").strip()
        try:
            enc = tiktoken.encoding_for_model(m)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Rough fallback: ~4 chars per token
        return max(1, int(len(text) / 4))


def _estimate_total_tokens_for_run(run_id: int) -> int:
    if not run_id:
        return 0

    try:
        from backend.init_db import SessionLocal
        from backend.data_store import get_run_snapshot

        with SessionLocal() as session:
            snapshot = get_run_snapshot(session, run_id)

        if not snapshot:
            return 0

        linked = snapshot.get('linked') or {}

        def _sum(rows, extra_rows=None):
            prompt_tokens = 0
            completion_tokens = 0
            seen_ids = set()

            def _iter(all_rows):
                for rr in (all_rows or []):
                    d = _orm_to_dict(rr) or {}
                    rid = d.get('id')
                    if rid is not None:
                        if rid in seen_ids:
                            continue
                        seen_ids.add(rid)
                    yield d

            for d in _iter(rows):
                model_name = d.get('model_name') or ""
                p = d.get('prompt')
                o = d.get('output')
                prompt_tokens += _estimate_tokens(str(p) if p is not None else "", model_name=model_name)
                completion_tokens += _estimate_tokens(str(o) if o is not None else "", model_name=model_name)

            for d in _iter(extra_rows):
                model_name = d.get('model_name') or ""
                p = d.get('prompt')
                o = d.get('output')
                prompt_tokens += _estimate_tokens(str(p) if p is not None else "", model_name=model_name)
                completion_tokens += _estimate_tokens(str(o) if o is not None else "", model_name=model_name)

            return prompt_tokens + completion_tokens

        total = 0
        total += _sum(snapshot.get('soil'), extra_rows=linked.get('soil'))
        total += _sum(snapshot.get('water'), extra_rows=linked.get('water'))
        total += _sum(snapshot.get('weather'), extra_rows=linked.get('weather'))
        total += _sum(snapshot.get('stage'))
        total += _sum(snapshot.get('nutrient'))
        total += _sum(snapshot.get('pest'))
        total += _sum(snapshot.get('disease'))
        total += _sum(snapshot.get('irrigation'))
        total += _sum(snapshot.get('merge'))
        return total
    except Exception:
        return 0


def _estimate_token_breakdown_for_run(run_id: int):
    if not run_id:
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

    try:
        from backend.init_db import SessionLocal
        from backend.data_store import get_run_snapshot

        with SessionLocal() as session:
            snapshot = get_run_snapshot(session, run_id)

        if not snapshot:
            return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

        linked = snapshot.get('linked') or {}

        def _sum_breakdown(rows, extra_rows=None):
            prompt_tokens = 0
            completion_tokens = 0
            seen_ids = set()

            def _iter(all_rows):
                for rr in (all_rows or []):
                    d = _orm_to_dict(rr) or {}
                    rid = d.get('id')
                    if rid is not None:
                        if rid in seen_ids:
                            continue
                        seen_ids.add(rid)
                    yield d

            for d in _iter(rows):
                model_name = d.get('model_name') or ""
                p = d.get('prompt')
                o = d.get('output')
                prompt_tokens += _estimate_tokens(str(p) if p is not None else "", model_name=model_name)
                completion_tokens += _estimate_tokens(str(o) if o is not None else "", model_name=model_name)

            for d in _iter(extra_rows):
                model_name = d.get('model_name') or ""
                p = d.get('prompt')
                o = d.get('output')
                prompt_tokens += _estimate_tokens(str(p) if p is not None else "", model_name=model_name)
                completion_tokens += _estimate_tokens(str(o) if o is not None else "", model_name=model_name)

            return prompt_tokens, completion_tokens

        p_total = 0
        c_total = 0

        for p, c in [
            _sum_breakdown(snapshot.get('soil'), extra_rows=linked.get('soil')),
            _sum_breakdown(snapshot.get('water'), extra_rows=linked.get('water')),
            _sum_breakdown(snapshot.get('weather'), extra_rows=linked.get('weather')),
            _sum_breakdown(snapshot.get('stage')),
            _sum_breakdown(snapshot.get('nutrient')),
            _sum_breakdown(snapshot.get('pest')),
            _sum_breakdown(snapshot.get('disease')),
            _sum_breakdown(snapshot.get('irrigation')),
            _sum_breakdown(snapshot.get('merge')),
        ]:
            p_total += p
            c_total += c

        return {
            'prompt_tokens': p_total,
            'completion_tokens': c_total,
            'total_tokens': p_total + c_total,
        }
    except Exception:
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}


nav = st.radio(
    "Navigation",
    options=["Agents", "Logs"],
    horizontal=True,
    label_visibility="collapsed",
)

if nav == "Logs":
    st.markdown("## Logs")
    try:
        from backend.init_db import SessionLocal
        import importlib
        import backend.data_store as data_store
        data_store = importlib.reload(data_store)

        list_agent_runs = getattr(data_store, 'list_agent_runs', None)
        get_run_snapshot = getattr(data_store, 'get_run_snapshot', None)
        if list_agent_runs is None or get_run_snapshot is None:
            st.error(
                "Logs helpers are missing from backend.data_store. "
                "Please restart Streamlit to reload the latest code."
            )
            st.stop()
        view_runs, view_db = st.tabs(["Runs", "Database"])

        with view_runs:
            show_all = st.checkbox("Show all runs", value=False)
            run_limit = None
            if not show_all:
                run_limit = st.number_input("Max runs to load", min_value=10, max_value=5000, value=200, step=50)

            with SessionLocal() as session:
                runs = list_agent_runs(session, limit=None if show_all else int(run_limit))

            if not runs:
                st.info("No runs logged yet. Run any agent to create a log entry.")
                st.stop()

            run_options = {}
            for r in runs:
                created = getattr(r, 'created_at', None)
                created_str = str(created) if created else ""
                label = f"Run {getattr(r, 'id', '')} | {getattr(r, 'triggered_agent_id', '')} | {created_str}"
                if getattr(r, 'location', None):
                    label += f" | {getattr(r, 'location')}"
                if getattr(r, 'crop_name', None):
                    label += f" | {getattr(r, 'crop_name')}"
                run_options[label] = getattr(r, 'id', None)

            selected_label = st.selectbox("Select a run", options=list(run_options.keys()))
            selected_run_id = run_options.get(selected_label)

            with SessionLocal() as session:
                snapshot = get_run_snapshot(session, selected_run_id)

            if not snapshot:
                st.warning("Run not found.")
                st.stop()

            run_row = snapshot.get('run')
            with st.expander("Run metadata", expanded=True):
                st.json(_orm_to_dict(run_row))

            def _render_rows_with_detail(title: str, rows):
                data = [_orm_to_dict(r) for r in (rows or [])]
                if not data:
                    st.caption("No rows.")
                    return

                st.dataframe(data, use_container_width=True)

                row_id_options = []
                for d in data:
                    rid = d.get('id')
                    if rid is not None:
                        row_id_options.append(rid)

                if not row_id_options:
                    return

                selected_row_id = st.selectbox(
                    f"Open full {title} report",
                    options=row_id_options,
                    key=f"log_select_{title}_{selected_run_id}",
                )
                selected_row = next((d for d in data if d.get('id') == selected_row_id), None)
                if not selected_row:
                    return

                prompt_text = selected_row.get('prompt')
                output_text = selected_row.get('output')

                if prompt_text is not None:
                    st.markdown("**Prompt**")
                    st.text_area(
                        "",
                        value=str(prompt_text),
                        height=220,
                        disabled=True,
                        key=f"log_prompt_{title}_{selected_run_id}_{selected_row_id}",
                    )
                if output_text is not None:
                    st.markdown("**Output**")
                    st.text_area(
                        " ",
                        value=str(output_text),
                        height=420,
                        disabled=True,
                        key=f"log_output_{title}_{selected_run_id}_{selected_row_id}",
                    )

            linked = snapshot.get('linked') or {}

            tab_soil, tab_water, tab_weather, tab_stage, tab_nutrient, tab_pest, tab_disease, tab_irrigation, tab_merge = st.tabs([
                "Soil",
                "Water",
                "Weather",
                "Stage",
                "Nutrient",
                "Pest",
                "Disease",
                "Irrigation",
                "Merge",
            ])

            with tab_soil:
                _render_rows_with_detail("Soil", snapshot.get('soil'))

            with tab_water:
                _render_rows_with_detail("Water", snapshot.get('water'))

            with tab_weather:
                _render_rows_with_detail("Weather", snapshot.get('weather'))

            with tab_stage:
                st.markdown("### Stage")
                _render_rows_with_detail("Stage", snapshot.get('stage'))

                st.markdown("### Dependencies used by Stage")
                stage_rows = snapshot.get('stage') or []
                if stage_rows:
                    stage_deps = []
                    for srow in stage_rows:
                        stage_deps.append({
                            'stage_id': getattr(srow, 'id', None),
                            'soil_id': getattr(srow, 'soil_id', None),
                            'water_id': getattr(srow, 'water_id', None),
                            'weather_id': getattr(srow, 'weather_id', None),
                        })
                    st.dataframe(stage_deps, use_container_width=True)
                else:
                    st.caption("No Stage rows.")

                dep_soil, dep_water, dep_weather = st.tabs([
                    "Soil (referenced)",
                    "Water (referenced)",
                    "Weather (referenced)",
                ])
                with dep_soil:
                    _render_rows_with_detail("Soil_ref", linked.get('soil'))
                with dep_water:
                    _render_rows_with_detail("Water_ref", linked.get('water'))
                with dep_weather:
                    _render_rows_with_detail("Weather_ref", linked.get('weather'))

            with tab_nutrient:
                _render_rows_with_detail("Nutrient", snapshot.get('nutrient'))

            with tab_pest:
                _render_rows_with_detail("Pest", snapshot.get('pest'))

            with tab_disease:
                _render_rows_with_detail("Disease", snapshot.get('disease'))

            with tab_irrigation:
                _render_rows_with_detail("Irrigation", snapshot.get('irrigation'))

            with tab_merge:
                _render_rows_with_detail("Merge", snapshot.get('merge'))

        with view_db:
            st.markdown("### Database")
            show_all_rows = st.checkbox("Show all rows (may be slow)", value=True)
            db_limit = None
            if not show_all_rows:
                db_limit = st.number_input("Max rows per table", min_value=10, max_value=10000, value=500, step=100)
            _render_db_snapshot(_fetch_latest_db_snapshot(limit=None if show_all_rows else int(db_limit)), title="Database")

        st.stop()
    except Exception as e:
        st.error(f"Failed to load logs: {e}")
        st.stop()


if nav == "Agents":
    with st.expander("Tokens", expanded=False):
        last_run_id = st.session_state.get('last_run_id')
        if last_run_id is None:
            st.caption("Run any agent to see token usage.")
        else:
            tok = _estimate_token_breakdown_for_run(last_run_id)
            st.markdown(f"**Prompt tokens (latest run):** {tok.get('prompt_tokens', 0)}")
            st.markdown(f"**Generation tokens (latest run):** {tok.get('completion_tokens', 0)}")
            st.markdown(f"**Total tokens (latest run):** {tok.get('total_tokens', 0)}")


# Initialize session state
if 'selected_agent' not in st.session_state:
    st.session_state.selected_agent = None

if 'agent_outputs' not in st.session_state:
    st.session_state.agent_outputs = {}

if 'custom_prompts' not in st.session_state:
    st.session_state.custom_prompts = {}

if 'prompt_source_preference' not in st.session_state:
    st.session_state.prompt_source_preference = {}
if 'temperature' not in st.session_state:
    st.session_state.temperature = 0.2
if 'max_tokens' not in st.session_state:
    st.session_state.max_tokens = 1500

if 'location_coords' not in st.session_state:
    st.session_state.location_coords = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "claude-sonnet-4-20250514"

if 'last_run_id' not in st.session_state:
    st.session_state.last_run_id = None

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

if 'default_prompts_snapshot' not in st.session_state:
    st.session_state.default_prompts_snapshot = {}

for key, value in DEFAULT_PROMPTS.items():
    prev_default = st.session_state.default_prompts_snapshot.get(key)
    if prev_default is not None and st.session_state.custom_prompts.get(key) == prev_default:
        st.session_state.custom_prompts[key] = value
    st.session_state.default_prompts_snapshot[key] = value

# Initialize custom prompts
for key, value in DEFAULT_PROMPTS.items():
    if key not in st.session_state.custom_prompts:
        st.session_state.custom_prompts[key] = value

for key in DEFAULT_PROMPTS.keys():
    if key not in st.session_state.prompt_source_preference:
        pref = _load_prompt_preference(key)
        if pref and pref.get('selected_source') in ('system', 'custom'):
            st.session_state.prompt_source_preference[key] = pref['selected_source']
            if pref.get('selected_source') == 'custom' and pref.get('selected_prompt'):
                st.session_state.custom_prompts[key] = pref['selected_prompt']
        else:
            st.session_state.prompt_source_preference[key] = 'custom'

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
            "GPT-4.1 (API)": "gpt-4.1",
            "Claude 3.5 Sonnet (Anthropic)": "claude-3-5-sonnet-20240620",
            "Claude 3.5 Haiku (Anthropic)": "claude-3-5-haiku-20241022",
            "Gemini 2.5 Flash (Google)": "gemini-2.5-flash",
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
        location_name = st.text_input(
            "Location Name (optional)",
            key="location_name_input",
            value=st.session_state.get("location_name", ""),
            help="Used only if map coordinates not selected",
        )

        if 'last_geocoded_location' not in st.session_state:
            st.session_state.last_geocoded_location = None

        col_loc_a, col_loc_b = st.columns([1, 1])
        with col_loc_a:
            locate_clicked = st.form_submit_button("Locate on map", use_container_width=True)
        with col_loc_b:
            clear_loc_clicked = st.form_submit_button("Clear map location", use_container_width=True)

        if clear_loc_clicked:
            st.session_state.location_coords = None
            st.session_state.last_geocoded_location = None

        if locate_clicked and location_name:
            if st.session_state.last_geocoded_location != location_name:
                try:
                    from weather import geocode_location
                    geo = geocode_location(location_name)
                    if geo and geo.get('latitude') is not None and geo.get('longitude') is not None:
                        st.session_state.location_coords = [geo['latitude'], geo['longitude']]
                        st.session_state.location_name = geo.get('name') or location_name
                        st.session_state.last_geocoded_location = location_name
                        st.rerun()
                    else:
                        st.warning("Could not find this location. Try a more specific name (district/state/country).")
                except Exception as e:
                    st.warning(f"Location lookup failed: {e}")

        st.markdown("**📌 Draw polygon or place marker on map:**")
        
        # Initialize map
        if st.session_state.location_coords is None:
            center = [22.5937, 75.0949]  # Default: Dhar
        else:
            center = st.session_state.location_coords
        
        m = folium.Map(location=center, zoom_start=12)

        try:
            if st.session_state.location_coords is not None:
                folium.Marker(
                    location=st.session_state.location_coords,
                    tooltip=st.session_state.get('location_name', 'Selected location'),
                ).add_to(m)
        except Exception:
            pass

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

                from backend.init_db import SessionLocal
                from backend.data_store import create_agent_run
                with SessionLocal() as session:
                    run = create_agent_run(
                        session,
                        triggered_agent_id="all",
                        location=getattr(farmer_input, 'location', None),
                        crop_name=getattr(farmer_input, 'crop_name', None),
                        crop_variety=getattr(farmer_input, 'crop_variety', None),
                        sowing_date=getattr(farmer_input, 'sowing_date', None),
                        model_name=st.session_state.selected_model,
                    )
                    run_id = run.id
                st.session_state.last_run_id = run_id

                # Get coordinates
                lat = st.session_state.location_coords[0] if st.session_state.location_coords else None
                lon = st.session_state.location_coords[1] if st.session_state.location_coords else None

                # Run each agent under the same run_id
                st.session_state.agent_outputs['soil'] = run_soil_agent(
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
                    run_id=run_id,
                )

                st.session_state.agent_outputs['water'] = water_agent(
                    farmer_input,
                    custom_prompt=st.session_state.custom_prompts['water'],
                    model=st.session_state.selected_model,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['weather'] = weather_7day_compact(
                    location=farmer_input.location,
                    latitude=lat,
                    longitude=lon,
                    days=7,
                    save_to_db=True,
                    model_name=st.session_state.selected_model,
                    crop_name=farmer_input.crop_name,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['stage'] = stage_generation(
                    farmer_input,
                    model=st.session_state.selected_model,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    latitude=lat,
                    longitude=lon,
                    session_state=st.session_state,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['nutrient'] = nutrient_agent(
                    farmer_input,
                    custom_prompt=st.session_state.custom_prompts['nutrient'],
                    model=st.session_state.selected_model,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    session_state=st.session_state,
                    latitude=lat,
                    longitude=lon,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['pest'] = pest_agent(
                    farmer_input,
                    custom_prompt=st.session_state.custom_prompts['pest'],
                    model=st.session_state.selected_model,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    session_state=st.session_state,
                    latitude=lat,
                    longitude=lon,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['disease'] = disease_agent(
                    farmer_input,
                    custom_prompt=st.session_state.custom_prompts['disease'],
                    model=st.session_state.selected_model,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    session_state=st.session_state,
                    latitude=lat,
                    longitude=lon,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['irrigation'] = irrigation_agent(
                    farmer_input,
                    custom_prompt=st.session_state.custom_prompts['irrigation'],
                    model_name=st.session_state.selected_model,
                    temperature=st.session_state.temperature,
                    max_tokens=st.session_state.max_tokens,
                    session_state=st.session_state,
                    latitude=lat,
                    longitude=lon,
                    run_id=run_id,
                )

                st.session_state.agent_outputs['merge'] = merge_agent(
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
                st.success("✅ Agent completed successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# Main Content Area - Agent Selection
if st.session_state.form_submitted:
    st.markdown("### Select an Agent")
    cols = st.columns(len(AGENTS))
    for idx, agent in enumerate(AGENTS):
        with cols[idx]:
            if st.button(
                f"{agent['icon']} {agent['name'].split()[-1]}",
                key=f"agent_{agent['id']}",
                use_container_width=True,
            ):
                st.session_state.selected_agent = agent['id']
                st.rerun()

    st.markdown("---")

else:
    st.info("👈 Submit inputs from the sidebar to enable agent runs")

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
            selected_source = st.session_state.prompt_source_preference.get(prompt_key, 'custom')

            selected_source = st.radio(
                "Prompt to use next",
                options=['custom', 'system'],
                index=0 if selected_source == 'custom' else 1,
                horizontal=True,
                key=f"prompt_source_{prompt_key}",
            )
            st.session_state.prompt_source_preference[prompt_key] = selected_source
            _save_prompt_preference(
                agent_id=prompt_key,
                selected_source=selected_source,
                selected_prompt=st.session_state.custom_prompts.get(prompt_key) if selected_source == 'custom' else None,
            )

            # Detect most recent custom prompt from history
            recent_events = _get_recent_prompt_events(prompt_key, limit=25)
            most_recent_custom = None
            for evt in recent_events:
                if getattr(evt, 'prompt_source', None) == 'custom':
                    most_recent_custom = getattr(evt, 'prompt', None)
                    break

            tab_system, tab_active, tab_recent = st.tabs([
                "Prompt",
                "Active Prompt",
                "Most Recent Custom",
            ])

            with tab_system:
                st.text_area(
                    "Prompt (read-only)",
                    value=DEFAULT_PROMPTS.get(prompt_key, ""),
                    height=400,
                    disabled=True,
                    key=f"system_prompt_view_{prompt_key}",
                )

            with tab_active:
                editor_key = f"prompt_editor_{prompt_key}"
                pending_editor_key = f"pending_{editor_key}"
                if pending_editor_key in st.session_state:
                    st.session_state[editor_key] = st.session_state.pop(pending_editor_key)

                edited_prompt = st.text_area(
                    "Edit Custom Prompt:",
                    value=st.session_state.custom_prompts.get(prompt_key, DEFAULT_PROMPTS.get(prompt_key, "")),
                    height=400,
                    key=editor_key,
                )

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("💾 Save Custom Prompt", key=f"save_custom_{prompt_key}"):
                        st.session_state.custom_prompts[prompt_key] = edited_prompt
                        st.session_state[pending_editor_key] = edited_prompt
                        _save_prompt_event(prompt_key, 'custom', 'edited', edited_prompt)
                        _save_prompt_preference(prompt_key, 'custom', edited_prompt)
                        st.session_state.prompt_source_preference[prompt_key] = 'custom'
                        st.rerun()
                with col_b:
                    if st.button("🔄 Reset to Default", key=f"reset_{prompt_key}"):
                        st.session_state.custom_prompts[prompt_key] = DEFAULT_PROMPTS[prompt_key]
                        st.session_state[pending_editor_key] = DEFAULT_PROMPTS[prompt_key]
                        _save_prompt_event(prompt_key, 'custom', 'edited', DEFAULT_PROMPTS[prompt_key])
                        _save_prompt_preference(prompt_key, 'custom', DEFAULT_PROMPTS[prompt_key])
                        st.session_state.prompt_source_preference[prompt_key] = 'custom'
                        st.rerun()
                with col_c:
                    st.download_button(
                        "📥 Download",
                        data=edited_prompt,
                        file_name=f"{prompt_key}_prompt.txt",
                        mime="text/plain",
                        key=f"download_{prompt_key}",
                    )

                st.markdown("#### Last 5 prompts (edited/used)")
                last5 = _get_recent_prompt_events(prompt_key, limit=5)
                if not last5:
                    st.caption("No prompt history yet.")
                else:
                    for evt in last5:
                        evt_source = getattr(evt, 'prompt_source', '')
                        evt_type = getattr(evt, 'event_type', '')
                        evt_prompt = getattr(evt, 'prompt', '')
                        evt_time = getattr(evt, 'created_at', None)
                        label = f"{evt_type} / {evt_source}"
                        if evt_time:
                            label = f"{label} @ {evt_time}"

                        with st.expander(label, expanded=False):
                            st.text_area(
                                "Prompt",
                                value=evt_prompt,
                                height=220,
                                disabled=True,
                                key=f"hist_prompt_{prompt_key}_{getattr(evt, 'id', label)}",
                            )
                            col_u, col_g = st.columns(2)
                            with col_u:
                                if st.button("Use this prompt next", key=f"reuse_{prompt_key}_{getattr(evt, 'id', label)}"):
                                    st.session_state.custom_prompts[prompt_key] = evt_prompt
                                    st.session_state[pending_editor_key] = evt_prompt
                                    st.session_state.prompt_source_preference[prompt_key] = 'custom'
                                    _save_prompt_preference(prompt_key, 'custom', evt_prompt)
                                    st.rerun()
                            with col_g:
                                if st.button("Generate report using this prompt", key=f"gen_{prompt_key}_{getattr(evt, 'id', label)}"):
                                    st.session_state.custom_prompts[prompt_key] = evt_prompt
                                    st.session_state[pending_editor_key] = evt_prompt
                                    st.session_state.prompt_source_preference[prompt_key] = 'custom'
                                    _save_prompt_preference(prompt_key, 'custom', evt_prompt)
                                    st.session_state.auto_run_agent = prompt_key
                                    st.session_state.auto_run_prompt = evt_prompt
                                    st.rerun()

            with tab_recent:
                st.text_area(
                    "Most recent custom prompt (read-only)",
                    value=most_recent_custom or "No custom prompt found yet.",
                    height=400,
                    disabled=True,
                    key=f"most_recent_custom_{prompt_key}",
                )
    
    with col2:
        st.markdown("### 🎯 Output")
        
        # Run button
        auto_run = (
            st.session_state.get('auto_run_agent') == st.session_state.selected_agent
            and st.session_state.get('auto_run_prompt')
        )

        run_clicked = st.button(f"▶️ Run {selected['name']} Agent", type="primary", use_container_width=True)
        if auto_run or run_clicked:
            with st.spinner(f"Running {selected['name']} agent..."):
                try:
                    from user_input import get_farmer_input_from_session
                    farmer_input = get_farmer_input_from_session(st.session_state)

                    from backend.init_db import SessionLocal
                    from backend.data_store import create_agent_run
                    with SessionLocal() as session:
                        run = create_agent_run(
                            session,
                            triggered_agent_id=st.session_state.selected_agent,
                            location=getattr(farmer_input, 'location', None),
                            crop_name=getattr(farmer_input, 'crop_name', None),
                            crop_variety=getattr(farmer_input, 'crop_variety', None),
                            sowing_date=getattr(farmer_input, 'sowing_date', None),
                            model_name=st.session_state.selected_model,
                        )
                        run_id = run.id
                    st.session_state.last_run_id = run_id

                    agent_id = st.session_state.selected_agent

                    prompt_source = st.session_state.prompt_source_preference.get(agent_id, 'custom')
                    if auto_run:
                        prompt_source = 'custom'
                        prompt_to_use = st.session_state.get('auto_run_prompt')
                    elif prompt_source == 'system':
                        prompt_to_use = DEFAULT_PROMPTS.get(agent_id, "")
                    else:
                        prompt_to_use = st.session_state.custom_prompts.get(agent_id, DEFAULT_PROMPTS.get(agent_id, ""))

                    # Clear auto-run flags early to prevent repeat execution on rerun
                    if auto_run:
                        st.session_state.auto_run_agent = None
                        st.session_state.auto_run_prompt = None

                    if agent_id != 'weather' and prompt_to_use:
                        _save_prompt_event(agent_id, prompt_source, 'used', prompt_to_use)

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
                            custom_prompt=prompt_to_use,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            run_id=run_id,
                        )
                    elif agent_id == 'water':
                        output = water_agent(
                            farmer_input,
                            custom_prompt=prompt_to_use,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            run_id=run_id,
                        )
                    elif agent_id == 'weather':
                        output = weather_7day_compact(
                            location=location_name,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            days=7,
                            save_to_db=True,
                            model_name=st.session_state.selected_model,
                            crop_name=farmer_input.crop_name,
                            run_id=run_id,
                        )
                        #     )
                    elif agent_id == 'stage':
                        output = stage_generation(
                            farmer_input,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            session_state=st.session_state,
                            run_id=run_id,
                        )
                    elif agent_id == 'nutrient':
                        output = nutrient_agent(
                            farmer_input,
                            custom_prompt=prompt_to_use,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            session_state=st.session_state,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            run_id=run_id,
                        )
                    elif agent_id == 'pest':
                        output = pest_agent(
                            farmer_input,
                            custom_prompt=prompt_to_use,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            session_state=st.session_state,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            run_id=run_id,
                        )
                    elif agent_id == 'disease':
                        output = disease_agent(
                            farmer_input,
                            custom_prompt=prompt_to_use,
                            model=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            run_id=run_id,
                        )
                    elif agent_id == 'irrigation':
                        output = irrigation_agent(
                            farmer_input,
                            custom_prompt=prompt_to_use,
                            model_name=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                            latitude=st.session_state.location_coords[0] if st.session_state.location_coords else None,
                            longitude=st.session_state.location_coords[1] if st.session_state.location_coords else None,
                            run_id=run_id,
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
                            custom_prompt=prompt_to_use,
                            model_name=st.session_state.selected_model,
                            temperature=st.session_state.temperature,
                            max_tokens=st.session_state.max_tokens,
                        )

                        try:
                            from backend.init_db import SessionLocal
                            from backend.data_store import save_merge

                            def _txt(v):
                                if isinstance(v, dict) and 'output' in v:
                                    return v.get('output')
                                return v

                            with SessionLocal() as session:
                                save_merge(
                                    session,
                                    soil=_txt(st.session_state.agent_outputs.get('soil')),
                                    nutrient=_txt(st.session_state.agent_outputs.get('nutrient')),
                                    irrigation=_txt(st.session_state.agent_outputs.get('irrigation')),
                                    pest=_txt(st.session_state.agent_outputs.get('pest')),
                                    disease=_txt(st.session_state.agent_outputs.get('disease')),
                                    weather=_txt(st.session_state.agent_outputs.get('weather')),
                                    stage=_txt(st.session_state.agent_outputs.get('stage')),
                                    model_name=st.session_state.selected_model,
                                    prompt=prompt_to_use,
                                    output=output,
                                    run_id=run_id,
                                )
                        except Exception:
                            pass
                    
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