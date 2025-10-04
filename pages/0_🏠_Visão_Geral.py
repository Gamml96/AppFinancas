import streamlit as st
import database
import pandas as pd
import datetime
import calendar
import utils

# --- AUTENTICAÇÃO ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()
st.title("Visão Geral Financeira")
st.markdown("---")

# --- BUSCA DE CONTAS ---
contas = database.get_contas(user_id)
if not contas:
    st.warning("Cadastre pelo menos uma conta para começar.")
    st.stop()
contas_dict = {conta[1]: conta[0] for conta in contas}

# --- FILTROS HORIZONTAIS ---
hoje = datetime.date.today()
meses = {i: calendar.month_name[i] for i in range(1, 13)}
meses_keys = list(meses.keys())
meses_keys.insert(0, "Todos")
mes_atual = hoje.month
index_mes = meses_keys.index(mes_atual) if mes_atual in meses_keys else 0

filtro_cols = st.columns(3)
with filtro_cols[2]:
    conta_filtro = st.selectbox("Conta", options=["Todas"] + list(contas_dict.keys()))
transacoes = database.get_transacoes_consolidadas(
    user_id, conta_id=contas_dict.get(conta_filtro) if conta_filtro != "Todas" else None
)
df = pd.DataFrame(transacoes, columns=["data", "descricao", "valor"])
df["data"] = pd.to_datetime(df["data"])
anos = sorted(df["data"].dt.year.unique()) if not df.empty else [hoje.year]
index_ano = anos.index(hoje.year) if hoje.year in anos else 0

with filtro_cols[0]:
    mes_selecionado = st.selectbox(
        "Mês",
        options=meses_keys,
        format_func=lambda x: "Todos" if x == "Todos" else meses[x],
        index=index_mes
    )
with filtro_cols[1]:
    ano_selecionado = st.selectbox("Ano", options=anos, index=index_ano)

# --- INÍCIO DA SEÇÃO: BOTÕES DE ACESSO RÁPIDO ---
st.markdown("### Acesso Rápido")
col1, col2, col3 = st.columns(3)

