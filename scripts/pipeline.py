from scripts.A_traitement_donnees import traiter_fichier_bancaire
from scripts.B_depenses import appliquer_regex, appliquer_fuzzy
import pandas as pd
import re
from openpyxl import load_workbook
import pandas as pd
from rapidfuzz import process, fuzz
from sqlalchemy import text
from db import engine  # Ton objet engine PostgreSQL (depuis db.py)


# ======================================================
# 1. Récupérer données postgresql
# 2. Retraiter fichier bancaire
# 3. Appliquer regex et fuzzy
# 4. Concaténer 
# 5. Envoyer vers postgresql
# ======================================================

# 1. Récupérer données postgresql

print("📡 Connexion à la base Railway...")
df_remote = pd.read_sql("SELECT * FROM operations;", engine)
print(f"✅ Données récupérées : {len(df_remote)} lignes")

# 2. Retraiter fichier bancaire
df_nouveau = traiter_fichier_bancaire("CA20251114_091415.xlsx")
df_nouveau = appliquer_regex(df_nouveau)

# 3. Harmoniser les colonnes
colonnes_communes = list(set(df_remote.columns) & set(df_nouveau.columns))
df_remote_aligne = df_remote[colonnes_communes].copy()
df_nouveau_aligne = df_nouveau[colonnes_communes].copy()

# Filtrer les nouvelles opérations (>= date max)
date_max_remote = df_remote_aligne["Date"].max()
print(f"📅 Dernière date dans df_remote : {date_max_remote.strftime('%d/%m/%Y')}")

df_nouveau_filtre = df_nouveau_aligne[df_nouveau_aligne["Date"] >= date_max_remote]
print(f"🆕 {len(df_nouveau_filtre)} nouvelles opérations à partir du {date_max_remote.strftime('%d/%m/%Y')}.")

# Fusion des datasets
df_concat = pd.concat([df_remote_aligne, df_nouveau_filtre], ignore_index=True)
print(f"🧩 Fusion effectuée : {len(df_concat)} lignes totales avant déduplication.")

# Déduplication ciblée — uniquement sur la date max
mask_date_max = df_concat["Date"] == date_max_remote
df_date_max = df_concat[mask_date_max]

# Détecter les doublons uniquement sur cette date
doublons_date_max = df_date_max.duplicated(subset=["Date", "Libellé", "Montant", "Compte"], keep="first")

# Supprimer uniquement ces doublons
nb_doublons = doublons_date_max.sum()
if nb_doublons > 0:
    print(f"⚠️ {nb_doublons} doublons détectés sur la date {date_max_remote.strftime('%d/%m/%Y')}.")
    df_concat = df_concat[~(mask_date_max & doublons_date_max)]
else:
    print("✅ Aucun doublon détecté sur la date la plus récente.")

print(f"🧹 Après nettoyage : {len(df_concat)} lignes uniques au total.")

# 7. Appliquer regex
test = appliquer_fuzzy(df_concat)

print(df_nouveau['Traitee'].value_counts())