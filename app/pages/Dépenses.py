
import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import engine

st.session_state.sidebar_closed = True
st.set_page_config(initial_sidebar_state="collapsed", layout="wide")


# Connexion DB
df = pd.read_sql("SELECT * FROM operations", engine)

st.title("📊 Suivi de budget")

# Charger depuis SQLite

# 🔥 Analyse des dépenses

import altair as alt
import pandas as pd


# ========================================
# 🔥 FILTRE DE PERIODE FIXE : 6 DERNIERS MOIS
# ========================================

st.subheader("📊 Analyse des dépenses (6 derniers mois)")

# Convertir la date
df["Date"] = pd.to_datetime(df["Date"])
df["Mois"] = df["Date"].dt.to_period("M")

# Dépenses uniquement
df_dep = df[df["Débit euros"].notna()].copy()

# Appliquer le filtre : 6 derniers mois
dernier_mois = df_dep["Mois"].max()
df_dep = df_dep[df_dep["Mois"] >= dernier_mois - 5]


# ========================================
# 📊 GRAPHIQUE AIRE STACKÉE % (PAR CATEGORIE / MENSUEL)
# ========================================

col1, col2 = st.columns([2, 1])   # area chart large / camembert petit

with col1:
    st.subheader("📈 Part des dépenses dans le temps (%)")

    df_trend = (
        df_dep.groupby(["Mois", "Categorie"])["Débit euros"]
        .sum()
        .reset_index()
        .rename(columns={"Débit euros": "Debit"})
    )

    df_trend["Mois"] = df_trend["Mois"].dt.to_timestamp()

    chart_area = (
        alt.Chart(df_trend)
        .mark_area()
        .encode(
            x=alt.X("Mois:T", title="Mois"),
            y=alt.Y("sum(Debit)", stack="normalize", axis=alt.Axis(format="%"), title="Part des dépenses"),
            color=alt.Color("Categorie:N", title="Catégorie"),
            tooltip=[
                alt.Tooltip("Mois:T", title="Mois"),
                alt.Tooltip("Categorie:N", title="Catégorie"),
                alt.Tooltip("sum(Debit):Q", title="Montant (€)", format=",.0f")
            ]
        )
        .properties(height=350)
        .interactive()
    )

    st.altair_chart(chart_area, use_container_width=True)


# ========================================
# 🥧 CAMEMBERT INTERACTIF (PART SUR LA PERIODE)
# ========================================

with col2:
    st.subheader("🥧 Répartition par catégorie")

    df_pie = (
        df_dep.groupby("Categorie")["Débit euros"]
        .sum()
        .reset_index()
        .rename(columns={"Débit euros": "Montant"})
    )

    total_depenses = df_pie["Montant"].sum()
    df_pie["Part (%)"] = df_pie["Montant"] / total_depenses * 100

    chart_pie = (
        alt.Chart(df_pie)
        .mark_arc(outerRadius=110)
        .encode(
            theta=alt.Theta(field="Montant", type="quantitative"),
            color=alt.Color(field="Categorie", type="nominal", title="Catégorie"),
            tooltip=[
                alt.Tooltip("Categorie:N", title="Catégorie"),
                alt.Tooltip("Montant:Q", title="Montant (€)", format=",.0f"),
                alt.Tooltip("Part (%):Q", title="Part", format=".1f")
            ]
        )
        .properties(width=350, height=350)
    )

    st.altair_chart(chart_pie, use_container_width=True)

# ========================================
# 📊 COMPARAISON MOIS COURANT VS MOYENNE 6 MOIS
# ========================================

mois_courant = df_dep["Mois"].max()

# Dépenses du mois courant
df_current = (
    df_dep[df_dep["Mois"] == mois_courant]
    .groupby("Categorie")["Débit euros"]
    .sum()
    .reset_index()
    .rename(columns={"Débit euros": "Montant"})
)

# Moyenne mensuelle sur 6 mois
df_avg = (
    df_dep.groupby(["Mois", "Categorie"])["Débit euros"]
    .sum()
    .reset_index()
    .groupby("Categorie")["Débit euros"]
    .mean()
    .reset_index()
    .rename(columns={"Débit euros": "Montant"})
)

# Ajouter un label pour le graphique
df_current["Type"] = "Mois courant"
df_avg["Type"] = "Moyenne 6 mois"

# Combiner
# Pivot to compute deviation

df_compare = pd.concat([df_current, df_avg], ignore_index=True)