# Botão para Adicionar Receita
# Botão para Adicionar Receita
with col1:
    with st.popover("➕ Adicionar Receita", use_container_width=True):
        st.markdown("#### Nova Receita")
        categorias_receita = database.get_categorias(user_id, "receita")
        if not contas or not categorias_receita:
            st.warning("É preciso ter ao menos uma conta e uma categoria de receita cadastradas.")
        else:
            contas_dict_rec = {conta[1]: conta[0] for conta in contas}
            categorias_list_rec = [cat[1] for cat in categorias_receita]
            with st.form("form_popover_receita"):
                descricao_rec = st.text_input("Descrição da Receita", key="pop_rec_desc")
                valor_rec = st.number_input("Valor", min_value=0.01, format="%.2f", key="pop_rec_val")
                data_rec = st.date_input("Data", value=utils.get_local_today(), key="pop_rec_data")
                categoria_nome_rec = st.selectbox("Categoria", options=categorias_list_rec, key="pop_rec_cat")
                conta_nome_rec = st.selectbox("Conta", options=list(contas_dict_rec.keys()), key="pop_rec_conta")

                if st.form_submit_button("Salvar Receita"):
                    if not descricao_rec.strip() or valor_rec <= 0:
                        st.warning("Descrição é obrigatória e o valor deve ser positivo.")
                    else:
                        try:
                            # CORREÇÃO: Passando os parâmetros de recorrência como padrão (None e 1)
                            database.insert_receita(
                                user_id, contas_dict_rec[conta_nome_rec], data_rec.isoformat(), 
                                valor_rec, categoria_nome_rec, descricao_rec.strip(), 
                                None, 1  # Lançamento único
                            )
                            st.toast("Receita adicionada!", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ocorreu um erro ao salvar a receita: {e}")

# Botão para Adicionar Despesa
with col2:
    with st.popover("➖ Adicionar Despesa", use_container_width=True):
        st.markdown("#### Nova Despesa")
        categorias_despesa = database.get_categorias(user_id, "despesa")
        if not contas or not categorias_despesa:
            st.warning("É preciso ter ao menos uma conta e uma categoria de despesa cadastradas.")
        else:
            contas_dict_desp = {conta[1]: conta[0] for conta in contas}
            categorias_list_desp = [cat[1] for cat in categorias_despesa]
            with st.form("form_popover_despesa"):
                descricao_desp = st.text_input("Descrição da Despesa", key="pop_desp_desc")
                valor_desp = st.number_input("Valor Total", min_value=0.01, format="%.2f", key="pop_desp_val")
                data_compra_desp = st.date_input("Data da Compra", value=utils.get_local_today(), key="pop_desp_data")
                tipo_pagamento_desp = st.radio("Pagamento", ["Crédito", "Débito"], horizontal=True, key="pop_desp_tipo")
                parcelas_desp = st.number_input("Parcelas", min_value=1, step=1, value=1, key="pop_desp_parc")
                categoria_desp = st.selectbox("Categoria", options=categorias_list_desp, key="pop_desp_cat")
                conta_nome_desp = st.selectbox("Conta", options=list(contas_dict_desp.keys()), key="pop_desp_conta")

                if st.form_submit_button("Salvar Despesa"):
                    if not descricao_desp.strip() or valor_desp <= 0:
                        st.warning("Descrição é obrigatória e o valor deve ser positivo.")
                    else:
                        try:
                            # CORREÇÃO: Passando os parâmetros de recorrência como padrão (None e 1)
                            database.insert_despesa(
                                user_id, contas_dict_desp[conta_nome_desp], data_compra_desp.isoformat(), 
                                valor_desp, categoria_desp, tipo_pagamento_desp, parcelas_desp, 
                                descricao_desp.strip(), None, 1 # Lançamento único, sem recorrência
                            )
                            st.toast("Despesa adicionada!", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ocorreu um erro ao salvar a despesa: {e}")
with col3:
    with st.popover("🔄 Transferir Entre Contas", use_container_width=True):
        st.markdown("#### Nova Transferência")
        if len(contas) < 2:
            st.warning("Você precisa de pelo menos duas contas para fazer uma transferência.")
        else:
            contas_dict_transf = {conta[1]: conta[0] for conta in contas}
            lista_nomes_contas = list(contas_dict_transf.keys())
            
            with st.form("form_popover_transferencia"):
                conta_origem_nome = st.selectbox("Conta de Origem", options=lista_nomes_contas, key="pop_transf_origem")
                conta_destino_nome = st.selectbox("Conta de Destino", options=lista_nomes_contas, index=min(1, len(lista_nomes_contas)-1), key="pop_transf_destino")
                valor_transf = st.number_input("Valor", min_value=0.01, format="%.2f", key="pop_transf_valor")
                data_transf = st.date_input("Data da Transferência", value=utils.get_local_today(), key="pop_transf_data")

                if st.form_submit_button("Confirmar Transferência"):
                    if conta_origem_nome == conta_destino_nome:
                        st.error("As contas de origem e destino devem ser diferentes.")
                    elif valor_transf <= 0:
                        st.error("O valor deve ser maior que zero.")
                    else:
                        try:
                            conta_origem_id = contas_dict_transf[conta_origem_nome]
                            conta_destino_id = contas_dict_transf[conta_destino_nome]
                            database.realizar_transferencia(user_id, conta_origem_id, conta_destino_id, valor_transf, data_transf)
                            st.toast("Transferência realizada com sucesso!", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
st.markdown("---")

# --- FILTRAGEM DO DATAFRAME ---
df_filtrado = df.copy()
if mes_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["data"].dt.month == mes_selecionado]
df_filtrado = df_filtrado[df_filtrado["data"].dt.year == ano_selecionado]

# --- PRÓXIMOS LANÇAMENTOS ---
conta_id_filtro = contas_dict.get(conta_filtro) if conta_filtro != "Todas" else None
proximos_lancamentos = database.get_proximos_lancamentos(user_id, dias_futuros=3, conta_id=conta_id_filtro)

# --- SALDO ATUAL CONSOLIDADO (HOJE) ---
df = df.sort_values(by="data")
df['entradas'] = df['valor'].apply(lambda x: x if x > 0 else 0)
df['saidas'] = df['valor'].apply(lambda x: abs(x) if x < 0 else 0)
fluxo_tudo = df.groupby('data').agg(
    entradas=('entradas', 'sum'),
    saidas=('saidas', 'sum')
).reset_index()
fluxo_tudo['saldo_dia'] = fluxo_tudo['entradas'] - fluxo_tudo['saidas']
fluxo_tudo['saldo_acumulado'] = fluxo_tudo['saldo_dia'].cumsum()
saldo_atual_valor = fluxo_tudo[fluxo_tudo['data'].dt.date <= utils.get_local_today()]['saldo_acumulado'].iloc[-1] if not fluxo_tudo.empty else 0.0
st.markdown("---")
st.metric("Saldo Atual Consolidado (Hoje)", utils.formatar_moeda_brl(saldo_atual_valor))
st.markdown("---")

# --- LANÇAMENTOS PRÓXIMOS ---
if not proximos_lancamentos:
    st.info("Nenhum lançamento previsto para os próximos 3 dias.")
else:
    st.markdown("### Lançamentos Próximos")
    for data_lanc, desc, val, tipo in proximos_lancamentos:
        hoje_dt = utils.get_local_today()
        if data_lanc == hoje_dt:
            dia_str = "Hoje"
        elif data_lanc == hoje_dt + datetime.timedelta(days=1):
            dia_str = "Amanhã"
        else:
            dia_str = data_lanc.strftime('%d/%m/%Y')
        valor_formatado = utils.formatar_moeda_brl(val)
        if tipo == 'receita':
            st.success(f"**{dia_str}:** {desc.upper()} | **+ {valor_formatado}**", icon="💰")
        else:
            st.error(f"**{dia_str}:** {desc.upper()} | **- {valor_formatado}**", icon="💸")
st.markdown("---")

# --- FLUXO DE CAIXA DIÁRIO (GRÁFICO + TABELA) ---
if df.empty:
    st.info("Você ainda não possui transações para exibir o fluxo de caixa.")
else:
    st.markdown("### Fluxo de Caixa Diário")
    st.markdown("")
    if not df_filtrado.empty:
        df_temp = df_filtrado.copy().sort_values(by="data")
        df_temp['entradas'] = df_temp['valor'].apply(lambda x: x if x > 0 else 0)
        df_temp['saidas'] = df_temp['valor'].apply(lambda x: abs(x) if x < 0 else 0)
        fluxo_diario = df_temp.groupby('data').agg(
            entradas=('entradas', 'sum'),
            saidas=('saidas', 'sum')
        ).reset_index()

        if not fluxo_diario.empty:
            data_inicio = fluxo_diario['data'].min()
            data_fim_transacoes = fluxo_diario['data'].max()
            data_fim_hoje = pd.to_datetime(utils.get_local_today())
            data_fim = max(data_fim_transacoes, data_fim_hoje)
            todos_os_dias = pd.date_range(start=data_inicio, end=data_fim, freq='D')
            fluxo_diario = fluxo_diario.set_index('data').reindex(todos_os_dias, fill_value=0).reset_index().rename(columns={'index': 'data'})
            fluxo_diario['saldo_dia'] = fluxo_diario['entradas'] - fluxo_diario['saidas']

            # CORREÇÃO DO SALDO ACUMULADO PELO HISTÓRICO
            saldo_ate_dia_anterior = df[df['data'] < data_inicio]['valor'].sum() if not df.empty else 0.0
            fluxo_diario['saldo_acumulado'] = fluxo_diario['saldo_dia'].cumsum() + saldo_ate_dia_anterior

            st.line_chart(
                fluxo_diario.rename(columns={'data': 'index'}).set_index('index')['saldo_acumulado']
            )
            st.markdown("---")

            # Gradiente de cor na coluna saldo acumulado
            def highlight_today(row):
                if row.data.date() == utils.get_local_today():
                    return ['background-color: #3D5320'] * len(row)
                return [''] * len(row)

            df_display = fluxo_diario.sort_values(by="data", ascending=True)[
                ["data", "entradas", "saidas", "saldo_acumulado"]]
            vmin = 0
            vmax = df_display["saldo_acumulado"].max()
            styled_df = (
                df_display.style
                .apply(highlight_today, axis=1)
                .format({
                    "entradas": utils.formatar_moeda_brl,
                    "saidas": utils.formatar_moeda_brl,
                    "saldo_acumulado": utils.formatar_moeda_brl
                })
                .background_gradient(subset=["saldo_acumulado"], cmap="RdYlGn", vmin=vmin, vmax=vmax)
                .hide(axis="index")
            )

            st.dataframe(
                styled_df,
                column_config={
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "entradas": st.column_config.NumberColumn("Entradas"),
                    "saidas": st.column_config.NumberColumn("Saídas"),
                    "saldo_acumulado": st.column_config.NumberColumn("Saldo do Dia")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Não há dados suficientes para o gráfico/tabela no período/conta filtrado.")
    else:
        st.info("Não há dados para o período/conta filtrado selecionado.")





