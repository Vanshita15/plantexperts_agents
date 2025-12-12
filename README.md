# Crop Advisory System (Agentic AI)

A Streamlit-based crop advisory app that collects farmer inputs (crop + location + farm practices + field observations) and runs a set of specialized AI **agents** to generate actionable, stage-wise recommendations.

The system is designed around:
- A shared structured input object: `FarmerInput`
- Independent “expert” agents: Soil, Water, Weather, Stage, Nutrient, Pest, Disease, Irrigation
- A final **Merge Agent** that combines outputs into a single farmer-friendly plan
- Optional database persistence for caching and traceability

---

## What this project does

You enter:
- Location (via map or name)
- Crop, variety, sowing date, area
- Farm practices (irrigation type/method, water source, farming method, fertilizers, etc.)
- Field observations (soil texture/drainage/waterlogging, water quality, last season pressure, etc.)

Then the app:
1. Fetches or generates baseline context (soil/water/weather)
2. Generates crop **growth stages**
3. Generates stage-wise recommendations for:
   - Nutrients
   - Irrigation
   - Pest
   - Disease
4. Optionally merges everything into a final combined advisory

---

## Repository structure (high level)

- `Agents/`
  - `stream_testing.py` — Streamlit UI + orchestration
  - `user_input.py` — `FarmerInput` dataclass + `get_farmer_input_from_session()`
  - `soil.py` — Soil agent
  - `water.py` — Water agent
  - `weather.py` — Weather retrieval (Open-Meteo)
  - `stage_agent.py` — Stage planner + stage generation
  - `nutrient_agent.py` — Nutrient agent
  - `pest.py` — Pest agent
  - `disease.py` — Disease agent
  - `irrigation.py` — Irrigation agent
  - `merge_agent.py` — Merge agent (final combined report)
  - `agent_helper.py` — DB/session caching helpers for dependent data

- `backend/`
  - `db_models.py` — SQLAlchemy ORM models (Soil, Water, Weather, Stage, Pest, Disease, Irrigation, Nutrient)
  - `data_store.py` — helper functions to save/read cached results (e.g. `save_soil`, `save_stage`, `save_irrigation`)
  - `init_db.py` — DB session initialization (SQLite by default)

---

## Core concept: `FarmerInput`

All agents should prefer receiving a `FarmerInput` object so the interface is consistent.

File: `Agents/user_input.py`

It contains:
- **Crop basics**: crop name, variety, sowing date, area
- **Farm practices**: irrigation type/method, water source, fertilizers, planting method, farming method
- **Field observations**: soil texture/drainage/waterlogging, salinity signs, hardpan/crusting, slope, water quality/reliability, last season pest/disease pressure
- **Coordinates**: latitude/longitude from the map

Streamlit stores inputs in `st.session_state`, and `get_farmer_input_from_session()` builds a `FarmerInput` from that state.

---

## Agent pipeline (how it works)

### Dependency flow
Many agents depend on “baseline” context:
- **Soil** report
- **Water** report
- **Weather** report
- **Stage** report

To avoid repeated calls:
- `agent_helper.py` uses **session_state first**, then **DB cache**, and finally calls the relevant agent/API if needed.

### Agents
- **Soil Agent** (`Agents/soil.py`)
  - Produces a soil analysis report

- **Water Agent** (`Agents/water.py`)
  - Produces water availability/quality summary

- **Weather** (`Agents/weather.py`)
  - Uses Open-Meteo to fetch weather data

- **Stage Agent** (`Agents/stage_agent.py`)
  - `stage_planner_agent(...)`: pure LLM generation of stage plan
  - `stage_generation(...)`: orchestration (fetch deps + generate + compute current stage + optional DB save)

- **Nutrient Agent** (`Agents/nutrient_agent.py`)
  - Stage-wise nutrient plan

- **Pest Agent** (`Agents/pest.py`)
  - Stage-wise pest risks + actions

- **Disease Agent** (`Agents/disease.py`)
  - Stage-wise disease risks + actions

- **Irrigation Agent** (`Agents/irrigation.py`)
  - Stage-wise irrigation schedule; can save into `Irrigation` table

- **Merge Agent** (`Agents/merge_agent.py`)
  - Combines all outputs into a final consolidated advisory

---

## Model settings (Temperature / Max Tokens)

In the Streamlit UI, you can set:
- `temperature`
- `max_tokens`

These are passed to agents that support them (soil/water/stage/nutrient/pest/disease/irrigation/merge).

---

## Database & caching

The project uses SQLAlchemy ORM models in `backend/db_models.py`.

Why DB:
- Cache expensive calls (soil/water/stage/weather)
- Track what model/prompt produced each output
- Link downstream outputs to upstream dependencies using foreign keys

Example:
- `Irrigation` row stores `stage_id`, `soil_id`, `water_id`, `weather_id`

---

## Setup (Windows)

### 1) Create & activate venv

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 2) Install dependencies

Install based on your environment. Typical packages include:
- `streamlit`
- `streamlit-folium`
- `folium`
- `sqlalchemy`
- `python-dotenv`
- `together`
- `openai`
- `requests`

If you already have a working environment, keep using it.

### 3) Environment variables

Create a `.env` file in the project root if needed:

```env
OPENAI_API_KEY=...
TOGETHER_API_KEY=...
```

Notes:
- Weather uses Open-Meteo (no key required)
- Some agents can run on Together models, some on OpenAI depending on selected model

---

## Run the app

From the project root:

```cmd
streamlit run Agents\stream_testing.py
```

---

## How to use

1. Select a model + set temperature/max_tokens
2. Select location on map (or type location)
3. Enter crop details
4. Fill Farm Practices + Field Observations
5. Click **Submit & Save Inputs**
6. Select an agent tab and click **Run** (or use **Run All Agents**)
7. Optionally use **Merge** to generate the final combined report

---

## Notes / troubleshooting

- **After code changes**: restart Streamlit to reload modules.
- If you see errors like:
  - `got an unexpected keyword argument ...`
  it means a call site is passing an argument the function signature doesn’t accept.

---

## Next improvements (recommended)

- Include field observations directly into prompts for each agent (soil/nutrient/irrigation/pest/disease)
- Add upload/parse of soil test PDF/image (OCR)
- Add export:
  - PDF report
  - per-agent JSON
- Add “profiles”: save farms and reload later
- Add language switch (Hindi/English)
- Add validations (e.g., sowing date in future, unrealistic area)

---

## License

Internal / private project (add a license if you plan to open source).
