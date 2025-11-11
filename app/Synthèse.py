import streamlit as st
import sqlite3
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import engine

st.set_page_config(
    page_title="Budget App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Dashboard — Synthèse")

df = pd.read_sql("SELECT * FROM operations", engine)

# S'assurer que Date est bien un datetime
df["Date"] = pd.to_datetime(df["Date"])

# Trier par compte + date
df_sorted = df.sort_values(["Compte", "Date"])

# Prendre la dernière valeur pour chaque compte
solde_par_compte = (
    df_sorted.groupby("Compte")
             .tail(1)[["Compte", "Solde courant"]]
             .reset_index(drop=True)
             .sort_values("Solde courant", ascending=False)
)

solde_total = float(solde_par_compte["Solde courant"].sum())


depenses = float(df["Débit euros"].sum())
revenus = float(df["Crédit euros"].sum())

df["Mois"] = pd.to_datetime(df["Date"]).dt.to_period("M")

depenses_par_mois = df[df["Compte"] == 1].groupby("Mois")["Débit euros"].sum()
revenus_par_mois  = df[df["Compte"] == 1].groupby("Mois")["Crédit euros"].sum()

depenses_mensuelles_moyennes = float(depenses_par_mois.mean())
revenus_mensuels_moyens = float(revenus_par_mois.mean())


def format_euro(val):
    return f"{val:,.2f} €".replace(",", " ").replace(".", ",")


# --- Affichage ---
col1, col2, col3 = st.columns(3)
col1.metric("💶 Solde total", format_euro(solde_total))
col2.metric("📉 Dépenses moy. / mois", format_euro(depenses_mensuelles_moyennes))
col3.metric("📈 Revenus moy. / mois", format_euro(revenus_mensuels_moyens))

# Détail du solde par compte
# --- Affichage du détail par compte sous forme de texte ---

# Mapping Compte → Nom lisible
account_names = {
    1: "Compte courant",
    2: "Compte épargne"
}

# --- Affichage du détail par compte en ordre imposé ---
for compte_id in [1, 2]:  # ordre d'affichage souhaité
    row = solde_par_compte[solde_par_compte["Compte"] == compte_id]
    if not row.empty:
        solde = row.iloc[0]["Solde courant"]
        st.write(f"- **{account_names[compte_id]}** : {format_euro(solde)}")


st.subheader("📈 Évolution du solde — Compte courant")

# Filtrer uniquement le compte 1
df_compte1 = df[df["Compte"] == 1].copy()

# S'assurer que la date est bien un datetime
df_compte1["Date"] = pd.to_datetime(df_compte1["Date"])

# Trier par date (au cas où)
df_compte1 = df_compte1.sort_values("Date")

# Afficher le graphique
st.line_chart(
    df_compte1.set_index("Date")["Solde courant"],
    height=300
)
