import re
import pandas as pd
from rapidfuzz import process, fuzz
from scripts.A_traitement_donnees import df_nouveau

# -----------------------------
# LISTE DES REGEX PAR CATÉGORIE
# -----------------------------
CATEGORIES = {
    # 🎬 Abonnements & médias
    r"(NETFLIX|SPOTIFY|DISNEY|APPLE|GOOGLE|MICROSOFT|PADDLE|HANDBALL\s?TV|YOUTUBE|UBER\s?EATS|UGC|PRIME\s?VIDEO|CANAL\+|DEEZER|MEDIAPART|ARRET\s?SUR\s?IMAGES|DELPERIE)": "Abonnements",

    # 🛒 Alimentation & restauration
    r"(CARREFOUR|AUCHAN|LECLERC|INTERMARCHE|MONOPRIX|LIDL|FRANPRIX|SUPERMARCH|SUPERMARCHE|SUPERMARKET|DEEGHA|NAAN|MCDO|BURGER|KFC|RESTAURANT|DELIVEROO|JUST\s?EAT|COFFEE|CAFE|BOULANGERIE|CAFFE|POLE EMPLOI|RELAY|EUREST)": "Alimentation",

    # 🏦 Banque, prélèvements, prêts
    r"(SEPA|TIP|CB|FRAIS|AGIOS|BANCAIRE|COTISATION|CREDIT\s?AGRICOLE|REMBOURSEMENT\s+DE\s+PRET|ECHEANCE|PRELEVEMENT|OFFRE\s+GLOBE\s+TROTTER|GLOBE\s+TROTTER)": "Banque",

    # 🏠 Logement & charges
    r"(EDF|ENGIE|SFR|FREE|ORANGE|LOYER|ASSURANCE\s?HABITATION|EAU|ELECTRICITE|INTERNET)": "Logement",

    # 👕 Vêtements & sport
    r"(ZARA|PRIMARK|H&M|LAFAYETTE|JULES|CELIO|BERSHKA|PULL\s?&?\s?BEAR|UNIQLO|DECATHLON|GO\s?SPORT|NIKE|ADIDAS|FOOT\s?LOCKER|SHEIN|MODE|VETEMENTS)": "Vêtements",

    # 🚗 Transports & retraits
    r"(SNCF|RATP|METRO|INDIGO|UBER|BOLT|NAVIGO|AUTOLIB|PARKING|PEAGE|TOTAL|ESSENCE|STATION|SIXT|CARBURANT|TAXI|RETRAIT\s+AU\s+DISTRIBUTEUR)": "Transports",

    # 💸 Virements et transferts
    r"(VIREMENT\s+EMIS|VIR\s+INST|VIR\s+SEPA|VIREMENT\s+RECU|CAISSE\s+NOIRE)": "Transferts",

    # 🎮 Loisirs & e-commerce
    r"(AMAZON|FNAC|CULTURA|CINEMA|STEAM|JEU|GAME|PAYPAL|DECATHLON|FNAC\.COM|BILLETERIE)": "Loisirs",
}

EXCLUSIONS_AUTRES = ["PHARMACIE", "ANDREA"]


# -----------------------------
# 1️⃣ Fonction de classification par REGEX
# -----------------------------
def classer_depense(libelle):
    """Retourne (Categorie, Mot_trouvé, Traitee)"""
    if pd.isna(libelle):
        return "Autres", None, False

    lib = str(libelle).upper()

    # Cas exclus → Autres mais marquées comme traitées
    for mot in EXCLUSIONS_AUTRES:
        if mot in lib:
            return "Autres", mot, True

    # Cas catégorisés via REGEX
    for pattern, categorie in CATEGORIES.items():
        match = re.search(pattern, lib)
        if match:
            return categorie, match.group(0), True

    # Cas restants → Autres non encore traités
    return "Autres", None, False


def appliquer_regex(df: pd.DataFrame) -> pd.DataFrame:
    """Applique la classification regex sur un DataFrame d'opérations."""
    df = df.copy()
    df[["Categorie", "Mot_trouve", "Traitee"]] = df.apply(
        lambda row: pd.Series(classer_depense(row["Libellé"]))
        if not pd.isna(row.get("Débit euros"))
        else pd.Series(["Autres", None, False]),
        axis=1,
    )
    print("✅ Classification REGEX appliquée.")
    return df


# -----------------------------
# 2️⃣ Fonction de classification par similarité (fuzzy)
# -----------------------------
def appliquer_fuzzy(df: pd.DataFrame, seuil: int = 90) -> pd.DataFrame:
    print("\n🔍 Traitement des catégories par similarité (fuzzy)...")

    df["EstTraitee"] = (df["Categorie"] != "Autres") | (df["Traitee"] == True)
    df_traitees = df[df["EstTraitee"]].copy()
    df_a_traiter = df[~df["EstTraitee"]].copy()

    print(f"🔹 {len(df_traitees)} opérations considérées comme traitées")
    print(f"🔸 {len(df_a_traiter)} opérations à traiter")

    if df_a_traiter.empty or df_traitees.empty:
        print("⚠️ Pas d'opérations à traiter par fuzzy matching.")
        return df

    libelles_traitees = df_traitees["Libellé"].dropna().unique()
    matches = []

    for lib in df_a_traiter["Libellé"].dropna():
        match = process.extractOne(lib, libelles_traitees, scorer=fuzz.token_sort_ratio)
        if match:
            match_lib, score, idx = match
            matches.append((lib, match_lib, score))

    df_matches = pd.DataFrame(matches, columns=["Libelle_non_traite", "Libelle_traite_similaire", "Score"])
    df_matches = df_matches.merge(
        df_traitees[["Libellé", "Categorie"]],
        left_on="Libelle_traite_similaire",
        right_on="Libellé",
        how="left",
    ).drop(columns=["Libellé"])

    df_suggestions = df_matches[df_matches["Score"] >= seuil].sort_values(by="Score", ascending=False)

    print(f"✅ {len(df_suggestions)} correspondances fortes trouvées (score ≥ {seuil})")

    for _, row in df_suggestions.iterrows():
        mask = df["Libellé"].str.contains(re.escape(row["Libelle_non_traite"]), case=False, na=False)
        df.loc[mask, "Categorie"] = row["Categorie"]
        df.loc[mask, "Traitee"] = True

    return df
 

# -----------------------------
# 🧪 Exécution
# -----------------------------
#df_result = appliquer_regex(df_nouveau)
#df_result = appliquer_fuzzy(df_nouveau)
