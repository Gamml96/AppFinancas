import streamlit as st
import database
import pandas as pd
import datetime
import utils
import plotly.express as px
from dateutil.relativedelta import relativedelta

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# --- Conteúdo da Página ---

st.title("Meus Investimentos")

# --- Criação das Abas ---
tab_portfolio, tab_transacoes, tab_ativos, tab_operacoes = st.tabs(["Meu Portfólio", "Transações", "Ativos", "Operações Estruturadas"])

# --- ABA 1: MEU PORTFÓLIO (VISUALIZAÇÃO) ---
with tab_portfolio:
    st.markdown("### Visão Geral da Carteira")
    # A função no DB foi atualizada para retornar os novos campos de Renda Fixa
    portfolio = database.get_portfolio_consolidado_fifo(user_id)


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
            # LÓGICA DE ATUALIZAÇÃO CORRIGIDA E EFICIENTE
            if "editor_ativos" in st.session_state and st.session_state["editor_ativos"]["edited_rows"]:
                # 1. Pega apenas as linhas que foram realmente editadas
                linhas_editadas = st.session_state["editor_ativos"]["edited_rows"]
                
                # 2. Itera sobre o dicionário de edições {índice: {coluna: valor}}
                for index, updates in linhas_editadas.items():
                    # Pega o ID do ativo original usando o índice da linha
                    ativo_id = int(df_ativos.iloc[index]["ID"])
                    
                    # Pega a linha original para ter os valores antigos como fallback
                    linha_original = df_ativos.iloc[index]

                    # 3. Chama a função de update com os novos valores (ou os antigos se não mudou)
                    database.update_ativo(
                        ativo_id, 
                        user_id,
                        updates.get("Descrição", linha_original["Descrição"]),
                        updates.get("Indexador", linha_original["Indexador"]),
                        float(updates.get("Taxa %", linha_original["Taxa %"]) or 0),
                        updates.get("Vencimento", linha_original["Vencimento"])
                    )
                st.success("Alterações nos ativos salvas com sucesso!")
                st.rerun()
            else:
                st.info("Nenhuma alteração foi feita para salvar.")

        if col_delete.button("Excluir Ativos Selecionados", type="primary"):
            # Lógica de exclusão corrigida
            if "editor_ativos" in st.session_state:
                # 1. Pega os índices das linhas marcadas para exclusão
                indices_para_deletar = [i for i, row in st.session_state["editor_ativos"]['edited_rows'].items() if row.get('Excluir')]
                
                if not indices_para_deletar:
                    st.info("Nenhum ativo selecionado para exclusão.")
                else:
                    sucessos = 0
                    erros = []
                    
                    # 2. Itera sobre os índices e tenta deletar
                    for index in indices_para_deletar:
                        ativo_para_deletar = df_ativos.iloc[index]
                        ativo_id = int(ativo_para_deletar["ID"])
                        nome_ativo = ativo_para_deletar["Código"]
                        
                        try:
                            # 3. Chama a função do banco de dados
                            database.delete_ativo(ativo_id, user_id)
                            sucessos += 1
                        except Exception as e:
                            # 4. Captura o erro específico para aquele ativo
                            erro_str = str(e)
                            if "foreign key constraint" in erro_str.lower():
                                erros.append(f"Ativo '{nome_ativo}': Não pôde ser excluído pois possui transações registradas.")
                            else:
                                erros.append(f"Ativo '{nome_ativo}': {erro_str}")

                    # 5. Exibe um resumo final
                    if sucessos > 0:
                        st.success(f"{sucessos} ativo(s) foram excluídos com sucesso.")
                    if erros:
                        st.error("Alguns ativos não puderam ser excluídos:")
                        for erro in erros:
                            st.warning(erro)
                    
                    # Roda o rerun no final para atualizar a tela
                    st.rerun()

