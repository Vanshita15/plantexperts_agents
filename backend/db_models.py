from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import ForeignKey

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String)
    crop_variety = Column(String)
    sowing_date = Column(String)
    previous_crop_sowed = Column(String)
    location = Column(String)
    area = Column(String)
    model_name = Column(String)
    latitude = Column(String)
    longitude = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Soil(Base):
    __tablename__ = "soil"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String)
    crop_name = Column(String)
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Weather(Base):
    __tablename__ = "weather"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String)
    crop_name = Column(String)
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Water(Base):
    __tablename__ = "water"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String)
    crop_name = Column(String)
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Stage(Base):
    __tablename__ = "stage"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String)
    crop_name = Column(String)
    sowing_date = Column(String)
    soil_id = Column(Integer, ForeignKey('soil.id'))
    water_id = Column(Integer, ForeignKey('water.id'))
    weather_id = Column(Integer, ForeignKey('weather.id'))
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Irrigation(Base):
    __tablename__ = "irrigation"
    id = Column(Integer, primary_key=True, autoincrement=True)
    location = Column(String)
    crop_name = Column(String)
    sowing_date = Column(String)
    area = Column(String)
    stage_id = Column(Integer, ForeignKey('stage.id'))
    soil_id = Column(Integer, ForeignKey('soil.id'))
    water_id = Column(Integer, ForeignKey('water.id'))
    weather_id = Column(Integer, ForeignKey('weather.id'))
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Nutrient(Base):
    __tablename__ = "nutrient"
    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String)
    crop_variety = Column(String)
    location = Column(String)
    area = Column(String)
    stage_id = Column(Integer, ForeignKey('stage.id'))
    soil_id = Column(Integer, ForeignKey('soil.id'))
    water_id = Column(Integer, ForeignKey('water.id'))
    weather_id = Column(Integer, ForeignKey('weather.id'))
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Pest(Base):
    __tablename__ = "pest"
    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String)
    crop_variety = Column(String)
    location = Column(String)
    sowing_date = Column(String)
    stage_id = Column(Integer, ForeignKey('stage.id'))
    soil_id = Column(Integer, ForeignKey('soil.id'))
    water_id = Column(Integer, ForeignKey('water.id'))
    weather_id = Column(Integer, ForeignKey('weather.id'))
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Disease(Base):
    __tablename__ = "disease"
    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String)
    crop_variety = Column(String)
    location = Column(String)
    sowing_date = Column(String)
    stage_id = Column(Integer, ForeignKey('stage.id'))
    soil_id = Column(Integer, ForeignKey('soil.id'))
    weather_id = Column(Integer, ForeignKey('weather.id'))
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Merge(Base):
    __tablename__ = "merge"
    id = Column(Integer, primary_key=True, autoincrement=True)
    soil = Column(Text)
    nutrient = Column(Text)
    irrigation = Column(Text)
    pest = Column(Text)
    disease = Column(Text)
    weather = Column(Text)
    stage = Column(Text)
    model_name = Column(String)
    prompt = Column(Text)
    output = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
