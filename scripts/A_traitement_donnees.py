import pandas as pd
import re
from openpyxl import load_workbook

def traiter_fichier_bancaire(fichier: str) -> pd.DataFrame:
    """
    Traite un fichier bancaire Excel brut (Crédit Agricole, etc.)
    et renvoie un DataFrame propre avec :
      - toutes les opérations
      - le solde final associé
      - le compte détecté
      - un calcul de solde courant

    Paramètres
    ----------
    fichier : str
        Nom du fichier Excel brut (ex: 'CA20251111_105004.xlsx')

    Retour
    ------
    pd.DataFrame : tableau nettoyé et enrichi
    """

    print(f"📂 Lecture du fichier : {fichier}")
    raw = pd.read_excel(fichier, header=None, engine="openpyxl")

    # =====================================================
    # 1️⃣ Détection des lignes "Solde au ..."
    # =====================================================
    soldes = []
    for i, row in raw.iterrows():
        row_str = " ".join(str(x) for x in row if pd.notna(x))
        match = re.search(r"Solde au\s+(\d{2}/\d{2}/\d{4})\s+([\d\s,]+)", row_str)
        if match:
            date_solde = pd.to_datetime(match.group(1), dayfirst=True)
            montant = match.group(2).replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
            soldes.append({"ligne_solde": i, "date_solde": date_solde, "solde": float(montant)})

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

        # Associer le solde correspondant
        solde_associe = None
        for s in sorted(soldes, key=lambda x: x["ligne_solde"], reverse=True):
            if s["ligne_solde"] < start:
                solde_associe = s
                break

        if solde_associe:
            df_tmp["Solde final"] = solde_associe["solde"]
            df_tmp["Date solde final"] = solde_associe["date_solde"]

        dataframes.append(df_tmp)

    if not dataframes:
        raise ValueError("❌ Aucune section d'opérations détectée.")

    # =====================================================
    # 3️⃣ Fusion, calculs et nettoyage
    # =====================================================
    df = pd.concat(dataframes, ignore_index=True)

    # Conversion des montants
    for col in ["Débit euros", "Crédit euros"]:
        df[col] = df[col].replace({",": ".", " ": ""}, regex=True)
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Compte unique par solde final
    df["Compte"] = df.groupby(["Solde final", "Date solde final"]).ngroup() + 1

    # Montant net : crédit - débit
    df["Montant"] = df["Crédit euros"] - df["Débit euros"]

    # Tri
    df = df.sort_values(["Compte", "Date"]).reset_index(drop=True)

    # Solde courant : calcul rétroactif à partir du solde final
    df["Solde courant"] = (
        df.groupby("Compte", group_keys=False)
        .apply(lambda g: g["Solde final"].iloc[0] - g["Montant"][::-1].cumsum()[::-1])
    )

    print("✅ Données bancaires traitées avec succès.")
    print(f"   → {len(df)} opérations consolidées sur {df['Compte'].nunique()} comptes détectés")

    return df
