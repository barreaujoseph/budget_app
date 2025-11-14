from db import engine
from sqlalchemy import text

# -----------------------------
# Script qui envoie les données vers PostgreSQL
# -----------------------------

print("🔄 Envoi des données vers PostgreSQL...")
print("Connexion utilisée :", engine)

# ✅ Forcer un index propre pour générer la colonne 'id'
df = df.reset_index(drop=True)

# ✅ Forcer la suppression de l'ancienne table
with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS operations;"))

# ✅ Envoi du DataFrame avec index comme colonne 'id'
df.to_sql(
    "operations",
    engine,
    if_exists="replace",
    index=True,
    index_label="id"
)

# ✅ Ajouter la colonne Traitee si elle n'existe pas déjà
with engine.begin() as conn:
    conn.execute(text("""
        ALTER TABLE operations_old
        ADD COLUMN IF NOT EXISTS "Traitee" BOOLEAN DEFAULT FALSE;
    """))

print("✅ Données envoyées dans PostgreSQL avec colonne id + Traitee")
