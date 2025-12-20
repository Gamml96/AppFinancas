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

# ===== FORMULÁRIO: NOVA SUBCATEGORIA =====
st.markdown("---")
st.markdown("### Adicionar Nova Subcategoria")

categorias_receita = database.get_categorias(user_id, "receita")
categorias_despesa = database.get_categorias(user_id, "despesa")

todas_categorias = [
    (cat[0], f"{cat[1]} (Receita)") for cat in categorias_receita
] + [
    (cat[0], f"{cat[1]} (Despesa)") for cat in categorias_despesa
]

if not todas_categorias:
    st.info("Cadastre uma categoria antes de criar subcategorias.")
else:
    cat_id_list = [c[0] for c in todas_categorias]
    cat_label_list = [c[1] for c in todas_categorias]

    with st.form("form_nova_subcategoria"):
        categoria_label = st.selectbox(
            "Categoria pai",
            options=cat_label_list,
        )
        nome_sub = st.text_input("Nome da subcategoria")

        if st.form_submit_button("Adicionar Subcategoria"):
            if not nome_sub.strip():
                st.toast("O nome da subcategoria é obrigatório.", icon="⚠️")
            else:
                idx = cat_label_list.index(categoria_label)
                categoria_id_escolhida = cat_id_list[idx]
                insert_subcategoria(user_id, categoria_id_escolhida, nome_sub.strip())
                st.toast(f"Subcategoria '{nome_sub}' adicionada!", icon="✅")
                st.rerun()

# ===== LISTAGEM / EDIÇÃO / EXCLUSÃO DE CATEGORIAS =====
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

# ===== LISTAGEM / EDIÇÃO / EXCLUSÃO DE SUBCATEGORIAS =====
st.markdown("---")
st.markdown("### Subcategorias por Categoria")

categorias_receita = database.get_categorias(user_id, "receita")
categorias_despesa = database.get_categorias(user_id, "despesa")
todas_categorias = categorias_receita + categorias_despesa  # [(id, nome), ...]

if not todas_categorias:
    st.info("Nenhuma categoria cadastrada para listar subcategorias.")
else:
    cat_id_to_nome = {c[0]: c[1] for c in todas_categorias}

    subcats = get_subcategorias(user_id)
    if not subcats:
        st.info("Nenhuma subcategoria cadastrada.")
    else:
        # subcats: (subcategoria_id, categoria_id, nome)
        df_sub = pd.DataFrame(
            subcats,
            columns=["Subcat ID", "Categoria ID", "Nome"],
        )
        df_sub["Categoria"] = df_sub["Categoria ID"].map(cat_id_to_nome)
        df_sub["Excluir"] = False

        edited_sub = st.data_editor(
            df_sub,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Subcat ID": None,
                "Categoria ID": None,
                "Categoria": st.column_config.TextColumn(disabled=True),
                "Nome": st.column_config.TextColumn(required=True),
            },
            key="editor_subcategorias",
        )

        col_s1, col_s2 = st.columns(2)

        if col_s1.button("Salvar Subcategorias"):
            for _, row in edited_sub.iterrows():
                update_subcategoria(
                    int(row["Subcat ID"]), user_id, row["Nome"].strip()
                )
            st.toast("Subcategorias atualizadas!", icon="✅")
            st.rerun()

        if col_s2.button("Excluir Subcategorias Selecionadas"):
            selected = edited_sub[edited_sub["Excluir"]]
            if not selected.empty:
                for _, row in selected.iterrows():
                    delete_subcategoria(int(row["Subcat ID"]), user_id)
                st.toast(
                    f"{len(selected)} subcategoria(s) excluída(s)!",
                    icon="🗑️",
                )
                st.rerun()
            else:
                st.toast("Nenhuma subcategoria selecionada.", icon="⚠️")



