import streamlit as st
import database
import pandas as pd
import datetime
import utils
import plotly.express as px
# --- Guarda de Autenticação ---
profile, user_id, username = utils.check_authentication()

# --- Conteúdo da Página ---

st.title("Meus Investimentos")

# --- Criação das Abas ---
tab_portfolio, tab_gerenciar = st.tabs(["Meu Portfólio", "Gerenciar Transações"])

# --- ABA 1: MEU PORTFÓLIO (VISUALIZAÇÃO) ---
with tab_portfolio:
    st.markdown("### Visão Geral da Carteira")
    portfolio = database.get_portfolio_consolidado(user_id)

    if not portfolio:
        st.info("Você ainda não possui investimentos registrados ou sua posição está zerada.")
        st.write("Vá para a aba 'Gerenciar Transações' para adicionar seus ativos e operações.")
    else:
        df_portfolio = pd.DataFrame(portfolio, columns=['Código', 'Descrição', 'Tipo', 'Quantidade Total', 'Preço Médio Compra'])
        
        progress_bar = st.progress(0, text="Buscando cotações...")
        df_portfolio['Preço Atual'] = 0.0
        
        for i, row in df_portfolio.iterrows():
            preco_atual = utils.get_current_price(row['Código'], row['Tipo'])
            df_portfolio.at[i, 'Preço Atual'] = preco_atual
            progress_bar.progress((i + 1) / len(df_portfolio), text=f"Buscando cotação para {row['Código']}...")
        
        progress_bar.empty()

        df_portfolio['Custo Total'] = df_portfolio['Quantidade Total'] * df_portfolio['Preço Médio Compra']
        df_portfolio['Valor de Mercado'] = df_portfolio['Quantidade Total'] * df_portfolio['Preço Atual']
        df_portfolio['Lucro/Prejuízo R$'] = df_portfolio['Valor de Mercado'] - df_portfolio['Custo Total']
        
        # Evita divisão por zero se o custo for 0
        df_portfolio['Rentabilidade %'] = (df_portfolio['Lucro/Prejuízo R$'] / df_portfolio['Custo Total'].replace(0, 1)) * 100

        custo_total_carteira = df_portfolio['Custo Total'].sum()
        valor_mercado_carteira = df_portfolio['Valor de Mercado'].sum()
        lucro_prejuizo_carteira = valor_mercado_carteira - custo_total_carteira
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Custo Total da Carteira", utils.formatar_moeda_brl(custo_total_carteira))
        col2.metric("Valor de Mercado Atual", utils.formatar_moeda_brl(valor_mercado_carteira))
        col3.metric("Lucro/Prejuízo Total", utils.formatar_moeda_brl(lucro_prejuizo_carteira))

        st.markdown("---")
        st.markdown("### Alocação da Carteira")
        
        tipo_agrupamento = st.selectbox("Agrupar por:", ["Tipo de Ativo", "Ativo Individual"])
        df_agrupado = df_portfolio.groupby(tipo_agrupamento.split(' ')[0])['Valor de Mercado'].sum().reset_index()
        fig = px.pie(df_agrupado, names=tipo_agrupamento.split(' ')[0], values='Valor de Mercado', title=f'Alocação por {tipo_agrupamento}', hole=.3)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### Detalhes dos Ativos")
        styled_df = df_portfolio.style.format({
            'Preço Médio Compra': utils.formatar_moeda_brl, 'Custo Total': utils.formatar_moeda_brl,
            'Preço Atual': utils.formatar_moeda_brl, 'Valor de Mercado': utils.formatar_moeda_brl,
            'Lucro/Prejuízo R$': utils.formatar_moeda_brl, 'Rentabilidade %': '{:.2f}%'
        }).hide(axis="index")
        st.dataframe(styled_df, use_container_width=True)

