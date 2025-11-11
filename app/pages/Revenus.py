
import re
import sqlite3
import streamlit as st
import pandas as pd

# ==========================================================
#                  INITIALISATION
# ==========================================================


st.session_state.sidebar_closed = True
st.set_page_config(initial_sidebar_state="collapsed", layout="wide")

conn = sqlite3.connect("budget.db")
df = pd.read_sql_query("SELECT * FROM operations", conn)


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
#                  PROJECTION EPARGNE (24/36/60 mois)
# ==========================================================


st.subheader("🔮 Projection d'épargne (comparatif 2 ans / 3 ans / 5 ans)")

st.write("")
st.write("")

# --- Paramètres utilisateur ---
col1, col2, col3 = st.columns(3)

salaire_simule = col1.slider(
    "Salaire mensuel pris en compte (€)",
    min_value=int(salaire_moyen_par_mois - 100),
    max_value=int(salaire_moyen_par_mois + 100),
    value=int(salaire_moyen_par_mois),
    step=50
)

taux_epargne_simule = col2.slider(
    "Taux d’épargne (%)",
    min_value=0.0,
    max_value=50.0,
    value=round((epargne_moyenne / salaire_moyen_par_mois) * 100, 1),
    step=1.0
)

taux_interet = col3.slider(
    "Taux d'intérêt (annuel, %)",
    min_value=0.0,
    max_value=5.0,
    value=1.5,
    step=0.5
)

# --- Calcul projection ---
import numpy as np
import pandas as pd

interet_mensuel = taux_interet / 12 / 100
epargne_mensuelle = salaire_simule * (taux_epargne_simule / 100)

def projection(mois):
    solde = 0
    for _ in range(mois):
        solde += epargne_mensuelle
        solde *= (1 + interet_mensuel)
    return solde

df_projection = pd.DataFrame({
    "Durée": ["2 ans (24 mois)", "3 ans (36 mois)", "5 ans (60 mois)"],
    "Solde projeté": [
        projection(24),
        projection(36),
        projection(60),
    ]
})

st.write("")
st.write("")
# --- Barplot ---
import altair as alt

# Formatage pour affichage des labels
df_projection["Label"] = df_projection["Solde projeté"].apply(
    lambda v: f"{v:,.0f} €".replace(",", " ")
)

chart = (
    alt.Chart(df_projection)
    .mark_bar(
        cornerRadiusTopLeft=12,
        cornerRadiusTopRight=12
    )
    .encode(
        x=alt.X("Durée:N", title=None, axis=alt.Axis(labelFontSize=14)),
        y=alt.Y("Solde projeté:Q", title="Épargne totale (€)", axis=alt.Axis(labelFontSize=14)),
        tooltip=[
            alt.Tooltip("Durée:N", title="Durée"),
            alt.Tooltip("Solde projeté:Q", title="Montant (€)", format=",.0f")
        ],
        color=alt.Color(
            "Durée:N",
            scale=alt.Scale(
                # Gradient personnalisé, plus premium
                range=["#7BC6FF", "#0096FF", "#005CFF"]
            ),
            legend=None
        )
    )
    .properties(
        height=420
    )
)

# ✅ Ajouter les labels au-dessus des barres
text_labels = (
    alt.Chart(df_projection)
    .mark_text(
        dy=-10,  # position par rapport à la barre
        fontSize=16,
        fontWeight="bold",
        color="#1a1a1a"
    )
    .encode(
        x="Durée:N",
        y="Solde projeté:Q",
        text="Label:N",
    )
)

# Affichage dans Streamlit
st.altair_chart(chart + text_labels, use_container_width=True)
