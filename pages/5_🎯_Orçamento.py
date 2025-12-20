import streamlit as st
import database
import pandas as pd
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Definir Orçamento Mensal por Subcategoria")
st.info("Defina um limite de gastos apenas para suas subcategorias de despesa. Deixe em 0 para não ter limite.")

# 1. Buscar TODAS as subcategorias do usuário
#    Esperado de get_subcategorias: (subcategoria_id, categoria_id, nome)
subcats = database.get_subcategorias(user_id)

if not subcats:
    st.warning("Você precisa cadastrar subcategorias de despesa antes de poder definir um orçamento.")
else:
    # 2. Buscar orçamentos já definidos (chave = nome da subcategoria)
    #    get_orcamentos retorna algo como: [(chave, limite), ...]
    orcamentos_definidos = database.get_orcamentos(user_id)
    orcamentos_dict = {orc[0]: orc[1] for orc in orcamentos_definidos}

    # 3. Montar lista de subcategorias ÚNICAS pelo nome
    nomes_unicos = sorted({sub_nome for _, _, sub_nome in subcats})

    dados_editor = []
    for sub_nome in nomes_unicos:
        chave = sub_nome  # orçamento só por subcategoria (nome)
        limite_atual = orcamentos_dict.get(chave, 0.0)
        dados_editor.append(
            {
                "Subcategoria": sub_nome,
                "Limite Mensal": limite_atual,
            }
        )

    df_orcamento = pd.DataFrame(dados_editor)

    st.markdown("### Orçamento por Subcategoria")

    edited_df = st.data_editor(
        df_orcamento,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Subcategoria": st.column_config.TextColumn(
                "Subcategoria",
                disabled=True,
            ),
            "Limite Mensal": st.column_config.NumberColumn(
                "Limite (R$)",
                format="%.2f",
                min_value=0.0,
            ),
        },
        key="editor_orcamento_sub",
    )

    if st.button("Salvar Orçamentos", type="primary"):
        for _, row in edited_df.iterrows():
            sub_nome = row["Subcategoria"]
            limite = float(row["Limite Mensal"])
            # Salva orçamento apenas por subcategoria (nome como chave)
            database.set_orcamento(user_id, sub_nome, limite)
        st.success("Orçamentos por subcategoria salvos com sucesso!")
        st.rerun()
