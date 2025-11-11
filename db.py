# db.py
import os
from sqlalchemy import create_engine

# En local → SQLite
# En prod → Railway/Supabase (via variable d’environnement DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///budget.db")

engine = create_engine(DATABASE_URL, echo=False)
