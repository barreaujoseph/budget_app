from db import engine
from scripts.B_depenses import df
from sqlalchemy import text

# -----------------------------
# Ancien script qui envoyait vers sqlite
# -----------------------------

# ✅ Assure-toi d'avoir un index propre
df = df.reset_index(drop=True)

print(engine)  # Debug

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS operations;"))

df.to_sql(
    "operations",
    engine,
    if_exists="replace",
    index=True,
    index_label="id"
)

print("✅ Table recréée + upload terminé")