# --- ABA 2: GERENCIAR TRANSAÇÕES (EDIÇÃO E CADASTRO) ---
with tab_gerenciar:
    st.markdown("### Registrar Nova Transação")
    investimentos_usuario = database.get_investimentos_usuario(user_id)
    investimentos_dict = {inv[1]: inv[0] for inv in investimentos_usuario}

    with st.form("form_transacao"):
        col1, col2 = st.columns(2)
        with col1:
            ativo_codigo = st.selectbox("Ativo (Código)", options=list(investimentos_dict.keys()), help="Cadastre novos ativos no expander abaixo.")
            tipo_transacao = st.radio("Tipo de Transação", ["compra", "venda"], horizontal=True)
            data_transacao = st.date_input("Data da Transação", value=datetime.date.today())
        with col2:
            quantidade = st.number_input("Quantidade", min_value=0.0, format="%.8f")
            preco_unitario = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")

        if st.form_submit_button("Registrar Transação"):
            if ativo_codigo and quantidade > 0 and preco_unitario > 0:
                investimento_id = investimentos_dict[ativo_codigo]
                database.add_transacao_investimento(investimento_id, tipo_transacao, data_transacao.isoformat(), quantidade, preco_unitario)
                st.success("Transação registrada com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha todos os campos corretamente.")

    with st.expander("Não encontrou seu ativo? Cadastre um novo aqui"):
        with st.form("form_novo_ativo"):
            tipos_investimento = database.get_tipos_investimento()
            tipos_dict = {tipo[1]: tipo[0] for tipo in tipos_investimento}
            
            novo_codigo = st.text_input("Código do Ativo (ex: PETR4, BTC-USD, MXRF11)")
            nova_descricao = st.text_input("Descrição (ex: Petrobras PN, Bitcoin)")
            novo_tipo_nome = st.selectbox("Tipo de Investimento", options=list(tipos_dict.keys()))
            
            if st.form_submit_button("Cadastrar Novo Ativo"):
                try:
                    tipo_id = tipos_dict[novo_tipo_nome]
                    database.add_investimento(user_id, tipo_id, novo_codigo, nova_descricao)
                    st.success(f"Ativo {novo_codigo.upper()} cadastrado com sucesso! Atualize a página ou selecione-o na lista acima.")
                    st.rerun()
                except ValueError as e:
                    st.error(e)

    st.markdown("---")
    st.markdown("### Histórico de Transações")
    
    todas_transacoes = database.get_all_transacoes(user_id)
    if not todas_transacoes:
        st.info("Nenhuma transação registrada.")
    else:
        df_transacoes = pd.DataFrame(todas_transacoes, columns=["ID", "Código", "Tipo", "Data", "Quantidade", "Preço Unitário"])
        df_transacoes["Data"] = pd.to_datetime(df_transacoes["Data"]).dt.date
        df_transacoes["Excluir"] = False

        edited_df = st.data_editor(
            df_transacoes,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": None,
                "Código": st.column_config.TextColumn("Código", disabled=True),
                "Tipo": st.column_config.TextColumn("Tipo", disabled=False),
                "Data": st.column_config.DateColumn("Data", required=True),
                "Quantidade": st.column_config.NumberColumn("Quantidade", format="%.8f", required=True),
                "Preço Unitário": st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f", required=True),
                "Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)
            },
            key="editor_transacoes"
        )

        col_save, col_delete = st.columns(2)
        if col_save.button("Salvar Alterações nas Transações"):
            for _, row in edited_df.iterrows():
                database.update_transacao_investimento(
                    transacao_id=int(row["ID"]),
                    data=row["Data"].isoformat(),
                    quantidade=float(row["Quantidade"]),
                    preco_unitario=float(row["Preço Unitário"])
                )
            st.success("Alterações salvas com sucesso!")
            st.rerun()

        if col_delete.button("Excluir Transações Selecionadas"):
            selected_to_delete = edited_df[edited_df["Excluir"]]
            if not selected_to_delete.empty:
                for _, row in selected_to_delete.iterrows():
                    database.delete_transacao_investimento(int(row["ID"]))
                st.success(f"{len(selected_to_delete)} transação(ões) excluída(s)!")
                st.rerun()
            else:
                st.info("Nenhuma transação selecionada para exclusão.")