import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# On cherche d'abord la nouvelle variable, sinon l'ancienne
db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")

if db_url is None:
    raise Exception("❌ Aucune URL de base de données détectée")

# Si l'URL contient "internal", on affiche un avertissement car ça va planter hors de Railway
if "internal" in db_url:
    print("⚠️ Attention : Utilisation d'une adresse interne Railway.")

engine = create_engine(db_url)