import streamlit as st
import database
import pandas as pd
import datetime
import utils
import plotly.express as px
from dateutil.relativedelta import relativedelta

# Lógica para usuário LOGADO
import streamlit_authenticator as stauth
credentials = database.get_authenticator_credentials()
authenticator = stauth.Authenticate(
    credentials, 
    cookie_name="app_fin_cookie",
    key="app_fin_key", 
    cookie_expiry_days=30
)
if st.session_state.get("authentication_status"):
    username = st.session_state['username']
    
    with st.sidebar:
        st.subheader(f"Bem-vindo, {st.session_state['name']}!")
        st.markdown("---")
        authenticator.logout("Logout", "sidebar", key="logout_button")
    # Lógica para usuário DESLOGADO (sem cadastro)
else:
    st.subheader("Acesse sua conta")
    authenticator.login(fields={'Form name': 'Login'})
    
    if st.session_state.get("authentication_status") is False:
        st.error("Usuário ou senha incorretos.")
    elif st.session_state.get("authentication_status") is None:
        st.warning("Por favor, insira seu usuário e senha.")

# --- Guarda de Autenticação ---
profile, user_id, username = utils.check_authentication()

# --- Conteúdo da Página ---

st.title("Meus Investimentos")

# --- Criação das Abas ---
tab_portfolio, tab_transacoes, tab_ativos = st.tabs(["Meu Portfólio", "Transações", "Ativos"])

# --- ABA 1: MEU PORTFÓLIO (VISUALIZAÇÃO) ---
with tab_portfolio:
    st.markdown("### Visão Geral da Carteira")
    # A função no DB foi atualizada para retornar os novos campos de Renda Fixa
    portfolio = database.get_portfolio_consolidado(user_id)

    if not portfolio:
        st.info("Você ainda não possui investimentos registrados ou sua posição está zerada.")
        st.write("Vá para a aba 'Gerenciar Transações' para adicionar seus ativos e operações.")
    else:
        df_portfolio = pd.DataFrame(portfolio, columns=['ID', 'Código', 'Descrição', 'Tipo', 'Quantidade Total', 'Preço Médio Compra', 'Indexador', 'Taxa %', 'Vencimento'])
        
        df_portfolio['Valor de Mercado'] = 0.0
        
        progress_bar = st.progress(0, text="Buscando cotações e calculando rendimentos...")
        total_rows = len(df_portfolio)

        for i, row in df_portfolio.iterrows():
            # Lógica para Renda Variável
            if row['Tipo'] in ['Ação BR', 'Ação EUA', 'FII', 'Criptomoeda']:
                preco_atual = utils.get_current_price(row['Código'], row['Tipo'])
                df_portfolio.at[i, 'Preço Atual'] = preco_atual
                df_portfolio.at[i, 'Valor de Mercado'] = row['Quantidade Total'] * preco_atual
            
            # Lógica para Renda Fixa atrelada ao CDI
            elif row['Tipo'] == 'Renda Fixa' and row['Indexador'] == 'CDI':
                transacoes = database.get_transacoes_por_investimento_id(row['ID'])
                if transacoes:
                    # Usa a primeira transação de compra como base
                    data_aporte, _, valor_aporte = transacoes[0]
                    hoje = utils.get_local_today()

                    if data_aporte < hoje:
                        fator_cdi = utils.get_cdi_acumulado(data_aporte, hoje)
                        # Aplica o rendimento do CDI sobre o valor do aporte inicial
                        valor_atualizado = valor_aporte * fator_cdi * (row['Taxa %'] / 100)
                        df_portfolio.at[i, 'Valor de Mercado'] = valor_atualizado * row['Quantidade Total']
                        df_portfolio.at[i, 'Preço Atual'] = valor_atualizado # Para RF, o preço atual é o valor total
                    else: # Se a data do aporte for futura, o valor de mercado é o inicial
                        df_portfolio.at[i, 'Valor de Mercado'] = valor_aporte
                        df_portfolio.at[i, 'Preço Atual'] = valor_aporte


            progress_bar.progress((i + 1) / total_rows, text=f"Analisando {row['Código']}...")
        progress_bar.empty()

        df_portfolio['Custo Total'] = df_portfolio['Quantidade Total'] * df_portfolio['Preço Médio Compra']
        df_portfolio['Lucro/Prejuízo R$'] = df_portfolio['Valor de Mercado'] - df_portfolio['Custo Total']
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
        coluna_agrupamento = 'Tipo' if tipo_agrupamento == 'Tipo de Ativo' else 'Código'
        df_agrupado = df_portfolio.groupby(coluna_agrupamento)['Valor de Mercado'].sum().reset_index()
        fig = px.pie(df_agrupado, names=coluna_agrupamento, values='Valor de Mercado', title=f'Alocação por {tipo_agrupamento}', hole=.3)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("### Detalhes dos Ativos")

        # --- INÍCIO DA ALTERAÇÃO ---
        # 1. Define a lista de colunas que queremos manter na visualização
        colunas_para_exibir = [
            'Código', 'Tipo', 'Quantidade Total', 'Preço Médio Compra',
            'Custo Total', 'Preço Atual', 'Valor de Mercado',
            'Lucro/Prejuízo R$', 'Rentabilidade %'
        ]
        
        # 2. Cria um novo DataFrame apenas com as colunas desejadas
        df_display = df_portfolio[colunas_para_exibir]

        # 3. Aplica o estilo e a formatação no novo DataFrame
        styled_df = df_display.style.format({
            'Quantidade Total':'{:.2f}',
            'Preço Médio Compra': utils.formatar_moeda_brl,
            'Custo Total': utils.formatar_moeda_brl,
            'Preço Atual': utils.formatar_moeda_brl,
            'Valor de Mercado': utils.formatar_moeda_brl,
            'Lucro/Prejuízo R$': utils.formatar_moeda_brl,
            'Rentabilidade %': '{:.2f}%'
        }).hide(axis="index")
        
        # 4. Exibe o DataFrame estilizado e limpo
        st.dataframe(styled_df, use_container_width=True,hide_index=True)

