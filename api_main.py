import os
import sys
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from Agents.weather import weather_7day_compact
from Agents.irrigation import irrigation_agent

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(PROJECT_ROOT, "Agents")
if AGENTS_DIR not in sys.path:
    sys.path.insert(0, AGENTS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


app = FastAPI(title="Crop Advisory API", version="1.0.0")


class WeatherRequest(BaseModel):
    location: Optional[str] = None
    crop_name: str = ""
    days: int = Field(default=7, ge=1, le=16)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    save_to_db: bool = True
    run_id: Optional[int] = None


class IrrigationRequest(BaseModel):
    crop_name: str
    location: str
    sowing_date: Optional[str] = None  # YYYY-MM-DD
    area: Optional[float] = None

    irrigation_type: Optional[str] = "rainfed"
    irrigation_method: Optional[str] = None
    water_source: Optional[str] = None
    water_reliability: Optional[str] = None
    irrigation_water_quality: Optional[str] = None
    soil_texture: Optional[str] = "unknown"
    drainage: Optional[str] = "unknown"
    waterlogging: Optional[str] = "unknown"
    salinity_signs: Optional[str] = "unknown"
    field_slope: Optional[str] = "unknown"
    hardpan_crusting: Optional[str] = "unknown"
    farming_method: Optional[str] = None
    planting_method: Optional[str] = None

    model_name: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2000
    custom_prompt: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    save_to_db: bool = True
    run_id: Optional[int] = None


def _create_run(triggered_agent_id: str, payload: Dict[str, Any]) -> Optional[int]:
    try:
        from backend.init_db import SessionLocal
        from backend.data_store import create_agent_run

        with SessionLocal() as session:
            run = create_agent_run(
                session,
                triggered_agent_id=triggered_agent_id,
                location=payload.get("location"),
                crop_name=payload.get("crop_name") or payload.get("crop"),
                crop_variety=payload.get("crop_variety"),
                sowing_date=payload.get("sowing_date"),
                model_name=payload.get("model_name"),
            )
            return getattr(run, "id", None)
    except Exception:
        return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/weather")
def weather(req: WeatherRequest):
    try:
        run_id = req.run_id
        if run_id is None and req.save_to_db:
            run_id = _create_run(
                "weather",
                {
                    "location": req.location,
                    "crop_name": req.crop_name,
                },
            )

        result = weather_7day_compact(
            location=req.location,
            days=req.days,
            latitude=req.latitude,
            longitude=req.longitude,
            crop_name=req.crop_name,
            save_to_db=req.save_to_db,
            model_name="open-meteo",
            run_id=run_id,
        )

        if isinstance(result, dict):
            return {"run_id": run_id, **result}
        return {"run_id": run_id, "output": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/irrigation")
def irrigation(req: IrrigationRequest):
    try:
        from Agents.user_input import FarmerInput

        run_id = req.run_id
        if run_id is None and req.save_to_db:
            run_id = _create_run(
                "irrigation",
                {
                    "location": req.location,
                    "crop_name": req.crop_name,
                    "sowing_date": req.sowing_date,
                    "model_name": req.model_name,
                },
            )

        farmer_input = FarmerInput(
            crop_name=req.crop_name,
            location=req.location,
            sowing_date=req.sowing_date,
            area=req.area,
            irrigation_type=req.irrigation_type,
            irrigation_method=req.irrigation_method,
            water_source=req.water_source,
            water_reliability=req.water_reliability,
            irrigation_water_quality=req.irrigation_water_quality,
            soil_texture=req.soil_texture,
            drainage=req.drainage,
            waterlogging=req.waterlogging,
            salinity_signs=req.salinity_signs,
            field_slope=req.field_slope,
            hardpan_crusting=req.hardpan_crusting,
            farming_method=req.farming_method,
            planting_method=req.planting_method,
            latitude=req.latitude,
            longitude=req.longitude,
        )

        result = irrigation_agent(
            farmer_input=farmer_input,
            model_name=req.model_name,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            custom_prompt=req.custom_prompt,
            latitude=req.latitude,
            longitude=req.longitude,
            save_to_db=req.save_to_db,
            run_id=run_id,
        )

        if isinstance(result, dict):
            return {"run_id": run_id, **result}
        return {"run_id": run_id, "output": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
