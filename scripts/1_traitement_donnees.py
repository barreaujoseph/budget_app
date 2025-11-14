import pandas as pd
import re
from openpyxl import load_workbook

fichier = "CA20251111_105004.xlsx"

# Charger toutes les données sans interprétation
raw = pd.read_excel(fichier, header=None, engine="openpyxl")

# =====================================================
# 1️⃣ Détection automatique des soldes "Solde au ..."
# =====================================================
soldes = []

for i, row in raw.iterrows():
    row_str = " ".join(str(x) for x in row if pd.notna(x))
    match = re.search(r"Solde au\s+(\d{2}/\d{2}/\d{4})\s+([\d\s ,]+)", row_str)

    if match:
        date_solde = match.group(1)
        montant = match.group(2)

        montant = montant.replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")

        soldes.append({
            "ligne_solde": i,
            "date_solde": pd.to_datetime(date_solde, dayfirst=True),
            "solde": float(montant),
        })

print("✅ Soldes détectés :")
for s in soldes:
    print(s)

# =====================================================
# 2️⃣ Détection des sections "Date / Libellé / Débit / Crédit"
# =====================================================
header_rows = raw[raw.eq("Date").any(axis=1)].index.tolist()

dataframes = []

# Pour chaque section d'opérations
for idx, start in enumerate(header_rows):
    end = header_rows[idx + 1] if idx + 1 < len(header_rows) else len(raw)
    
    df_tmp = pd.read_excel(
        fichier,
        skiprows=start,
        nrows=end - start - 1,
        engine="openpyxl"
    )

    # Nettoyage des opérations valides
    df_tmp = df_tmp[pd.to_datetime(df_tmp["Date"], errors="coerce").notna()]
    df_tmp["Date"] = pd.to_datetime(df_tmp["Date"])

    # Associer le solde au tableau correspondant
# Trouver le solde le plus proche situé AVANT le tableau (start)
    solde_associe = None
    for s in sorted(soldes, key=lambda x: x["ligne_solde"], reverse=True):
        if s["ligne_solde"] < start:
            solde_associe = s
            break

    if solde_associe:
        df_tmp["Solde final"] = solde_associe["solde"]
        df_tmp["Date solde final"] = solde_associe["date_solde"]

    dataframes.append(df_tmp)

# Concaténer tous les comptes
df = pd.concat(dataframes, ignore_index=True)

df["Compte"] = df.groupby(["Solde final", "Date solde final"]).ngroup() + 1

# Montant de l'opération (+ crédit - débit)
df["Montant"] = df["Crédit euros"].fillna(0) - df["Débit euros"].fillna(0)

# Tri par compte et par date
df = df.sort_values(["Compte", "Date"])

# Calcul du solde qui "remonte dans le temps"
df["Solde courant"] = df.groupby("Compte").apply(
    lambda g: g["Solde final"].iloc[0] - g["Montant"][::-1].cumsum()[::-1]
).reset_index(level=0, drop=True)


# Convertir colonnes débit / crédit en float proprement
df["Débit euros"] = (
    df["Débit euros"].replace({",": ".", " ": ""}, regex=True).astype(float)
)

df["Crédit euros"] = (
    df["Crédit euros"].replace({",": ".", " ": ""}, regex=True).astype(float)
)

print("\n=== Tableau complet (tous comptes) ===")
print(df)
