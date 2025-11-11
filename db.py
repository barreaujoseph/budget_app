import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()  # Charge .env en local

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///budget.db")

engine = create_engine(DATABASE_URL)
