# pages/11_Orcamento.py
import streamlit as st
import database
import pandas as pd
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Definir Orçamento Mensal")
st.info("Defina um limite de gastos para suas categorias de despesa. Deixe em 0 para não ter um limite.")

# 1. Busca todas as categorias de DESPESA do usuário
categorias_despesa = database.get_categorias(user_id, "despesa")
# 2. Busca os orçamentos JÁ definidos pelo usuário
orcamentos_definidos = database.get_orcamentos(user_id)

if not categorias_despesa:
    st.warning("Você precisa cadastrar categorias de despesa antes de poder definir um orçamento.")
else:
    # Cria um dicionário com os orçamentos atuais para fácil acesso
    orcamentos_dict = {orc[0]: orc[1] for orc in orcamentos_definidos}

    # Prepara os dados para o editor
    dados_editor = []
    for cat_id, cat_nome in categorias_despesa:
        limite_atual = orcamentos_dict.get(cat_nome, 0.0)
        dados_editor.append({"Categoria": cat_nome, "Limite Mensal": limite_atual})
    
    df_orcamento = pd.DataFrame(dados_editor)

    st.markdown("### Orçamento por Categoria")
    
    # Usa o data_editor para uma interface de edição rápida
    edited_df = st.data_editor(
        df_orcamento,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Categoria": st.column_config.TextColumn("Categoria", disabled=True),
            "Limite Mensal": st.column_config.NumberColumn("Limite (R$)", format="%.2f", min_value=0.0)
        },
        key="editor_orcamento"
    )

    if st.button("Salvar Orçamentos", type="primary"):
        # Itera sobre o DataFrame editado e salva cada orçamento
        for _, row in edited_df.iterrows():
            database.set_orcamento(user_id, row["Categoria"], row["Limite Mensal"])
        st.success("Orçamentos salvos com sucesso!")
        st.rerun()