import streamlit as st
import database
import pandas as pd
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Distribuição Percentual de Despesas por Categoria")
st.info(
    "Defina qual percentual do total de despesas você espera gastar em cada categoria. "
    "A soma não precisa ser exatamente 100%, mas isso ajuda na comparação com o realizado."
)

st.markdown("### Percentual planejado por categoria de despesa")

# Buscar categorias de despesa
categorias_despesa = database.get_categorias(user_id, "despesa")

if not categorias_despesa:
    st.info("Cadastre categorias de despesa para definir percentuais.")
else:
    # Quando tiver uma tabela específica de percentuais, carregue aqui:
    # orc_percentuais = database.get_orcamentos_percentuais(user_id)  # [(categoria, percentual), ...]
    # percentuais_dict = {o[0]: o[1] for o in orc_percentuais}
    percentuais_dict = {}  # provisório, sem persistência ainda

    dados_cat = []
    for cat_id, cat_nome in categorias_despesa:
        pct_atual = percentuais_dict.get(cat_nome, 0.0)
        dados_cat.append(
            {
                "Categoria": cat_nome,
                "Percentual Planejado": pct_atual,
            }
        )

    df_pct = pd.DataFrame(dados_cat)

    edited_pct = st.data_editor(
        df_pct,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Categoria": st.column_config.TextColumn(disabled=True),
            "Percentual Planejado": st.column_config.NumberColumn(
                "Percentual (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f",
                help="Percentual da despesa total que você espera gastar nessa categoria.",
            ),
        },
        key="editor_orcamento_pct",
    )

    if st.button("Salvar Percentuais por Categoria"):
        for _, row in edited_pct.iterrows():
            cat_nome = row["Categoria"]
            pct = float(row["Percentual Planejado"])
            # Quando criar a persistência, use algo como:
            # database.set_orcamento_percentual(user_id, cat_nome, pct)
        st.success("Percentuais planejados por categoria salvos!")
