
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

cloud_database_url = os.getenv("DATABASE_URL")

if cloud_database_url:
    DATABASE_URL = cloud_database_url.replace(
        "postgres://", "postgresql+psycopg://", 1
    ).replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
else:
    DATABASE_URL = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

def test_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database()")
        )
        print("Connected to database:", result.scalar())


if __name__ == "__main__":
    test_connection()