df_pivot = (
    df_compare
    .pivot(index="Categorie", columns="Type", values="Montant")
    .fillna(0)
    .reset_index()
)

df_pivot["Écart (€)"] = df_pivot["Mois courant"] - df_pivot["Moyenne 6 mois"]



st.subheader("📊 Écart des dépenses par rapport à la moyenne (mois courant)")

chart_dev = (
    alt.Chart(df_pivot)
    .mark_bar()
    .encode(
        x=alt.X("Categorie:N", sort="-y", title="Catégorie"),
        y=alt.Y("Écart (€):Q", title="Écart (€)"),
        color=alt.condition(
            alt.datum["Écart (€)"] > 0,
            alt.value("#d62728"),  # red = overspend
            alt.value("#2ca02c"),  # green = underspend
        ),
        tooltip=[
            alt.Tooltip("Categorie:N", title="Catégorie"),
            alt.Tooltip("Écart (€):Q", title="Écart (€)", format=",.0f"),
        ],
    )
    .properties(height=400)
)

st.altair_chart(chart_dev, use_container_width=True)




# Filtre catégories pour ce tableau
st.subheader("Top 20 dépenses les plus importantes (6 derniers mois)")

# ✅ Liste unique des catégories (triées)
categories = sorted(df["Categorie"].dropna().unique())

# ✅ Initialisation (catégorie active ou aucune)
if "active_category" not in st.session_state:
    st.session_state.active_category = None


st.write("Filtrer par catégorie :")

cols = st.columns(4)  # 4 boutons par ligne

for i, cat in enumerate(categories):
    col = cols[i % 4]

    # Style du bouton selon l'état
    active = st.session_state.active_category == cat
    label = cat

    style = (
        "background-color:#1f77b4;color:white;border-radius:6px;"
        if active else
        "background-color:#E8E8E8;border-radius:6px;"
    )

    if col.button(label, key=f"btn_{cat}", use_container_width=True):
        # Si on clique sur un bouton déjà actif → on désactive
        if active:
            st.session_state.active_category = None
        else:
            st.session_state.active_category = cat


# ✅ Filtrage
dernier_mois = df_dep["Mois"].max()
six_mois = dernier_mois - 5
df_6m = df_dep[df_dep["Mois"] >= six_mois]

df_top = df_6m.copy()

if st.session_state.active_category:
    df_top = df_top[df_top["Categorie"] == st.session_state.active_category]

df_top = (
    df_top.sort_values("Débit euros", ascending=False)
          .head(20)
          [["Date", "Libellé", "Categorie", "Débit euros"]]
)

st.dataframe(df_top)

from sqlalchemy import text

st.subheader("🟡 Catégoriser les opérations non classées")

df_autres = df[
    (df["Categorie"] == "Autres")
    & (df["Traitee"] == False)
    & (df["Débit euros"].notna())
].copy()


if len(df_autres) == 0:
    st.success("🎉 Aucune opération à catégoriser !")
else:
    page_size = 3
    total_pages = (len(df_autres) - 1) // page_size + 1
    page = st.number_input("Page", 1, total_pages, 1)

    start, end = (page - 1) * page_size, page * page_size
    df_page = df_autres.iloc[start:end]

    categories = [
        "Abonnements", "Alimentation", "Banque", "Logement",
        "Transports", "Loisirs", "Vêtements", "Autres"
    ]

    with st.form("categorisation_form"):
        new_cats = {}
        st.write(f"📄 Page {page}/{total_pages}")

        for _, row in df_page.iterrows():
            st.markdown(f"### 💳 {row['Libellé']}")
            st.caption(f"{row['Date'].strftime('%d/%m/%Y')} — {row['Débit euros']} €")

            new_cat = st.radio(
                "Choisir une catégorie :",
                categories,
                key=f"cat_{row['id']}",
                horizontal=True,
            )
            new_cats[row["id"]] = new_cat
            st.divider()

        submit = st.form_submit_button("✅ Enregistrer les changements")

        if submit:
            with engine.begin() as conn:
                for idx, cat in new_cats.items():
                    if cat == "Autres":
                        conn.execute(text("""
                            UPDATE operations
                            SET "Traitee" = TRUE
                            WHERE id = :idx
                        """), {"idx": idx})
                    else:
                        conn.execute(text("""
                            UPDATE operations
                            SET "Categorie" = :cat, "Traitee" = TRUE
                            WHERE id = :idx
                        """), {"cat": cat, "idx": idx})

            st.success("✅ Modifications enregistrées !")
            st.rerun()

