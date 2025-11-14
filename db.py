import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# -----------------------------
# Mise en place de la connexion à la base de données PostgreSQL
# -----------------------------

load_dotenv()  # Charge .env en local

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise Exception("❌ DATABASE_URL non détecté — vérifie Railway Variables")


engine = create_engine(DATABASE_URL)

