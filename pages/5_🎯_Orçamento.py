import streamlit as st
import database
import pandas as pd
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Distribuição Percentual de Despesas por Subcategoria")
st.info(
    "Defina qual percentual do total de despesas você espera gastar em cada subcategoria. "
    "A soma não precisa ser exatamente 100%, mas isso ajuda na comparação com o realizado."
)

st.markdown("### Percentual planejado por subcategoria de despesa")

# Buscar subcategorias de despesa
# Esperado: get_subcategorias(user_id) -> (subcategoria_id, categoria_id, nome)
subcats = database.get_subcategorias(user_id)

if not subcats:
    st.info("Cadastre subcategorias de despesa para definir percentuais.")
else:
    # Quando tiver uma tabela específica de percentuais, carregue aqui:
    # orc_percentuais = database.get_orcamentos_percentuais_sub(user_id)  # [(subcategoria_nome, percentual), ...]
    # percentuais_dict = {o[0]: o[1] for o in orc_percentuais}
    percentuais_dict = {}  # provisório, sem persistência ainda

    # Subcategorias únicas pelo nome
    nomes_unicos = sorted({sub_nome for _, _, sub_nome in subcats})

    dados_sub = []
    for sub_nome in nomes_unicos:
        pct_atual = percentuais_dict.get(sub_nome, 0.0)
        dados_sub.append(
            {
                "Subcategoria": sub_nome,
                "Percentual Planejado": pct_atual,
            }
        )

    df_pct = pd.DataFrame(dados_sub)

    edited_pct = st.data_editor(
        df_pct,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Subcategoria": st.column_config.TextColumn(disabled=True),
            "Percentual Planejado": st.column_config.NumberColumn(
                "Percentual (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.1f",
                help="Percentual da despesa total que você espera gastar nesta subcategoria.",
            ),
        },
        key="editor_orcamento_pct_sub",
    )

    if st.button("Salvar Percentuais por Subcategoria"):
        for _, row in edited_pct.iterrows():
            sub_nome = row["Subcategoria"]
            pct = float(row["Percentual Planejado"])
            # Quando criar a persistência, use algo como:
            # database.set_orcamento_percentual_sub(user_id, sub_nome, pct)
        st.success("Percentuais planejados por subcategoria salvos!")
