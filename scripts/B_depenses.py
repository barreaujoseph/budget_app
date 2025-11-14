
import re
import pandas as pd
from scripts.1_traitement_donnees import df  

# -----------------------------
# Script qui gère la classification REGEX
# -----------------------------


# -----------------------------
# LISTE DES REGEX PAR CATÉGORIE
# -----------------------------
CATEGORIES = {
    # 🎬 Abonnements & médias
    r"(NETFLIX|SPOTIFY|DISNEY|APPLE|GOOGLE|MICROSOFT|PADDLE|HANDBALL\s?TV|YOUTUBE|UBER\s?EATS|UGC|PRIME\s?VIDEO|CANAL\+|DEEZER|MEDIAPART|ARRET\s?SUR\s?IMAGES)": "Abonnements",

    # 🛒 Alimentation & restauration
    r"(CARREFOUR|AUCHAN|LECLERC|INTERMARCHE|MONOPRIX|LIDL|FRANPRIX|SUPERMARCH|SUPERMARCHE|SUPERMARKET|SELECTA|MCDO|BURGER|KFC|RESTAURANT|DELIVEROO|JUST\s?EAT|COFFEE|CAFE|BOULANGERIE)": "Alimentation",

    # 🏦 Banque, prélèvements, prêts
    r"(SEPA|TIP|CB|FRAIS|AGIOS|BANCAIRE|COTISATION|CREDIT\s?AGRICOLE|REMBOURSEMENT\s+DE\s+PRET|ECHEANCE|PRELEVEMENT|OFFRE\s+GLOBE\s+TROTTER|GLOBE\s+TROTTER)": "Banque",

    # 🏠 Logement & charges
    r"(EDF|ENGIE|SFR|FREE|ORANGE|LOYER|ASSURANCE\s?HABITATION|EAU|ELECTRICITE|INTERNET)": "Logement",

    # 👕 Vêtements & sport
    r"(ZARA|PRIMARK|H&M|LAFAYETTE|JULES|CELIO|BERSHKA|PULL\s?&?\s?BEAR|UNIQLO|DECATHLON|GO\s?SPORT|NIKE|ADIDAS|FOOT\s?LOCKER|SHEIN|MODE|VETEMENTS)": "Vêtements",

    # 🚗 Transports & retraits
    r"(SNCF|RATP|METRO|INDIGO|UBER|BOLT|NAVIGO|AUTOLIB|PARKING|PEAGE|TOTAL|ESSENCE|STATION|LYFT|CARBURANT|TAXI|RETRAIT\s+AU\s+DISTRIBUTEUR)": "Transports",

    # 💸 Virements et transferts
    r"(VIREMENT\s+EMIS|VIR\s+INST|VIR\s+SEPA|VIREMENT\s+RECU|CAISSE\s+NOIRE)": "Transferts",

    # 🎮 Loisirs & e-commerce
    r"(AMAZON|FNAC|CULTURA|CINEMA|STEAM|JEU|GAME|PAYPAL|DECATHLON|FNAC\.COM|BILLETERIE)": "Loisirs",
}


EXCLUSIONS_AUTRES = ["PHARMACIE", "ANDREA"]

def classer_depense(libelle):
    if pd.isna(libelle):
        return "Autres", None

    lib = str(libelle).upper()

    for mot in EXCLUSIONS_AUTRES:
        if mot in lib:
            return "Autres", mot

    for pattern, categorie in CATEGORIES.items():
        match = re.search(pattern, lib)
        if match:
            mot_trouve = match.group(0)
            return categorie, mot_trouve

    # ⬇️ ajout pour debug
    print("🔸 Non classé :", lib)
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
    # Appliquer ta fonction de classification à chaque ligne
    df[["Categorie", "Mot_trouve"]] = df.apply(
        lambda row: pd.Series(classer_depense(row["Libellé"])) 
        if not pd.isna(row["Débit euros"]) else pd.Series([None, None]),
        axis=1
    )

autres_count = (df["Categorie"] == "Autres").sum()
total = len(df)
print(f"🔸 {autres_count} opérations dans 'Autres' ({autres_count/total*100:.1f}% du total)")

print(df['Categorie'].value_counts(normalize=True))
 

