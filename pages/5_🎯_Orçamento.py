import streamlit as st
import database
import pandas as pd
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Definir Orçamento Mensal por Subcategoria")
st.info("Defina um limite de gastos para suas subcategorias de despesa. Deixe em 0 para não ter um limite.")

# 1. Busca todas as subcategorias de DESPESA do usuário
#    Supondo que get_subcategorias retorna (subcategoria_id, categoria_id, nome)
subcats = database.get_subcategorias(user_id)

if not subcats:
    st.warning("Você precisa cadastrar subcategorias de despesa antes de poder definir um orçamento.")
else:
    # Também buscar categorias para exibir o nome da categoria mãe
    categorias_despesa = database.get_categorias(user_id, "despesa")
    cat_id_to_nome = {c[0]: c[1] for c in categorias_despesa}

    # 2. Busca os orçamentos JÁ definidos pelo usuário
    orcamentos_definidos = database.get_orcamentos(user_id)
    # orcamentos_definidos: lista de (nome, limite)
    orcamentos_dict = {orc[0]: orc[1] for orc in orcamentos_definidos}

    # 3. Prepara os dados para o editor
    dados_editor = []
    for sub_id, cat_id, sub_nome in subcats:
        categoria_nome = cat_id_to_nome.get(cat_id, "–")
        chave_orcamento = sub_nome  # usando o nome da subcategoria como chave
        limite_atual = orcamentos_dict.get(chave_orcamento, 0.0)
        dados_editor.append({
            "Categoria": categoria_nome,
            "Subcategoria": sub_nome,
            "Limite Mensal": limite_atual,
        })

    df_orcamento = pd.DataFrame(dados_editor)

    st.markdown("### Orçamento por Subcategoria")

    edited_df = st.data_editor(
        df_orcamento,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Categoria": st.column_config.TextColumn("Categoria", disabled=True),
            "Subcategoria": st.column_config.TextColumn("Subcategoria", disabled=True),
            "Limite Mensal": st.column_config.NumberColumn(
                "Limite (R$)", format="%.2f", min_value=0.0
            ),
        },
        key="editor_orcamento_sub",
    )

    if st.button("Salvar Orçamentos", type="primary"):
        for _, row in edited_df.iterrows():
            # grava orçamento usando o nome da subcategoria como chave
            database.set_orcamento(user_id, row["Subcategoria"], row["Limite Mensal"])
        st.success("Orçamentos por subcategoria salvos com sucesso!")
        st.rerun()
