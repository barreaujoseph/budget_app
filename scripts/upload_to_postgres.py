
from db import engine
from scripts.depenses import df

df.to_sql("operations", engine, if_exists="replace", index=False)

print("✅ Données envoyées dans PostgreSQL")
print("Connexion utilisée :", engine)
