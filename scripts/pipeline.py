from scripts.A_traitement_donnees import traiter_fichier_bancaire
from scripts.B_depenses import appliquer_regex, appliquer_fuzzy
from sqlalchemy import text
from db import engine
import pandas as pd

# ======================================================
# 1. Lecture depuis PostgreSQL
# ======================================================
print("Connexion à la base PostgreSQL...")
df_remote = pd.read_sql("SELECT * FROM operations;", engine)
print(f"Données existantes : {len(df_remote)} lignes")

# ======================================================
# 2. Traitement du nouveau fichier bancaire
# ======================================================
fichier_excel = "/Users/josephbarreau/Documents/python/expenses_tracker/V2/CA20251229_102636.xlsx"
df_nouveau = traiter_fichier_bancaire(fichier_excel)
df_nouveau = appliquer_regex(df_nouveau)
#df_remote = appliquer_regex(df_remote)

# ======================================================
# 3. Harmonisation des colonnes
# ======================================================
colonnes_communes = list(set(df_remote.columns) & set(df_nouveau.columns))
df_remote_aligne = df_remote[colonnes_communes].copy()
df_nouveau_aligne = df_nouveau[colonnes_communes].copy()

# ======================================================
# 4. Filtrage des nouvelles opérations
# ======================================================
date_max_remote = df_remote_aligne["Date"].max()
print(f"Dernière date dans la base existante : {date_max_remote.strftime('%d/%m/%Y')}")

df_nouveau_filtre = df_nouveau_aligne[df_nouveau_aligne["Date"] >= date_max_remote]
print(f"{len(df_nouveau_filtre)} nouvelles opérations à partir du {date_max_remote.strftime('%d/%m/%Y')}")

# ======================================================
# 5. Fusion et déduplication ciblée
# ======================================================
df_concat = pd.concat([df_remote_aligne, df_nouveau_filtre], ignore_index=True)
print(f"Fusion effectuée : {len(df_concat)} lignes avant déduplication")

mask_date_max = df_concat["Date"] == date_max_remote
doublons_date_max = df_concat[mask_date_max].duplicated(subset=["Date", "Libellé", "Montant", "Compte"], keep="first")

nb_doublons = doublons_date_max.sum()
if nb_doublons > 0:
    print(f"{nb_doublons} doublons détectés sur la date {date_max_remote.strftime('%d/%m/%Y')} — supprimés")
    df_concat = df_concat[~(mask_date_max & doublons_date_max)]
else:
    print("Aucun doublon détecté sur la date la plus récente")

print(f"Nettoyage terminé : {len(df_concat)} lignes uniques")


# ======================================================
# 6. Classification fuzzy
# ======================================================
df_final = appliquer_fuzzy(df_concat)

# ======================================================
# 7. Chargement dans une table temporaire PostgreSQL
# ======================================================
print("Chargement dans la table temporaire 'operations_temp'...")

# 1️⃣ Supprimer proprement la table existante (et ses index)
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS operations_temp CASCADE;"))
    conn.commit()

# 2️⃣ Créer un index 'id' manuellement après insertion
# On ajoute la colonne id avant l'export SQL
df_final = df_final.reset_index(drop=True)
df_final.insert(0, "id", df_final.index + 1)  # id commence à 1

# 3️⃣ Exporter vers PostgreSQL sans laisser pandas créer d’index automatique
df_final.to_sql("operations_temp", engine, if_exists="replace", index=False)

# 4️⃣ Définir l'id comme PRIMARY KEY + index
with engine.begin() as conn:
    conn.execute(text("""
        ALTER TABLE operations_temp
        ADD PRIMARY KEY (id);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_operations_temp_id
        ON operations_temp (id);
    """))

print("Table temporaire 'operations_temp' chargée et indexée avec succès.")


# ======================================================
# 8. Sauvegarde de la table existante et remplacement
# ======================================================

with engine.begin() as conn:
    print("Sauvegarde de la table actuelle en 'operations_old'...")
    conn.execute(text("DROP TABLE IF EXISTS operations_old CASCADE;"))
    conn.execute(text("ALTER TABLE operations RENAME TO operations_old;"))

    print("Remplacement par la nouvelle table...")
    conn.execute(text("ALTER TABLE operations_temp RENAME TO operations;"))

    print("Suppression des tables temporaires résiduelles (par sécurité)...")
    conn.execute(text("DROP TABLE IF EXISTS operations_temp CASCADE;"))

print("✅ Mise à jour terminée avec succès.")
