# ======================================================
# 🔧 Ajustement des catégories depuis PostgreSQL
# ======================================================
# Étapes :
# 1. Récupère la base depuis Railway
# 2. Catégorise par similarité de libellés (fuzzy)
# 3. Catégorise les restantes via la moulinette regex
# 4. Réécrit la base mise à jour dans PostgreSQL
# ======================================================

import re
import pandas as pd
from rapidfuzz import process, fuzz
from sqlalchemy import text
from db import engine  # Ton objet engine PostgreSQL (depuis db.py)
from scripts.B_depenses import appliquer_regex  # ⚙️ ta moulinette regex

# ======================================================
# 1️⃣ Récupération de la base PostgreSQL
# ======================================================

print("📡 Connexion à la base Railway...")
df_remote = pd.read_sql("SELECT * FROM operations;", engine)
print(f"✅ Données récupérées : {len(df_remote)} lignes")

df = df_remote.copy()
df.to_csv("operations_local.csv", index=False)
print("💾 Sauvegarde locale effectuée : operations_local.csv")

# ======================================================
# 2️⃣ Traitement des catégories par similarité de libellés
# ======================================================

print("\n🔍 Traitement des catégories par similarité (fuzzy)...")

# Identifier les opérations traitées selon la règle métier
df['EstTraitee'] = (df['Categorie'] != 'Autres') | (df['Traitee'] == True)

# Séparer les deux groupes
df_traitees = df[df['EstTraitee']].copy()
df_a_traiter = df[~df['EstTraitee']].copy()

print(f"🔹 {len(df_traitees)} opérations considérées comme traitées")
print(f"🔸 {len(df_a_traiter)} opérations à traiter")

# Liste des libellés déjà traités
libelles_traitees = df_traitees['Libellé'].unique()

# Trouver la meilleure correspondance pour chaque libellé à traiter
matches = []
for lib in df_a_traiter['Libellé']:
    match, score, idx = process.extractOne(lib, libelles_traitees, scorer=fuzz.token_sort_ratio)
    matches.append((lib, match, score))

# Créer un DataFrame des correspondances
df_matches = pd.DataFrame(matches, columns=['Libelle_non_traite', 'Libelle_traite_similaire', 'Score'])

# Ajouter la catégorie correspondante
df_matches = df_matches.merge(
    df_traitees[['Libellé', 'Categorie']],
    left_on='Libelle_traite_similaire',
    right_on='Libellé',
    how='left'
).drop(columns=['Libellé'])

# Filtrer les correspondances très fortes
df_suggestions = df_matches[df_matches['Score'] >= 90].sort_values(by='Score', ascending=False)

print(f"✅ {len(df_suggestions)} correspondances fortes trouvées (score ≥ 90)")

# Appliquer les catégories trouvées (toutes les occurrences similaires)
for _, row in df_suggestions.iterrows():
    mask = df['Libellé'].str.contains(re.escape(row['Libelle_non_traite']), case=False, na=False)
    df.loc[mask, 'Categorie'] = row['Categorie']

# Mettre à jour le statut "Traitee"
df.loc[df['Categorie'] != 'Autres', 'Traitee'] = True
 

# ======================================================
# 3️⃣ Passage de la moulinette regex (scripts.depenses)
# ======================================================

print("\n🧩 Passage de la moulinette regex pour les opérations restantes...")

df_non_traitees = df[(df['Categorie'] == 'Autres') & (df['Traitee'] == False)].copy()
print(f"🔸 {len(df_non_traitees)} opérations à traiter par regex")

if len(df_non_traitees) > 0:
    df_regex = appliquer_regex(df_non_traitees)
    df.update(df_regex)
    df.loc[df['Categorie'] != 'Autres', 'Traitee'] = True
    print("✅ Regex appliquées aux opérations restantes.")
else:
    print("✅ Aucune opération restante à traiter par regex.")

# ======================================================
# 4️⃣ Réintégration dans PostgreSQL (méthode sécurisée)
# ======================================================

print("\n💾 Création de la table temporaire 'operations_temp'...")
df.to_sql("operations_temp", engine, if_exists="replace", index=False)

# Vérification
nb_temp = pd.read_sql("SELECT COUNT(*) FROM operations_temp;", engine).iloc[0, 0]
print(f"🧮 {nb_temp} lignes écrites dans 'operations_temp'")

# Remplacement sécurisé avec sauvegarde automatique
with engine.begin() as conn:
    # S'il existe une table "operations_old", on la supprime pour éviter l'empilement
    conn.execute(text("DROP TABLE IF EXISTS operations_old;"))
    
    # On renomme la table actuelle en "operations_old" (sauvegarde)
    conn.execute(text("ALTER TABLE operations RENAME TO operations_old;"))
    
    # On renomme la table temporaire en "operations" (mise à jour)
    conn.execute(text("ALTER TABLE operations_temp RENAME TO operations;"))

print("✅ Table 'operations' mise à jour avec sauvegarde 'operations_old'.")

# ======================================================
# 5️⃣ Résumé final
# ======================================================
nb_non_traitees = len(df[(df['Categorie'] == 'Autres') & (df['Traitee'] == False)])
print(f"\n📊 Résumé final : {len(df)} opérations au total")
print(f"   ✅ {len(df) - nb_non_traitees} traitées")
print(f"   ❌ {nb_non_traitees} encore non traitées")
print("🎉 Traitement terminé avec succès.")
