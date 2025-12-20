import streamlit as st
import database
import pandas as pd
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Definir Orçamento Mensal por Subcategoria")
st.info("Defina um limite de gastos apenas para suas subcategorias de despesa. Se quiser que uma subcategoria não tenha limite, deixe o valor em 0.")

# 1. Buscar TODAS as subcategorias do usuário
#    Esperado: (subcategoria_id, categoria_id, nome)
subcats = database.get_subcategorias(user_id)

if not subcats:
    st.warning("Você precisa cadastrar subcategorias de despesa antes de poder definir um orçamento.")
else:
    # Buscar categorias de despesa para exibir o nome da categoria mãe (apenas informativo)
    categorias_despesa = database.get_categorias(user_id, "despesa")
    cat_id_to_nome = {c[0]: c[1] for c in categorias_despesa}

    # 2. Buscar orçamentos já definidos (chave = nome da subcategoria)
    #    get_orcamentos retorna, por ex.: [(categoria_ou_chave, limite), ...]
    orcamentos_definidos = database.get_orcamentos(user_id)
    orcamentos_dict = {orc[0]: orc[1] for orc in orcamentos_definidos}

    # 3. Montar DataFrame apenas com subcategorias
    dados_editor = []
    for sub_id, cat_id, sub_nome in subcats:
        categoria_nome = cat_id_to_nome.get(cat_id, "–")
        chave = sub_nome  # orçamento só por subcategoria
        limite_atual = orcamentos_dict.get(chave, 0.0)
        dados_editor.append(
            {
                "Categoria": categoria_nome,   # só para visualizar
                "Subcategoria": sub_nome,     # chave lógica de orçamento
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
            "Categoria": st.column_config.TextColumn(
                "Categoria",
                disabled=True,
                help="Categoria mãe da subcategoria (não usada como chave de orçamento).",
            ),
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
            # Agora o orçamento é SEMPRE por subcategoria
            database.set_orcamento(user_id, sub_nome, limite)
        st.success("Orçamentos por subcategoria salvos com sucesso!")
        st.rerun()
