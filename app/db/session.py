import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
db   = os.getenv("POSTGRES_DB", "postgres")
user = os.getenv("POSTGRES_USER", "postgres")
pw   = os.getenv("POSTGRES_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{user}:{pw}@{host}:{port}/{db}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)