import os
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from .db_models import Base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def _migrate_db():
    """Best-effort schema migration for existing databases (Postgres).

    This project currently uses `create_all`, which doesn't add new columns to
    existing tables. We add the minimal columns/tables needed for the Logs UI.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS agent_runs (
                        id SERIAL PRIMARY KEY,
                        triggered_agent_id VARCHAR NOT NULL,
                        location VARCHAR,
                        crop_name VARCHAR,
                        crop_variety VARCHAR,
                        sowing_date VARCHAR,
                        model_name VARCHAR,
                        created_at TIMESTAMP DEFAULT now()
                    );
                    """
                )
            )

            for table in [
                "soil",
                "water",
                "weather",
                "stage",
                "nutrient",
                "pest",
                "disease",
                "irrigation",
                "merge",
            ]:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES agent_runs(id);"
                    )
                )
    except Exception:
        # Migration is best-effort; app should still be usable without logs.
        pass

def init_db():
    Base.metadata.create_all(engine)
    _migrate_db()

if __name__ == "__main__":
    init_db()
    print("Tables created!")
