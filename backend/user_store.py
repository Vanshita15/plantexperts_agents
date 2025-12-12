from sqlalchemy.orm import Session
from .db_models import User

def save_previous_crop_sowed(session: Session, crop_name: str, crop_variety: str, sowing_date: str, previous_crop_sowed: str, location: str, area: str, model_name: str, latitude: str = None, longitude: str = None):
    user = User(
        crop_name=crop_name,
        crop_variety=crop_variety,
        sowing_date=sowing_date,
        previous_crop_sowed=previous_crop_sowed,
        location=location,
        area=area,
        model_name=model_name,
        latitude=latitude,
        longitude=longitude
    )
    session.add(user)
    session.commit()
    print("------------------data is saved in database")
    return user
