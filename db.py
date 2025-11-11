import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()  # Charge .env en local

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise Exception("❌ DATABASE_URL non détecté — vérifie Railway Variables")


engine = create_engine(DATABASE_URL)
