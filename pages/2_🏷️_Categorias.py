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

# Carrega apenas categorias de despesa (pode adaptar para receita também, se quiser)
categorias_despesa = database.get_categorias(user_id, "despesa")

if not categorias_despesa:
    st.info("Cadastre uma categoria de despesa antes de criar subcategorias.")
else:
    cat_id_list = [c[0] for c in categorias_despesa]
    cat_nome_list = [c[1] for c in categorias_despesa]

    with st.form("form_nova_subcategoria"):
        categoria_escolhida_nome = st.selectbox(
            "Categoria",
            options=cat_nome_list,
        )
        nome_sub = st.text_input("Nome da subcategoria")

        if st.form_submit_button("Adicionar Subcategoria"):
            if not nome_sub.strip():
                st.toast("O nome da subcategoria é obrigatório.", icon="⚠️")
            else:
                idx = cat_nome_list.index(categoria_escolhida_nome)
                categoria_id = cat_id_list[idx]
                insert_subcategoria(user_id, categoria_id, nome_sub.strip())
                st.toast("Subcategoria adicionada!", icon="✅")
                st.rerun()
# ===== LISTAGEM / EDIÇÃO / EXCLUSÃO DE CATEGORIAS =====
st.markdown("---")
st.markdown("### Categorias")

col1, col2 = st.columns(2)

# --- Categorias de RECEITA (sem subcategoria) ---
with col1:
    st.markdown("#### Categorias de Receita")
    categorias_receita = database.get_categorias(user_id, "receita")

    if not categorias_receita:
        st.info("Nenhuma categoria de receita cadastrada.")
    else:
        df_rec = pd.DataFrame(categorias_receita, columns=["ID", "Nome"])
        df_rec["Excluir"] = False

        edited_rec = st.data_editor(
            df_rec,
            key="editor_receita",
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None,
                "Nome": st.column_config.TextColumn(required=True),
            },
        )

        if st.button("Salvar Receita", key="save_receita"):
            for _, row in edited_rec.iterrows():
                database.update_categoria(int(row["ID"]), user_id, row["Nome"])
            st.toast("Categorias de receita atualizadas!", icon="✅")
            st.rerun()

        if st.button("Excluir de Receita", key="delete_receita"):
            selected = edited_rec[edited_rec["Excluir"]]
            if not selected.empty:
                for _, row in selected.iterrows():
                    database.delete_categoria(int(row["ID"]), user_id)
                st.toast(
                    f"{len(selected)} categoria(s) de receita excluída(s)!",
                    icon="🗑️",
                )
                st.rerun()
            else:
                st.toast(
                    "Nenhuma categoria de receita selecionada.",
                    icon="⚠️",
                )

# --- Categorias de DESPESA (com subcategoria no mesmo editor) ---
with col2:
    st.markdown("#### Categorias de Despesa")
    categorias_despesa = database.get_categorias(user_id, "despesa")

    if not categorias_despesa:
        st.info("Nenhuma categoria de despesa cadastrada.")
    else:
        # DF base de categorias de despesa
        df_desp = pd.DataFrame(categorias_despesa, columns=["ID", "Nome"])

        # Carrega subcategorias e monta um mapeamento categoria_id -> lista de subcats
        subcats = get_subcategorias(user_id)  # (subcat_id, categoria_id, nome)
        # Para simplicidade no editor: vamos exibir apenas UMA subcategoria por linha.
        # (Se houver várias no banco, pegamos a primeira.)
        catid_to_first_sub = {}
        subcatid_by_catid = {}
        for sub_id, cat_id, nome_sub in subcats:
            if cat_id not in catid_to_first_sub:
                catid_to_first_sub[cat_id] = nome_sub
                subcatid_by_catid[cat_id] = sub_id

        df_desp["Subcategoria"] = df_desp["ID"].map(catid_to_first_sub).fillna("")
        df_desp["Subcat ID"] = df_desp["ID"].map(subcatid_by_catid)
        df_desp["Excluir"] = False

        edited_desp = st.data_editor(
            df_desp,
            key="editor_despesa",
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None,
                "Subcat ID": None,
                "Nome": st.column_config.TextColumn(required=True),
                "Subcategoria": st.column_config.TextColumn(
                    help="Opcional. Se informado, será vinculada como subcategoria desta categoria."
                ),
            },
        )

        if st.button("Salvar Despesa", key="save_despesa"):
            for _, row in edited_desp.iterrows():
                categoria_id = int(row["ID"])
                nome_cat = str(row["Nome"]).strip()
                nome_sub = str(row.get("Subcategoria", "")).strip()
                subcat_id = row.get("Subcat ID")

                # Atualiza nome da categoria
                database.update_categoria(categoria_id, user_id, nome_cat)

                # Gerencia subcategoria associada (apenas uma por categoria nesse modelo)
                if nome_sub:
                    # Se já existe subcategoria, atualiza; senão, cria
                    if pd.notna(subcat_id):
                        update_subcategoria(int(subcat_id), user_id, nome_sub)
                    else:
                        insert_subcategoria(user_id, categoria_id, nome_sub)
                else:
                    # Se o campo foi deixado vazio e existia subcategoria, remover
                    if pd.notna(subcat_id):
                        delete_subcategoria(int(subcat_id), user_id)

            st.toast("Categorias de despesa e subcategorias salvas!", icon="✅")
            st.rerun()

        if st.button("Excluir de Despesa", key="delete_despesa"):
            selected = edited_desp[edited_desp["Excluir"]]
            if not selected.empty:
                for _, row in selected.iterrows():
                    categoria_id = int(row["ID"])
                    # Apaga também possíveis subcategorias ligadas a essa categoria
                    # (se o FK estiver com ON DELETE CASCADE, pode até pular isso)
                    subcats_cat = [
                        s for s in subcats if s[1] == categoria_id
                    ]  # (sub_id, cat_id, nome)
                    for sub_id, _, _ in subcats_cat:
                        delete_subcategoria(int(sub_id), user_id)

                    database.delete_categoria(categoria_id, user_id)

                st.toast(
                    f"{len(selected)} categoria(s) de despesa excluída(s)!",
                    icon="🗑️",
                )
                st.rerun()
            else:
                st.toast(
                    "Nenhuma categoria de despesa selecionada.",
                    icon="⚠️",
                )