# --- ABA 2: GERENCIAR TRANSAÇÕES (EDIÇÃO E CADASTRO) ---
with tab_transacoes:
    st.markdown("### Registrar Nova Transação")
    investimentos_usuario = database.get_investimentos_usuario(user_id)
    
    if not investimentos_usuario:
        st.info("Você precisa cadastrar um ativo antes de registrar uma transação.")
    else:
        investimentos_dict = {inv[1]: inv[0] for inv in investimentos_usuario}
        with st.form("form_transacao"):
            col1, col2 = st.columns(2)
            with col1:
                ativo_codigo = st.selectbox("Ativo (Código)", options=list(investimentos_dict.keys()), help="Cadastre novos ativos no expander abaixo.")
                tipo_transacao = st.radio("Tipo de Transação", ["compra", "venda"], horizontal=True)
                data_transacao = st.date_input("Data da Transação", value=utils.get_local_today())
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
        pass

    st.markdown("---")
    st.markdown("### Histórico de Transações")
    
    todas_transacoes = database.get_all_transacoes(user_id)
    if not todas_transacoes:
        st.info("Nenhuma transação registrada.")
    else:
        df_transacoes = pd.DataFrame(todas_transacoes, columns=["ID", "Código", "Tipo", "Data", "Quantidade", "Preço Unitário"])
        df_transacoes["Excluir"] = False

        edited_df = st.data_editor(df_transacoes, use_container_width=True, hide_index=True,
            column_config={
                "ID": None, "Código": st.column_config.TextColumn(disabled=True), "Tipo": st.column_config.TextColumn(disabled=True),
                "Data": st.column_config.DateColumn("Data", required=True),
                "Quantidade": st.column_config.NumberColumn(format="%.8f", required=True),
                "Preço Unitário": st.column_config.NumberColumn("Preço Unitário", format="R$ %.2f", required=True),
                "Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)
            }, key="editor_transacoes")

        col_save, col_delete = st.columns(2)
        if col_save.button("Salvar Alterações nas Transações"):
            for _, row in edited_df.iterrows():
                database.update_transacao_investimento(int(row["ID"]), row["Data"].isoformat(), float(row["Quantidade"]), float(row["Preço Unitário"]))
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

