import streamlit as st
import database
import pandas as pd
import datetime
import utils
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import calendar

# Guarda de Autenticação
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# Criação das Abas
tab_despesas, tab_simulacao = st.tabs(["Inserir Despesa", "Simular Despesa"])

with tab_despesas:
    # Conteúdo da Página
    contas = database.get_contas(user_id)
    categorias_despesa = database.get_categorias(user_id, "despesa")

    st.title("Gerenciar Despesas")
    if not contas:
        st.warning("Cadastre uma conta para adicionar despesas.")
    if not categorias_despesa:
        st.warning("Cadastre uma categoria de despesa para continuar.")

    contas_dict = {conta[1]: conta[0] for conta in contas}
    categorias_list = [cat[1] for cat in categorias_despesa]

    with st.form("form_nova_despesa"):
        st.markdown("### Adicionar Nova Despesa")
        descricao = st.text_input("Descrição da Despesa")
        valor = st.number_input("Valor", min_value=0.01, format="%.2f",
                                help="Para parcelas, insira o valor total da compra. Para recorrências, insira o valor de cada ocorrência.")
        data_compra = st.date_input("Data da Primeira Ocorrência/Compra", value=utils.get_local_today())
        categoria = st.selectbox("Categoria", options=categorias_list)
        conta_nome = st.selectbox("Conta", options=list(contas_dict.keys()))

        st.markdown("---")
        st.markdown("#### Detalhes de Pagamento e Repetição")

        col1, col2 = st.columns(2)
        with col1:
            tipo_pagamento = st.radio("Tipo de Pagamento", ["Crédito", "Débito"],
                                      horizontal=True, key="tipo_pagamento")
            parcelas_input = st.number_input("Nº de Parcelas", min_value=1, step=1,
                                             help="Para compras parceladas. Para assinaturas, use a Recorrência ao lado.")
        with col2:
            recorrencia_freq_input = st.selectbox("Frequência da Recorrência",
                                                  ["Única", "Diária", "Semanal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"],
                                                  key="recorrencia_freq")
            recorrencia_vezes_input = st.number_input("Repetir por (vezes)", min_value=1, step=1,
                                                      help="Deixe 1 para um lançamento único.")

        if st.form_submit_button("Adicionar Despesa"):
            if not descricao.strip() or valor <= 0:
                st.warning("Descrição é obrigatória e o valor deve ser positivo.")
            else:
                # Lógica de Sanitização de Entrada
                parcelas_final = parcelas_input
                recorrencia_freq_final = None
                recorrencia_vezes_final = 1

                # Se o usuário escolheu uma recorrência, ela tem prioridade.
                if recorrencia_freq_input != "Única" and recorrencia_vezes_input > 1:
                    recorrencia_freq_final = recorrencia_freq_input
                    recorrencia_vezes_final = recorrencia_vezes_input
                    parcelas_final = 1
                try:
                    database.insert_despesa(
                        user_id=user_id,
                        conta_id=contas_dict[conta_nome],
                        data_compra_str=data_compra.isoformat(),
                        valor=valor,
                        categoria=categoria,
                        tipo_pagamento=tipo_pagamento,
                        parcelas=parcelas_final,
                        descricao=descricao.strip(),
                        recorrencia_freq=recorrencia_freq_final,
                        recorrencia_vezes=recorrencia_vezes_final
                    )
                    st.toast(f"Despesa '{descricao}' adicionada com sucesso!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ocorreu um erro ao salvar a despesa: {e}")

    st.markdown("---")
    despesas = database.get_despesas(user_id)
    if not despesas:
        st.info("Nenhuma despesa cadastrada.")
    else:
        # Montagem do DataFrame
        df = pd.DataFrame(despesas, columns=[
            "ID", "user_id", "conta_id", "Data Compra", "Data Vencimento", "Valor",
            "Categoria", "Tipo", "Parcela", "Descrição", "Recorrência", "Grupo ID"
        ])
        # Conversão de datas
        df["Data Compra"] = pd.to_datetime(df["Data Compra"])
        df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"])
        df["Conta"] = df["conta_id"].map({v: k for k, v in contas_dict.items()})
        df["Excluir"] = False

       # ====== FILTROS AVANÇADOS EM LINHA ======
        st.markdown("### Filtros das Despesas")
        
        meses = {i: calendar.month_name[i] for i in range(1, 13)}
        meses_keys = list(meses.keys())
        meses_keys.insert(0, "Todos")
        anos = sorted(df["Data Vencimento"].dt.year.unique())
        ano_atual = datetime.datetime.now().year
        index_ano = anos.index(ano_atual) if ano_atual in anos else 0

        filtro_cols = st.columns(5)
        with filtro_cols[0]:
            mes_selecionado = st.selectbox(
                "Mês",
                options=meses_keys,
                format_func=lambda x: "Todos" if x == "Todos" else meses[x],
                key="mes_vencimento_filtro"
            )
        with filtro_cols[1]:
            ano_selecionado = st.selectbox("Ano", options=anos, index=index_ano, key="ano_receita_filtro")
        with filtro_cols[2]:
            categoria_filtro = st.selectbox("Categoria", options=["Todas"] + categorias_list, key="categoria_filtro")
        with filtro_cols[3]:
            conta_filtro = st.selectbox("Conta", options=["Todas"] + list(contas_dict.keys()), key="conta_filtro")
        with filtro_cols[4]:
            tipo_filtro = st.selectbox("Tipo", options=["Todos", "Crédito", "Débito"], key="tipo_filtro")
        

        df_filtrado = df.copy()

        # Filtro de mês e ano: se "Todos", ignora mês e filtra só ano
        if mes_selecionado != "Todos":
            df_filtrado = df_filtrado[
                (df_filtrado["Data Vencimento"].dt.month == mes_selecionado) &
                (df_filtrado["Data Vencimento"].dt.year == ano_selecionado)
            ]
        else:
            df_filtrado = df_filtrado[
                (df_filtrado["Data Vencimento"].dt.year == ano_selecionado)
            ]

        if categoria_filtro != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Categoria"] == categoria_filtro]
        if conta_filtro != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Conta"] == conta_filtro]
        if tipo_filtro != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Tipo"] == tipo_filtro]

        st.markdown("### Despesas Lançadas (Filtradas)")
        st.warning(
            "A edição na tabela afeta apenas a parcela individual. "
            "Para alterar a compra inteira, exclua as parcelas e adicione-a novamente.",
            icon="⚠️"
        )

        edited_df = st.data_editor(
            df_filtrado,
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None, "user_id": None, "conta_id": None, "Parcela": None, "Recorrência": None, "Grupo ID": None,
                "Descrição": st.column_config.TextColumn(required=True),
                "Tipo": st.column_config.SelectboxColumn(options=["Crédito", "Débito"], required=True),
                "Valor": st.column_config.NumberColumn(format="R$ %.2f", required=True),
                "Conta": st.column_config.SelectboxColumn(options=list(contas_dict.keys()), required=True),
                "Categoria": st.column_config.SelectboxColumn(options=categorias_list, required=True),
                "Data Compra": st.column_config.DateColumn(required=True),
                "Data Vencimento": st.column_config.DateColumn(required=True)
            },
            key="despesas_editor"
        )

        c1, c2 = st.columns(2)
        if c1.button("Salvar Alterações em Despesas"):
            for _, row in edited_df.iterrows():
                database.update_despesa(
                    int(row["ID"]), user_id, contas_dict[row["Conta"]],
                    row["Data Compra"].isoformat(), row["Data Vencimento"].isoformat(),
                    float(row["Valor"]), row["Categoria"], row["Descrição"]
                )
            st.toast("Despesas atualizadas!", icon="✅")
            st.rerun()

        if c2.button("Excluir Despesas Selecionadas"):
            selected = edited_df[edited_df["Excluir"]]
            if not selected.empty:
                for _, row in selected.iterrows():
                    database.delete_despesa(int(row["ID"]), user_id)
                st.toast(f"{len(selected)} despesa(s) excluída(s)!", icon="🗑️")
                st.rerun()
            else:
                st.toast("Nenhuma despesa selecionada.", icon="⚠️")

