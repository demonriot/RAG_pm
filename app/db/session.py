import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # helps with dropped connections in containers
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