# --- ABA 3: ATIVOS (CRIAÇÃO E GERENCIAMENTO) ---
with tab_ativos:
    st.markdown("### Cadastrar Novo Ativo")
    st.markdown("#### Detalhes do Novo Ativo")
    tipos_investimento = database.get_tipos_investimento()
    tipos_dict = {tipo[1]: tipo[0] for tipo in tipos_investimento}
    
    col_a, col_b = st.columns(2)
    with col_a:
        # Usamos uma chave para o selectbox para ajudar o Streamlit a rastrear seu estado
        novo_tipo_nome = st.selectbox("Tipo de Investimento", options=list(tipos_dict.keys()), key="tipo_ativo_selecionado")
        novo_codigo = st.text_input("Código/Apelido do Ativo (ex: PETR4, CDB Banco X)")
    with col_b:
        nova_descricao = st.text_input("Descrição (ex: Petrobras PN, CDB 105% CDI)")

    # Campos condicionais que aparecem apenas para Renda Fixa
    indexador = None
    taxa_percentual = None
    data_vencimento = None

    # Agora, quando você selecionar 'Renda Fixa', a página irá re-executar
    # e esta condição será avaliada corretamente, mostrando os campos abaixo.
    if novo_tipo_nome.strip().lower() == 'renda fixa':
        st.markdown("##### Detalhes da Renda Fixa")
        col_c, col_d, col_e = st.columns(3)
        with col_c:
            indexador = st.selectbox("Indexador", ["CDI", "IPCA", "Prefixado"])
        with col_d:
            taxa_percentual = st.number_input(f"Taxa/Percentual do {indexador}", min_value=0.0, format="%.2f")
        with col_e:
            data_vencimento = st.date_input("Data de Vencimento", value=utils.get_local_today() + relativedelta(years=2))

    # Usamos um st.button normal em vez de um st.form_submit_button
    if st.button("Cadastrar Novo Ativo"):
        if novo_codigo and novo_tipo_nome:
            try:
                tipo_id = tipos_dict[novo_tipo_nome]
                database.add_investimento(
                    user_id, tipo_id, novo_codigo, nova_descricao, 
                    indexador, taxa_percentual, data_vencimento
                )
                st.success(f"Ativo {novo_codigo.upper()} cadastrado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar ativo: {e}")
        else:
            st.warning("Preencha pelo menos o Código e o Tipo de Investimento.")

    st.markdown("---")
    st.markdown("### Ativos Cadastrados")
    
    todos_ativos = database.get_all_ativos_usuario(user_id)
    if not todos_ativos:
        st.info("Nenhum ativo cadastrado. Use o formulário acima para começar.")
    else:
        # --- INÍCIO DO BLOCO CORRIGIDO (AGORA INDENTADO) ---
        df_ativos = pd.DataFrame(todos_ativos, columns=["ID", "Código", "Descrição", "Tipo", "Indexador", "Taxa %", "Vencimento"])
        df_ativos["Excluir"] = False

        edited_df = st.data_editor(
            df_ativos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": None,
                "Código": st.column_config.TextColumn("Código", disabled=True),
                "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
                "Descrição": st.column_config.TextColumn("Descrição", required=True),
                "Indexador": st.column_config.SelectboxColumn("Indexador", options=["CDI", "IPCA", "Prefixado"], required=False),
                "Taxa %": st.column_config.NumberColumn("Taxa %", format="%.2f"),
                "Vencimento": st.column_config.DateColumn("Vencimento"),
                "Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)
            },
            key="editor_ativos"
        )

        col_save, col_delete = st.columns(2)
        if col_save.button("Salvar Alterações nos Ativos"):
            if "editor_ativos" in st.session_state:
                dados_para_salvar = st.session_state["editor_ativos"]
                df_para_salvar = pd.DataFrame(dados_para_salvar)
                
                for _, row in df_para_salvar.iterrows():
                    database.update_ativo(
                        int(row["ID"]), user_id, row["Descrição"], row["Indexador"], 
                        float(row["Taxa %"]) if row["Taxa %"] else None, 
                        row["Vencimento"]
                    )
                st.success("Alterações nos ativos salvas com sucesso!")
                st.rerun()

        if col_delete.button("Excluir Ativos Selecionados", type="primary"):
            # Acessamos o estado editado para garantir que pegamos a marcação mais recente
            if "editor_ativos" in st.session_state:
                df_para_deletar = pd.DataFrame(st.session_state["editor_ativos"])
                selected_to_delete = df_para_deletar[df_para_deletar["Excluir"]]
                
                if not selected_to_delete.empty:
                    for _, row in selected_to_delete.iterrows():
                        database.delete_ativo(int(row["ID"]), user_id)
                    st.success(f"{len(selected_to_delete)} ativo(s) excluído(s)!")
                    st.rerun()
                else:
                    st.info("Nenhum ativo selecionado para exclusão.")
