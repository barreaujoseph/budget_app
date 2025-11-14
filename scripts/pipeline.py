from scripts.A_traitement_donnees import traiter_fichier_bancaire
from scripts.B_depenses import classifier_operations
import pandas as pd
import re
import pandas as pd
from rapidfuzz import process, fuzz
from sqlalchemy import text
from db import engine  # Ton objet engine PostgreSQL (depuis db.py)


# ======================================================
# 1. Récupérer données postgresql
# 2. Retraiter fichier bancaire
# 3. Appliquer regex
# 4. Concaténer 
#5. Envoyer vers postgresql
# ======================================================

# 1. Récupérer données postgresql

print("📡 Connexion à la base Railway...")
df_remote = pd.read_sql("SELECT * FROM operations;", engine)
print(f"✅ Données récupérées : {len(df_remote)} lignes")

# 2. Retraiter fichier bancaire
df_nouveau = classifier_operations("CA20251114_091415.xlsx")

# 3. Appliquer regex
