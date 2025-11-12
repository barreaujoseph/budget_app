
import re
import pandas as pd
from scripts.traitement_donnees import df  

# -----------------------------
# LISTE DES REGEX PAR CATÉGORIE
# -----------------------------
CATEGORIES = {
    r"(NETFLIX|SPOTIFY|DISNEY|APPLE|GOOGLE|MICROSOFT|PADDLE|HANDBALL TV|YOUTUBE|UBEREATS+PASS|UGC)": "Abonnements",

    r"(CARREFOUR|AUCHAN|LECLERC|INTERMARCHE|MONOPRIX|LIDL|FRANPRIX|SUPERMARCHE|SELECTA|MCDO|BURGER|KFC|RESTAURANT|QUICK|DELIVEROO|JUSTEAT)": "Alimentation",

    r"(SEPA|TIP|PAIEMENT MOBILE|CB|COMMISSION|FRAIS|AGIOS|BANCAIRE|CAISSE D'EPARGNE|CREDIT AGRICOLE)": "Banque",

    r"(EDF|ENGIE|SFR|FREE|ORANGE|Loyer|LOYER|ASSURANCE HABITATION)": "Logement",

    r"(ZARA|PRIMARK|H&M|LAFAYETTE|JULES|CELIO|BERSHKA|PULL ?& ?BEAR|UNIQLO|DECATHLON|GO SPORT|NIKE|ADIDAS|FOOT LOCKER|VETEMENTS)": "Vêtements",

    r"(SNCF|RATP|METRO|INDIGO|UBER|BOLT|NAVIGO|AUTOLIB|TISSEO|PARKING|PEAGE|TOTAL|ESSENCE|STATION)": "Transports",

    r"(AMAZON|FNAC|ZARA|PRIMARK|CULTURA|LOISIRS|CINEMA|STEAM|JEU|GAME|PAYPAL)": "Loisirs",
}

EXCLUSIONS_AUTRES = ["PHARMACIE", "ANDREA"]

def classer_depense(libelle):
    if pd.isna(libelle):
        return "Autres", None

    lib = str(libelle).upper()

    # Règle d’exclusion
    for mot in EXCLUSIONS_AUTRES:
        if mot in lib:
            return "Autres", mot

    for pattern, categorie in CATEGORIES.items():
        match = re.search(pattern, lib)
        if match:
            mot_trouve = match.group(0)
            return categorie, mot_trouve

    return "Autres", None



def appliquer_regex(df):
    df = df.copy()
    df[["Categorie", "Mot_trouve"]] = df.apply(
        lambda row: pd.Series(classer_depense(row["Libellé"])) 
        if not pd.isna(row.get("Débit euros")) else pd.Series([None, None]),
        axis=1
    )
    return df

# -----------------------------
# Ne s'exécute que si lancé directement
# -----------------------------

if __name__ == "__main__":
    df[["Categorie", "Mot_trouve"]] = df.apply(
        lambda row: pd.Series(classer_depense(row["Libellé"])) 
        if not pd.isna(row["Débit euros"]) else pd.Series([None, None]),
        axis=1
    )
    print(df.groupby("Categorie")["Débit euros"].sum().sort_values(ascending=False))


