
import re
import pandas as pd
from traitement_donnees import df  

# -----------------------------
# LISTE DES REGEX PAR CATÉGORIE
# -----------------------------
CATEGORIES = {
    r"(NETFLIX|SPOTIFY|DISNEY|APPLE|GOOGLE|MICROSOFT|PADDLE|HANDBALL TV|YOUTUBE|UBEREATS+PASS|UGC)": "Abonnements",

    r"(CARREFOUR|AUCHAN|LECLERC|INTERMARCHE|MONOPRIX|LIDL|FRANPRIX|SUPERMARCHE|SELECTA|MCDO|BURGER|KFC|RESTAURANT|QUICK|DELIVEROO|JUSTEAT)": "Alimentation",

    r"(SEPA|TIP|PAIEMENT MOBILE|CB|COMMISSION|FRAIS|AGIOS|BANCAIRE|CAISSE D'EPARGNE|CREDIT AGRICOLE)": "Banque",

    r"(EDF|ENGIE|SFR|FREE|ORANGE|Loyer|LOYER|ASSURANCE HABITATION)": "Logement",

    r"(ZARA|PRIMARK|H&M|LAFAYETTE|JULES|CELIO|BERSHKA|PULL ?& ?BEAR|UNIQLO|DECATHLON|GO SPORT|NIKE|ADIDAS|FOOT LOCKER|VETEMENTS)": "Vêtements",

    r"(SNCF|RATP|METRO|INDIGO|UBER|BOLT|TAXI|AUTOLIB|TISSEO|PARKING|PEAGE|TOTAL|ESSENCE|STATION)": "Transports",

    r"(AMAZON|FNAC|ZARA|PRIMARK|CULTURA|LOISIRS|CINEMA|STEAM|JEU|GAME|PAYPAL)": "Loisirs",
}

def classer_depense(libelle):
    if pd.isna(libelle):
        return "Autres", None  # pas de catégorie / pas de mot détecté

    lib = str(libelle).upper()  # Normalisation

    for pattern, categorie in CATEGORIES.items():
        match = re.search(pattern, lib)
        if match:
            mot_trouve = match.group(0)  # ✅ extrait le mot réellement identifié
            return categorie, mot_trouve

    return "Autres", None


df[["Categorie", "Mot_trouve"]] = df.apply(
    lambda row: pd.Series(classer_depense(row["Libellé"])) if not pd.isna(row["Débit euros"]) else pd.Series([None, None]),
    axis=1
)

print(df.groupby("Categorie")["Débit euros"].sum().sort_values(ascending=False))


import sqlite3

# Connexion / création
conn = sqlite3.connect("budget.db")

# Sauvegarde du dataframe dans une table SQL
df.to_sql("operations", conn, if_exists="replace", index=True)  # index=True = garder l'index pour modification

conn.close()

print("✅ Données enregistrées dans budget.db")