with tab_simulacao:
    st.title("🎯 Simulador de Impacto de Despesas")
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None

    transacoes_atuais = database.get_transacoes_consolidadas(user_id, None)
    if not transacoes_atuais:
        st.warning("Você precisa ter transações registadas para poder usar o simulador.")
        st.stop()

    if st.session_state.simulation_results is None:
        st.info("Verifique como uma nova despesa afetaria o seu fluxo de caixa futuro antes de a realizar.")
        st.markdown("---")
        st.markdown("### 1. Insira os dados da nova despesa")

        contas = database.get_contas(user_id)
        contas_dict = {conta[1]: conta[0] for conta in contas}
        contas_info = {conta[0]: conta for conta in contas}

        with st.form("form_simulacao"):
            col1, col2 = st.columns(2)
            with col1:
                descricao = st.text_input("Descrição da Despesa")
                valor = st.number_input("Valor Total da Compra", min_value=0.01, format="%.2f")
                data_compra = st.date_input("Data da Compra", value=utils.get_local_today())
                conta_nome = st.selectbox("Conta que seria usada", options=list(contas_dict.keys()))
            with col2:
                tipo_pagamento = st.radio("Tipo de Pagamento", ["Crédito", "Débito"], horizontal=True)
                parcelas = st.number_input("Número de Parcelas", min_value=1, step=1, value=1)

            submitted = st.form_submit_button("Analisar Impacto Financeiro", type="primary")

        if submitted:
            if not descricao.strip() or valor <= 0:
                st.error("Por favor, preencha a descrição e um valor válido para a simulação.")
            else:
                # --- Lógica da Simulação ---
                df_atual = pd.DataFrame(transacoes_atuais, columns=["data", "descricao", "valor"])
                df_atual["data"] = pd.to_datetime(df_atual["data"])
                df_atual = df_atual.sort_values(by="data")
                fluxo_diario_atual = df_atual.groupby('data')['valor'].sum().reset_index()

                data_inicio_atual = fluxo_diario_atual['data'].min()
                data_fim_atual = max(fluxo_diario_atual['data'].max(), pd.to_datetime(utils.get_local_today()))
                todos_os_dias = pd.date_range(start=data_inicio_atual, end=data_fim_atual + relativedelta(years=1), freq='D')
                df_completo_atual = fluxo_diario_atual.set_index('data').reindex(todos_os_dias, fill_value=0).reset_index().rename(columns={'index': 'data'})
                df_completo_atual['saldo_acumulado_atual'] = df_completo_atual['valor'].cumsum()

                despesas_simuladas = []
                conta_id_selecionada = contas_dict[conta_nome]
                valor_parcela_padrao = round(valor / parcelas, 2)
                diferenca = round(valor - (valor_parcela_padrao * parcelas), 2)

                if tipo_pagamento == 'Crédito':
                    info_conta = contas_info[conta_id_selecionada]
                    vencimento_base = utils._calcular_vencimento_credito(data_compra, info_conta[2], info_conta[5])
                else:
                    vencimento_base = data_compra

                for i in range(parcelas):
                    valor_parcela = (valor_parcela_padrao + diferenca) if i == 0 else valor_parcela_padrao
                    data_vencimento = vencimento_base + relativedelta(months=i)
                    despesas_simuladas.append({
                        "data": data_vencimento,
                        "descricao": f"[SIMULAÇÃO] {descricao} ({i+1}/{parcelas})",
                        "valor": -valor_parcela
                    })

                df_simulado = pd.DataFrame(despesas_simuladas)
                df_simulado["data"] = pd.to_datetime(df_simulado["data"])

                df_combinado = pd.concat([df_atual, df_simulado], ignore_index=True)
                df_combinado = df_combinado.sort_values(by="data")
                fluxo_diario_combinado = df_combinado.groupby('data')['valor'].sum().reset_index()

                data_fim_combinado = max(fluxo_diario_combinado['data'].max(), pd.to_datetime(utils.get_local_today()))
                todos_os_dias_combinado = pd.date_range(start=data_inicio_atual, end=data_fim_combinado + relativedelta(years=1), freq='D')
                df_completo_simulado = fluxo_diario_combinado.set_index('data').reindex(todos_os_dias_combinado, fill_value=0).reset_index().rename(columns={'index': 'data'})
                df_completo_simulado['saldo_acumulado_simulado'] = df_completo_simulado['valor'].cumsum()

                df_final = pd.merge(df_completo_atual, df_completo_simulado[['data', 'saldo_acumulado_simulado']], on='data', how='left')
                df_final['saldo_acumulado_simulado'] = df_final['saldo_acumulado_simulado'].fillna(method='ffill')

                st.session_state.simulation_results = {
                    "df_final": df_final,
                    "df_simulado": df_simulado
                }
                st.rerun()

    # Mostrar os resultados da simulação se houver
    if st.session_state.simulation_results is not None:
        results = st.session_state.simulation_results
        df_final = results['df_final']
        df_simulado = results['df_simulado']

        st.markdown("### 2. Resultado da Simulação")

        saldo_negativo_df = df_final[df_final['saldo_acumulado_simulado'] < 0]

        col_res, col_btn = st.columns([4, 1])

        with col_res:
            if not saldo_negativo_df.empty:
                primeira_data_negativa = saldo_negativo_df['data'].iloc[0]
                menor_saldo = saldo_negativo_df['saldo_acumulado_simulado'].min()
                st.error(
                    f"🚨 **Alerta de Risco!** Esta despesa tornaria o seu saldo negativo a partir de "
                    f"**{primeira_data_negativa.strftime('%d/%m/%Y')}**, atingindo um mínimo de "
                    f"**{utils.formatar_moeda_brl(menor_saldo)}**.",
                    icon="🔥"
                )
            else:
                st.success(
                    "✅ **Análise Concluída:** A inclusão desta despesa **não** tornaria o seu saldo negativo no período analisado.",
                    icon="👍"
                )

        with col_btn:
            if st.button("🔄 Fazer Nova Simulação", use_container_width=True):
                st.session_state.simulation_results = None
                st.rerun()

        st.markdown("#### Comparativo do Fluxo de Caixa")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_final['data'], y=df_final['saldo_acumulado_atual'],
            mode='lines', name='Saldo Atual', line=dict(color='royalblue', width=2)))
        fig.add_trace(go.Scatter(
            x=df_final['data'], y=df_final['saldo_acumulado_simulado'],
            mode='lines', name='Saldo Simulado (com a nova despesa)', line=dict(color='firebrick', width=2, dash='dash')))
        fig.update_layout(
            title_text='Evolução do Saldo Acumulado: Cenário Atual vs. Simulado',
            xaxis_title='Data', yaxis_title='Saldo Acumulado (R$)', legend_title="Cenários")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Detalhes das Parcelas Simuladas")
        st.dataframe(
            df_simulado.rename(
                columns={"data": "Data de Vencimento", "descricao": "Descrição da Parcela", "valor": "Valor da Parcela"}
            ).style.format({"Valor da Parcela": utils.formatar_moeda_brl}),
            hide_index=True,
            use_container_width=True
        )


