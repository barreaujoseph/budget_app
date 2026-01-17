import streamlit as st
import pandas as pd
import os
import sys

# --- CONFIGURATION DU CHEMIN ---
# 1. Chemin du fichier actuel (app/pages/New_data.py)
# 2. .parent -> app/
# 3. .parent.parent -> racine_du_projet/
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if root_path not in sys.path:
    sys.path.insert(0, root_path)

# --- MAINTENANT LES IMPORTS FONCTIONNERONT ---
from db import engine
from scripts.A_traitement_donnees import traiter_fichier_bancaire
from scripts.B_depenses import appliquer_regex, appliquer_fuzzy
from sqlalchemy import text

st.title("📥 Ajouter de nouvelles données")

uploaded_file = st.file_uploader("Glissez le relevé bancaire .xlsx ici", type="xlsx")

if uploaded_file is not None:
    if st.button("Lancer l'intégration à PostgreSQL"):
        try:
            with st.status("Traitement du pipeline...", expanded=True) as status:
                
                # 1. Charger l'existant
                st.write("Récupération de la base actuelle...")
                df_remote = pd.read_sql("SELECT * FROM operations;", engine)
                df_remote["Date"] = pd.to_datetime(df_remote["Date"])

                # 2. Sauvegarde temporaire de l'upload
                temp_path = "temp_upload.xlsx"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # 3. Ton Pipeline de traitement
                st.write("Analyse du nouveau fichier...")
                df_nouveau = traiter_fichier_bancaire(temp_path)
                df_nouveau = appliquer_regex(df_nouveau)
                df_nouveau["Date"] = pd.to_datetime(df_nouveau["Date"])

                # 4. Déduplication (Logique de ton master.py)
                colonnes_communes = list(set(df_remote.columns) & set(df_nouveau.columns))
                date_max_remote = df_remote["Date"].max()
                
                df_nouveau_filtre = df_nouveau[df_nouveau["Date"] >= date_max_remote]
                df_concat = pd.concat([df_remote[colonnes_communes], df_nouveau_filtre[colonnes_communes]], ignore_index=True)
                
                mask_date_max = df_concat["Date"] == date_max_remote
                df_concat = df_concat[~(mask_date_max & df_concat[mask_date_max].duplicated(subset=["Date", "Libellé", "Montant", "Compte"], keep="first"))]

                # 5. Classification Fuzzy
                st.write("Classification Fuzzy...")
                df_final = appliquer_fuzzy(df_concat)

                # 6. Push SQL (Méthode de remplacement propre)
                st.write("Mise à jour de la base de données...")
                df_final = df_final.reset_index(drop=True)
                df_final.insert(0, "id", df_final.index + 1)
                
                with engine.connect() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS operations_temp CASCADE;"))
                    conn.commit()

                df_final.to_sql("operations_temp", engine, if_exists="replace", index=False)

                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE operations_temp ADD PRIMARY KEY (id);"))
                    conn.execute(text("DROP TABLE IF EXISTS operations_old CASCADE;"))
                    conn.execute(text("ALTER TABLE operations RENAME TO operations_old;"))
                    conn.execute(text("ALTER TABLE operations_temp RENAME TO operations;"))

                os.remove(temp_path)
                status.update(label="✅ Données synchronisées !", state="complete")
            
            st.balloons()
            st.success("La base de données est à jour.")

        except Exception as e:
            st.error(f"Erreur lors du traitement : {e}")