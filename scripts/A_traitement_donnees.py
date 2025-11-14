import pandas as pd
import re
from openpyxl import load_workbook
import os

def traiter_fichier_bancaire(fichier: str) -> pd.DataFrame:
    """
    Traite un fichier bancaire Excel brut (Crédit Agricole, etc.)
    et renvoie un DataFrame propre avec :
      - toutes les opérations
      - le solde final associé
      - le compte détecté
      - un calcul de solde courant
    """

    pd.set_option('future.no_silent_downcasting', True)

        # ✅ Détermination du répertoire de base
    try:
        base_dir = os.path.dirname(__file__)
    except NameError:
        base_dir = os.getcwd()  # cas notebook / Streamlit
    fichier_path = os.path.join(base_dir, fichier)

    if not os.path.exists(fichier_path):
        raise FileNotFoundError(f"❌ Fichier introuvable : {fichier_path}")

    print(f"📂 Lecture du fichier : {fichier_path}")
    raw = pd.read_excel(fichier_path, header=None, engine="openpyxl")

    # =====================================================
    # 1️⃣ Détection des lignes "Solde au ..."
    # =====================================================
    soldes = []
    for i, row in raw.iterrows():
        row_str = " ".join(str(x) for x in row if pd.notna(x))
        match = re.search(r"Solde au\s+(\d{2}/\d{2}/\d{4})\s+([\d\s,]+)", row_str)
        if match:
            date_solde = pd.to_datetime(match.group(1), dayfirst=True)
            montant = (
                match.group(2)
                .replace("\xa0", "")
                .replace("\u202f", "")
                .replace(" ", "")
                .replace(",", ".")
            )
            soldes.append({
                "ligne_solde": i,
                "date_solde": date_solde,
                "solde": float(montant)
            })

    print(f"✅ {len(soldes)} soldes détectés")
    for s in soldes:
        print(f"   - {s['date_solde'].strftime('%d/%m/%Y')} : {s['solde']:.2f} € (ligne {s['ligne_solde']})")

    # =====================================================
    # 2️⃣ Repérage des sections 'Date / Libellé / Débit / Crédit'
    # =====================================================
    header_rows = raw[raw.eq("Date").any(axis=1)].index.tolist()
    print(f"📑 {len(header_rows)} sections d'opérations détectées")

    dataframes = []
    for idx, start in enumerate(header_rows):
        end = header_rows[idx + 1] if idx + 1 < len(header_rows) else len(raw)

        df_tmp = pd.read_excel(fichier, skiprows=start, nrows=end - start - 1, engine="openpyxl")

        # Garder uniquement les lignes avec une date valide
        df_tmp = df_tmp[pd.to_datetime(df_tmp["Date"], errors="coerce").notna()].copy()
        df_tmp["Date"] = pd.to_datetime(df_tmp["Date"])

        # Trouver le solde au-dessus de ce bloc
        solde_associe = None
        for s in sorted(soldes, key=lambda x: x["ligne_solde"], reverse=True):
            if s["ligne_solde"] < start:
                solde_associe = s
                break

        # Si aucune opération trouvée après le solde → ignorer ce compte
        if df_tmp.empty:
            if solde_associe:
                print(f"⚠️ Aucun mouvement trouvé après le solde du {solde_associe['date_solde'].strftime('%d/%m/%Y')} — compte ignoré.")
            continue

        if solde_associe:
            df_tmp["Solde final"] = solde_associe["solde"]
            df_tmp["Date solde final"] = solde_associe["date_solde"]

        dataframes.append(df_tmp)

    if not dataframes:
        raise ValueError("❌ Aucun tableau d'opérations valide détecté.")

    # =====================================================
    # 3️⃣ Fusion, nettoyage et calculs
    # =====================================================
    df = pd.concat(dataframes, ignore_index=True)

    # Conversion sécurisée des montants
    for col in ["Débit euros", "Crédit euros"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace({",": ".", " ": ""}, regex=True)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Ajouter un ID de compte unique
    df["Compte"] = df.groupby(["Solde final", "Date solde final"], dropna=False).ngroup() + 1

    # Montant net : crédit - débit
    df["Montant"] = df["Crédit euros"] - df["Débit euros"]

    # Tri chronologique
    df = df.sort_values(["Compte", "Date"]).reset_index(drop=True)

    # ✅ Calcul du solde courant seulement si Solde final est présent
    if "Solde final" in df.columns and df["Solde final"].notna().any():
        print("🧮 Calcul du solde courant...")

        # Liste pour stocker les soldes calculés par compte
        solde_courant_list = []

        for compte, g in df.groupby("Compte", sort=False):
            solde_final = g["Solde final"].iloc[0]
            # cumul inverse des montants pour reconstruire le solde
            solde_courant = solde_final - g["Montant"].iloc[::-1].cumsum().iloc[::-1]
            solde_courant_list.append(solde_courant)

        # Fusion des résultats dans le bon ordre
        df["Solde courant"] = pd.concat(solde_courant_list).sort_index()

    else:
        print("⚠️ Aucun solde final valide, solde courant non calculé.")
        df["Solde courant"] = pd.NA


    print(f"✅ Données bancaires traitées avec succès : {len(df)} opérations sur {df['Compte'].nunique()} compte(s).")

    return df



# Exemple d'utilisation

#df_nouveau = traiter_fichier_bancaire("/Users/josephbarreau/Documents/python/expenses_tracker/V2/CA20251114_091415.xlsx")
