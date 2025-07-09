import streamlit as st
import database
import pandas as pd
import datetime
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# --- Conteúdo da Página ---

st.title("Gerenciar Categorias")
with st.form("form_nova_categoria"):
    st.markdown("### Adicionar Nova Categoria")
    tipo = st.radio("Tipo de categoria", options=["receita", "despesa"], horizontal=True)
    nome = st.text_input("Nome da categoria")
    if st.form_submit_button("Adicionar"):
        if not nome.strip():
            st.toast("O nome da categoria é obrigatório.", icon="⚠️")
        else:
            database.insert_categoria(user_id, tipo, nome.strip())
            st.toast(f"Categoria '{nome}' adicionada!", icon="✅")
            st.rerun()

st.markdown("---")
col1, col2 = st.columns(2)

for tipo, col in [("receita", col1), ("despesa", col2)]:
    with col:
        st.markdown(f"### Categorias de {tipo.capitalize()}")
        categorias = database.get_categorias(user_id, tipo)
        if not categorias:
            st.info(f"Nenhuma categoria de {tipo} cadastrada.")
            continue

        df = pd.DataFrame(categorias, columns=["ID", "Nome"])
        df["Excluir"] = False
        edited_df = st.data_editor(df, key=f"editor_{tipo}", hide_index=True, use_container_width=True,
            column_config={"ID": None, "Nome": st.column_config.TextColumn(required=True)})
        
        if st.button(f"Salvar {tipo.capitalize()}", key=f"save_{tipo}"):
            for _, row in edited_df.iterrows():
                database.update_categoria(int(row["ID"]), user_id, row["Nome"])
            st.toast(f"Categorias de {tipo} atualizadas!", icon="✅")
            st.rerun()
        
        if st.button(f"Excluir de {tipo.capitalize()}", key=f"delete_{tipo}"):
            selected = edited_df[edited_df["Excluir"]]
            if not selected.empty:
                for _, row in selected.iterrows():
                    database.delete_categoria(int(row["ID"]), user_id)
                st.toast(f"{len(selected)} categoria(s) de {tipo} excluída(s)!", icon="🗑️")
                st.rerun()
            else:
                st.toast(f"Nenhuma categoria de {tipo} selecionada.", icon="⚠️")
