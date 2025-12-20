import streamlit as st
import database
import pandas as pd
import datetime
import utils


# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# --- Conteúdo da Página ---
st.title("Gerenciar Categorias")

# ===== FORMULÁRIO: NOVA CATEGORIA =====
with st.form("form_nova_categoria"):
    st.markdown("### Adicionar Nova Categoria")

    tipo = st.radio(
        "Tipo de categoria",
        options=["receita", "despesa"],
        horizontal=True,
    )
    nome = st.text_input("Nome da categoria")

    if st.form_submit_button("Adicionar"):
        if not nome.strip():
            st.toast("O nome da categoria é obrigatório.", icon="⚠️")
        else:
            database.insert_categoria(user_id, tipo, nome.strip())
            st.toast(f"Categoria '{nome}' adicionada!", icon="✅")
            st.rerun()

# ===== LISTAGEM / EDIÇÃO / EXCLUSÃO DE CATEGORIAS =====
st.markdown("---")
st.markdown("### Categorias")

col1, col2 = st.columns(2)

for tipo, col in [("receita", col1), ("despesa", col2)]:
    with col:
        st.markdown(f"#### Categorias de {tipo.capitalize()}")
        categorias = database.get_categorias(user_id, tipo)

        if not categorias:
            st.info(f"Nenhuma categoria de {tipo} cadastrada.")
            continue

        df = pd.DataFrame(categorias, columns=["ID", "Nome"])
        df["Excluir"] = False

        edited_df = st.data_editor(
            df,
            key=f"editor_{tipo}",
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None,
                "Nome": st.column_config.TextColumn(required=True),
            },
        )

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
                st.toast(
                    f"{len(selected)} categoria(s) de {tipo} excluída(s)!",
                    icon="🗑️",
                )
                st.rerun()
            else:
                st.toast(
                    f"Nenhuma categoria de {tipo} selecionada.",
                    icon="⚠️",
                )

# ===== CATEGORIAS + SUBCATEGORIAS NO MESMO DATAFRAME =====
st.markdown("---")
st.markdown("### Categorias e Subcategorias")

# Carrega todas as categorias (receita + despesa)
categorias_receita = database.get_categorias(user_id, "receita")
categorias_despesa = database.get_categorias(user_id, "despesa")
todas_categorias = categorias_receita + categorias_despesa  # [(id, nome), ...]

if not todas_categorias:
    st.info("Cadastre categorias para gerenciar subcategorias.")
else:
    # Mapas de id <-> nome
    cat_id_to_nome = {c[0]: c[1] for c in todas_categorias}
    cat_nome_to_id = {v: k for k, v in cat_id_to_nome.items()}
    lista_nomes_categorias = list(cat_nome_to_id.keys())

    # Carrega subcategorias existentes
    subcats = get_subcategorias(user_id)  # (subcat_id, categoria_id, nome)

    if subcats:
        df_sub = pd.DataFrame(
            subcats,
            columns=["Subcat ID", "Categoria ID", "Subcategoria"],
        )
        df_sub["Categoria"] = df_sub["Categoria ID"].map(cat_id_to_nome)
    else:
        # DataFrame vazio para permitir criação de novas subcategorias direto no editor
        df_sub = pd.DataFrame(
            columns=["Subcat ID", "Categoria ID", "Subcategoria", "Categoria"]
        )

    df_sub["Excluir"] = False

    edited_sub = st.data_editor(
        df_sub,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",  # permite adicionar/remover linhas
        column_config={
            "Subcat ID": None,
            "Categoria ID": None,
            "Categoria": st.column_config.SelectboxColumn(
                "Categoria",
                options=lista_nomes_categorias,
                required=True,
            ),
            "Subcategoria": st.column_config.TextColumn(required=True),
        },
        key="editor_categorias_sub",
    )

    col_s1, col_s2 = st.columns(2)

    if col_s1.button("Salvar Categorias/Subcategorias"):
        for _, row in edited_sub.iterrows():
            # Excluir marcadas
            if row.get("Excluir", False):
                if pd.notna(row.get("Subcat ID")):
                    delete_subcategoria(int(row["Subcat ID"]), user_id)
                continue

            nome_cat = str(row.get("Categoria", "")).strip()
            nome_sub = str(row.get("Subcategoria", "")).strip()

            if not nome_cat or not nome_sub:
                continue

            categoria_id = cat_nome_to_id.get(nome_cat)

            # Nova subcategoria
            if pd.isna(row.get("Subcat ID")) or row.get("Subcat ID") == "":
                insert_subcategoria(user_id, categoria_id, nome_sub)
            else:
                # Atualizar subcategoria existente
                update_subcategoria(int(row["Subcat ID"]), user_id, nome_sub)

        st.toast("Categorias e subcategorias salvas!", icon="✅")
        st.rerun()

    if col_s2.button("Excluir Subcategorias Marcadas"):
        to_delete = edited_sub[
            (edited_sub["Excluir"] == True) & edited_sub["Subcat ID"].notna()
        ]
        if not to_delete.empty:
            for _, row in to_delete.iterrows():
                delete_subcategoria(int(row["Subcat ID"]), user_id)
            st.toast(f"{len(to_delete)} subcategoria(s) excluída(s)!", icon="🗑️")
            st.rerun()
        else:
            st.toast("Nenhuma subcategoria marcada para exclusão.", icon="⚠️")



