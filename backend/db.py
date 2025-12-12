import psycopg2
from contextlib import contextmanager
import os

DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'cropadvisory')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASS = os.getenv('POSTGRES_PASSWORD', 'password')

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_responses (
                id SERIAL PRIMARY KEY,
                agent_name TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
