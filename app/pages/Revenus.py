
import re
import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import engine

# ==========================================================
#                  INITIALISATION
# ==========================================================


st.session_state.sidebar_closed = True
st.set_page_config(initial_sidebar_state="collapsed", layout="wide")

df = pd.read_sql("SELECT * FROM operations", engine)


df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Mois"] = df["Date"].dt.to_period("M")

# ==========================================================
#                  IDENTIFICATION EPARGNE
# ==========================================================


# Normaliser le libellé 
df["Libellé_upper"] = df["Libellé"].astype(str).str.upper()
df["Virement_interne"] = df["Libellé_upper"].str.contains(
    r"(?s)(?=.*VIREMENT)(?=.*BARREAU)(?=.*JOSEPH)(?!.*LOYER)",
    regex=True,
    na=False
)
# Filtrer uniquement les virements internes réellement entre comptes
df_virements = df[df["Virement_interne"] == True]

# Virements sortants du compte courant vers épargne
# Détection des virements internes sortants (courant -> épargne)
df_virements_sortants = df_virements[df_virements["Compte"] == 1]

if not df_virements_sortants.empty:

    # --- 1️⃣ Définir la période d'épargne ---
    debut = df_virements_sortants["Mois"].min()      # premier mois où tu épargnes
    fin = df_virements_sortants["Mois"].max()        # dernier mois détecté

    # Créer une liste continue de mois entre début et fin
    mois_range = pd.period_range(start=debut, end=fin, freq="M")

    # --- 2️⃣ Calcul des montants d'épargne par mois ---
    epargne_mensuelle = (
        df_virements_sortants
        .groupby("Mois")["Débit euros"]
        .sum()
        .reindex(mois_range, fill_value=0)   # ✅ Remplir les mois sans virement par 0
    )

    # --- 3️⃣ Moyenne sur la période complète ---
    epargne_moyenne = epargne_mensuelle.mean()

else:
    epargne_moyenne = 0.0


def format_euro(val):
    return f"{val:,.2f} €".replace(",", " ").replace(".", ",")

st.subheader("💰 Épargne")
st.metric("💰 Épargne moyenne par mois", format_euro(epargne_moyenne))


import altair as alt

# Évolution du solde courant
df_solde = (
    df[df["Compte"] == 1]    # compte courant
    .sort_values("Date")[["Date", "Solde courant"]]
)

# Points pour les virements sortants
df_points = (
    df_virements[df_virements["Compte"] == 1]
    [["Date", "Débit euros"]]
    .assign(Montant=lambda x: -x["Débit euros"])
)

chart_solde = (
    alt.Chart(df_solde)
    .mark_line(color="#1f77b4")
    .encode(
        x="Date:T",
        y="Solde courant:Q",
        tooltip=["Date", "Solde courant"]
    )
)

chart_virements = (
    alt.Chart(df_points)
    .mark_bar(color="green", width=8)
    .encode(
        x="Date:T",
        y=alt.Y("Montant:Q", title="Montant épargné"),
        tooltip=["Date", "Montant"]
    )
)

st.subheader("📈 Evolution du solde courant + moments d'épargne")
st.altair_chart(chart_solde + chart_virements, use_container_width=True)

# ==========================================================
#                  Indicateurs Salaire
# ==========================================================


# Détection des salaires (crédit sur un compte avec mention SALAIRE)
df["Salaire"] = df["Libellé_upper"].str.contains("SALAIRE", na=False)

# On ne garde que les crédits liés au salaire
df_salaires = df[(df["Salaire"] == True) & (df["Crédit euros"].notna())].copy()

# Salaire mensuel
salaire_mensuel = (
    df_salaires.groupby("Mois")["Crédit euros"]
    .sum()
    .reindex(df["Mois"].unique())  # garde tous les mois même si pas de salaire
    .fillna(0)
)

salaire_moyen_par_mois = salaire_mensuel.mean()

df_salaires["Année"] = df_salaires["Date"].dt.year

salaire_annuel = (
    df_salaires.groupby("Année")["Crédit euros"]
    .sum()
)

if salaire_moyen_par_mois > 0:
    part_epargne = epargne_moyenne / salaire_moyen_par_mois
else:
    part_epargne = 0

st.subheader("💼 Revenus")

col1, col2, col3 = st.columns(3)

col1.metric("💰 Salaire moyen net / mois", format_euro(salaire_moyen_par_mois))
col2.metric("📅 Salaire annuel net", format_euro(salaire_annuel.iloc[-1]))  # dernière année
col3.metric("📊 % du salaire net épargné", f"{part_epargne:.1%}")

st.write("")
st.write("")

# ==========================================================
#                  VIREMENTS REÇUS (ANDREA)
# ==========================================================

st.subheader("📩 Virements reçus — ANDREA")

# 1. Filtrage des opérations contenant "ANDREA" dans le libellé
# On utilise la colonne Libellé_upper créée plus haut pour ignorer la casse
df_andrea = df[df["Libellé_upper"].str.contains("ANDREA", na=False)].copy()

if not df_andrea.empty:
    # On ne garde que les colonnes pertinentes et on trie par date
    df_display = df_andrea[["Date", "Libellé", "Crédit euros"]].sort_values("Date", ascending=False)
    
    # Calcul du total reçu
    total_andrea = df_display["Crédit euros"].sum()

    # Affichage d'un indicateur visuel
    col1, col2 = st.columns([1, 3])
    col1.metric("Total reçu", format_euro(total_andrea))
    
    # Affichage du tableau stylisé
    st.dataframe(
        df_display,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "Libellé": "Détail du virement",
            "Crédit euros": st.column_config.NumberColumn("Montant", format="%.2f €")
        },
        hide_index=True,
        use_container_width=True
    )
    
    # Petit graphique d'évolution des virements reçus
    st.write("📈 Historique des réceptions")
    chart_andrea = (
        alt.Chart(df_display)
        .mark_area(
            line={'color':'#0096FF'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='white', offset=0),
                       alt.GradientStop(color='#0096FF', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        )
        .encode(
            x='Date:T',
            y=alt.Y('Crédit euros:Q', title="Montant (€)"),
            tooltip=['Date', 'Libellé', 'Crédit euros']
        )
        .properties(height=250)
    )
    st.altair_chart(chart_andrea, use_container_width=True)

else:
    st.info("Aucun virement contenant 'ANDREA' n'a été détecté dans l'historique.")