# --- ABA 4: OPERAÇÕES ESTRUTURADAS ---
with tab_operacoes:
    st.markdown("### Registrar Nova Operação Estruturada")

    # Inicializa o estado para as pernas da operação se não existir
    if 'pernas_operacao' not in st.session_state:
        st.session_state.pernas_operacao = []

    # --- SEÇÃO PARA ADICIONAR PERNAS (FORA DO FORMULÁRIO) ---
    st.markdown("##### 1. Adicione as Pernas da Operação")
    col_perna1, col_perna2, col_perna3, col_perna4, col_perna5, col_perna6 = st.columns(6)
    with col_perna1:
        codigo_opcao = st.text_input("Código da Opção", key="codigo_opcao")
    with col_perna2:
        strike_perna = st.number_input("Strike (R$)", min_value=0.0, format="%.2f", key="strike_perna")
    with col_perna3:
        tipo_operacao = st.selectbox("Operação", ["compra", "venda"], key="tipo_operacao")
    with col_perna4:
        quantidade_perna = st.number_input("Quantidade", min_value=1, step=100, key="qtd_perna")
    with col_perna5:
        preco_entrada = st.number_input("Preço Entrada (R$)", min_value=0.0, format="%.2f", key="preco_entrada")
    with col_perna6:
        data_vencimento = st.date_input("Vencimento", value=utils.get_local_today() + relativedelta(months=1), key="venc_perna")

    if st.button("Adicionar Perna à Lista"):
        if codigo_opcao and strike_perna > 0 and quantidade_perna > 0:
            st.session_state.pernas_operacao.append({
                "codigo_opcao": codigo_opcao.upper(),
                "tipo_opcao": "CALL" if 'C' in codigo_opcao.upper() else "PUT",
                "strike": strike_perna,
                "tipo_operacao": tipo_operacao,
                "quantidade": quantidade_perna,
                "preco_entrada": preco_entrada,
                "data_vencimento": data_vencimento
            })
            st.rerun()
        else:
            st.warning("Preencha todos os campos da perna, incluindo o Strike.")

    # --- FORMULÁRIO PARA SALVAR A OPERAÇÃO COMPLETA ---
    st.markdown("---")
    st.markdown("##### 2. Salve a Estratégia Completa")
    with st.form("form_nova_operacao"):
        if st.session_state.pernas_operacao:
            st.markdown("###### Pernas a serem registradas:")
            df_pernas = pd.DataFrame(st.session_state.pernas_operacao)
            st.dataframe(df_pernas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma perna adicionada à operação ainda.")

        st.markdown("###### Detalhes da Estratégia")
        c1, c2, c3 = st.columns(3)
        with c1:
            ativo_subjacente = st.text_input("Ativo Subjacente (ex: PETR4)")
        with c2:
            nome_estrategia = st.text_input("Nome da Estratégia (ex: Trava de Alta)")
        with c3:
            data_montagem = st.date_input("Data de Montagem", value=utils.get_local_today())

        submitted = st.form_submit_button("Salvar Operação Estruturada", type="primary")
        if submitted:
            if not ativo_subjacente or not nome_estrategia or not st.session_state.pernas_operacao:
                st.error("Preencha os detalhes da estratégia e adicione pelo menos uma perna antes de salvar.")
            else:
                try:
                    database.add_operacao_estruturada(user_id, ativo_subjacente.upper(), nome_estrategia, data_montagem.isoformat(), st.session_state.pernas_operacao)
                    st.success("Operação estruturada salva com sucesso!")
                    st.session_state.pernas_operacao = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar a operação: {e}")

    # --- VISUALIZAÇÃO E GERENCIAMENTO DAS OPERAÇÕES EM ABERTO ---
    st.markdown("---")
    st.markdown("### Operações em Aberto")
    operacoes_abertas = database.get_operacoes_estruturadas(user_id, "Aberta")

    if not operacoes_abertas:
        st.info("Nenhuma operação estruturada em aberto.")
    else:
        df_ops = pd.DataFrame(operacoes_abertas, columns=['ID', 'Ativo', 'Estratégia', 'Data Montagem', 'Status', 'Perna ID', 'Código Opção', 'Tipo', 'C/V', 'Strike', 'Qtd', 'Preço Entrada', 'Vencimento'])
        for operacao_id, group in df_ops.groupby('ID'):
            info = group.iloc[0]
            custo_montagem = (group.apply(lambda row: row['Preço Entrada'] * row['Qtd'] if row['C/V'] == 'compra' else -row['Preço Entrada'] * row['Qtd'], axis=1)).sum()

            with st.expander(f"**{info['Estratégia']} em {info['Ativo']}** (Montada em: {info['Data Montagem'].strftime('%d/%m/%Y')})"):
                with st.form(key=f"form_edit_{operacao_id}"):
                    st.markdown("##### Editar Operação")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        novo_ativo = st.text_input("Ativo Subjacente", value=info['Ativo'], key=f"ativo_{operacao_id}")
                    with c2:
                        nova_estrategia = st.text_input("Nome da Estratégia", value=info['Estratégia'], key=f"estr_{operacao_id}")
                    with c3:
                        nova_data = st.date_input("Data de Montagem", value=info['Data Montagem'], key=f"data_{operacao_id}")

                    st.markdown("###### Editar Pernas")
                    df_edit_pernas = group[['Perna ID', 'Código Opção', 'C/V', 'Strike', 'Qtd', 'Preço Entrada', 'Vencimento']].copy()
                    df_edit_pernas['Excluir'] = False
                    edited_df = st.data_editor(
                        df_edit_pernas, use_container_width=True, hide_index=True,
                        column_config={
                            "Perna ID": None, "Código Opção": st.column_config.TextColumn("Código", required=True),
                            "C/V": st.column_config.SelectboxColumn("C/V", options=["compra", "venda"], required=True),
                            "Strike": st.column_config.NumberColumn("Strike", format="R$ %.2f", required=True),
                            "Qtd": st.column_config.NumberColumn("Qtd", min_value=1, required=True),
                            "Preço Entrada": st.column_config.NumberColumn("Preço Entrada", format="R$ %.2f", required=True),
                            "Vencimento": st.column_config.DateColumn("Vencimento", required=True),
                            "Excluir": st.column_config.CheckboxColumn("Excluir?", default=False)
                        }, key=f"editor_pernas_{operacao_id}"
                    )
                    
                    col_save, col_delete_op = st.columns([4, 1.1])
                    with col_save:
                        if st.form_submit_button("Salvar Alterações na Operação", type="primary"):
                            database.update_operacao_header(operacao_id, novo_ativo.upper(), nova_estrategia, nova_data.isoformat())
                            for _, row in edited_df.iterrows():
                                perna_id = row['Perna ID']
                                if row['Excluir']:
                                    database.delete_operacao_perna(perna_id)
                                else:
                                    database.update_operacao_perna(perna_id, row['Código Opção'], row['C/V'], row['Strike'], row['Qtd'], row['Preço Entrada'], row['Vencimento'])
                            st.success(f"Operação '{nova_estrategia}' atualizada com sucesso!")
                            st.rerun()
                    with col_delete_op:
                        if st.form_submit_button("Excluir Tudo"):
                            database.delete_operacao_inteira(operacao_id)
                            st.warning(f"Operação '{info['Estratégia']}' foi excluída permanentemente.")
                            st.rerun()

                st.markdown("---")
                st.markdown("##### Desmontar Operação")
                st.metric("Custo de Montagem", utils.formatar_moeda_brl(custo_montagem))
                
                pernas_saida = {}
                # O loop permanece o mesmo
                for _, perna in group.iterrows():
                    codigo = perna['Código Opção']
                    perna_id = perna['Perna ID'] # Usamos o ID da perna para a chave
                    
                    # A chave agora inclui o perna_id, garantindo que seja 100% única
                    preco_saida = st.number_input(
                        f"Preço de Saída para {codigo}", 
                        min_value=0.0, 
                        format="%.2f", 
                        key=f"saida_{operacao_id}_{perna_id}" # <<< CHAVE CORRIGIDA
                    )
                    # Ainda usamos o 'codigo' como chave do dicionário, o que está correto
                    pernas_saida[codigo] = preco_saida

                if st.button("Confirmar Desmontagem", key=f"desmontar_{operacao_id}"):
                    try:
                        database.desmontar_operacao(operacao_id, utils.get_local_today().isoformat(), pernas_saida)
                        st.success(f"Operação {info['Estratégia']} fechada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao desmontar operação: {e}")

    # --- HISTÓRICO DE OPERAÇÕES FINALIZADAS ---
    st.markdown("---")
    st.markdown("### Histórico de Operações Finalizadas")

    operacoes_finalizadas = database.get_operacoes_finalizadas(user_id)

    if not operacoes_finalizadas:
        st.info("Nenhuma operação finalizada encontrada.")
    else:
        df_finalizadas = pd.DataFrame(operacoes_finalizadas, columns=[
            'ID', 'Ativo', 'Estratégia', 'Data Montagem', 'Data Finalização', 
            'Status', 'Resultado R$', 'Código Opção', 'Opção (C/P)', 
            'Operação (C/V)', 'Strike', 'Qtd'
        ])

        for ativo, df_ativo in df_finalizadas.groupby('Ativo'):
            with st.expander(f"**Ativo: {ativo}**"):
                for operacao_id, group in df_ativo.groupby('ID'):
                    info = group.iloc[0]
                    resultado_reais = info['Resultado R$']
                    valor_nocional = (group['Strike'] * group['Qtd']).sum()
                    resultado_percentual = (resultado_reais / valor_nocional * 100) if valor_nocional > 0 else 0

                    st.markdown(f"##### {info['Estratégia']} (Finalizada em: {info['Data Finalização'].strftime('%d/%m/%Y')})")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Resultado Financeiro", f"{utils.formatar_moeda_brl(resultado_reais)}")
                    with col2:
                        st.metric("Resultado Percentual", f"{resultado_percentual:.2f}%")
                    with col3:
                        st.metric("Valor Nocional (Aprox.)", f"{utils.formatar_moeda_brl(valor_nocional)}")

                    st.markdown(f"Status final: **{info['Status']}**")
                    
                    df_display = group[['Código Opção', 'Opção (C/P)', 'Operação (C/V)', 'Strike', 'Qtd']]
                    st.markdown("###### Pernas da Operação:")
                    st.dataframe(df_display, use_container_width=True, hide_index=True)

                    # --- NOVOS BOTÕES DE AÇÃO ---
                    st.markdown("###### Ações:")
                    col_actions1, col_actions2 = st.columns([1, 1.5])
                    with col_actions1:
                        if st.button("Reabrir Operação", key=f"reabrir_{operacao_id}", help="Mover esta operação de volta para 'Operações em Aberto' para edição."):
                            try:
                                database.reabrir_operacao(operacao_id)
                                st.success(f"Operação '{info['Estratégia']}' foi reaberta! Você pode editá-la na seção 'Operações em Aberto'.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao reabrir operação: {e}")
                    
                    with col_actions2:
                        if st.button("Excluir Permanentemente", key=f"excluir_hist_{operacao_id}", type="primary"):
                            try:
                                database.delete_operacao_inteira(operacao_id)
                                st.warning(f"Operação '{info['Estratégia']}' foi excluída do histórico.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir operação: {e}")
                    
                    st.markdown("---")
