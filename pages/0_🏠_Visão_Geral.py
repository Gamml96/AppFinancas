# app.py (versão corrigida para ser a sua Home)
import streamlit as st
import streamlit_authenticator as stauth
import database
import datetime
import pandas as pd
import utils # Certifique-se que o utils.py está na mesma pasta
import plotly.express as px
from dateutil.relativedelta import relativedelta

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()


# --- Conteúdo da Página ---
st.title("📊 Visão Geral Financeira")
st.markdown("---")

# --- INÍCIO DA SEÇÃO DE FILTROS ---
st.markdown("### Filtros da Visão Geral")

# Busca todas as contas para popular o filtro
contas = database.get_contas(user_id)
if not contas:
    st.warning("Cadastre pelo menos uma conta para começar.")
    st.stop()
    
lista_contas = {conta[1]: conta[0] for conta in contas}
opcoes_filtro = ["Todas as Contas"] + list(lista_contas.keys())

# Cria o selectbox para o filtro de conta
conta_selecionada_nome = st.selectbox("Visualizar por conta:", options=opcoes_filtro)
conta_id_filtro = lista_contas.get(conta_selecionada_nome) # Obter o ID da conta selecionada

# --- FIM DA SEÇÃO DE FILTROS ---

# --- INÍCIO DA SEÇÃO: BOTÕES DE ACESSO RÁPIDO ---
st.markdown("### Acesso Rápido")
col1, col2, col3 = st.columns(3)

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
                conta_nome_rec = st.selectbox("Conta", options=list(contas_dict_rec.keys()), key="pop_rec_conta")
                categoria_nome_rec = st.selectbox("Categoria", options=categorias_list_rec, key="pop_rec_cat")

                if st.form_submit_button("Salvar Receita"):
                    if not descricao_rec.strip() or valor_rec <= 0:
                        st.warning("Descrição é obrigatória e o valor deve ser positivo.")
                    else:
                        try:
                            # A lógica de recorrência não está no popover, então passamos None/1
                            database.insert_receita(user_id, contas_dict_rec[conta_nome_rec], data_rec.isoformat(), valor_rec, categoria_nome_rec, descricao_rec.strip(), None, 1)
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
                conta_nome_desp = st.selectbox("Conta", options=list(contas_dict_desp.keys()), key="pop_desp_conta")
                categoria_desp = st.selectbox("Categoria", options=categorias_list_desp, key="pop_desp_cat")

                if st.form_submit_button("Salvar Despesa"):
                    if not descricao_desp.strip() or valor_desp <= 0:
                        st.warning("Descrição é obrigatória e o valor deve ser positivo.")
                    else:
                        try:
                            # A lógica de recorrência não está no popover, então passamos None/1
                            database.insert_despesa(user_id, contas_dict_desp[conta_nome_desp], data_compra_desp.isoformat(), valor_desp, categoria_desp, tipo_pagamento_desp, parcelas_desp, descricao_desp.strip(), None, 1)
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
# --- FIM DA SEÇÃO ---

# Seção de Lançamentos Próximos
st.markdown("### Lançamentos Próximos")
proximos_lancamentos = database.get_proximos_lancamentos(user_id, dias_futuros=3, conta_id=conta_id_filtro)

if not proximos_lancamentos:
    st.info("Nenhum lançamento previsto para os próximos 3 dias.")
else:
    st.write("Fique de olho nas suas próximas movimentações:")
    for data_lanc, desc, val, tipo in proximos_lancamentos:
        hoje = utils.get_local_today()
        
        if data_lanc == hoje:
            dia_str = "Hoje"
        elif data_lanc == hoje + datetime.timedelta(days=1):
            dia_str = "Amanhã"
        else:
            dia_str = data_lanc.strftime('%d/%m/%Y')
        
        valor_formatado = utils.formatar_moeda_brl(val)

        if tipo == 'receita':
            st.success(f"**{dia_str}:** {desc.upper()} | **+ {valor_formatado}**", icon="💰")
        else:
            st.error(f"**{dia_str}:** {desc.upper()} | **- {valor_formatado}**", icon="💸")

st.markdown("---")
# Seção do Fluxo de Caixa
st.header("Fluxo de Caixa Diário")
transacoes = database.get_transacoes_consolidadas(user_id, conta_id=conta_id_filtro)

if not transacoes:
    st.info("Você ainda não possui transações para exibir o fluxo de caixa.")
else:
    df = pd.DataFrame(transacoes, columns=["data", "descricao", "valor"])
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values(by="data")

    df['entradas'] = df['valor'].apply(lambda x: x if x > 0 else 0)
    df['saidas'] = df['valor'].apply(lambda x: abs(x) if x < 0 else 0)

    fluxo_diario = df.groupby('data').agg(
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
        fluxo_diario['saldo_acumulado'] = fluxo_diario['saldo_dia'].cumsum()

        saldo_atual_valor = fluxo_diario[fluxo_diario['data'].dt.date <= utils.get_local_today()]['saldo_acumulado'].iloc[-1] if not fluxo_diario.empty else 0.0
        st.metric("Saldo Atual Consolidado (Hoje)", utils.formatar_moeda_brl(saldo_atual_valor))
        st.markdown("---")
        st.markdown("### Evolução do Saldo")
        st.line_chart(fluxo_diario.rename(columns={'data':'index'}).set_index('index')['saldo_acumulado'])
        st.markdown("---")
        st.markdown("### Detalhamento do Fluxo de Caixa")

        def highlight_today(row):
            if row.data.date() == utils.get_local_today():
                return ['background-color: #3D5320'] * len(row)
            return [''] * len(row)

        df_display = fluxo_diario.sort_values(by="data", ascending=True)[["data", "entradas", "saidas", "saldo_acumulado"]]
        styled_df = df_display.style.apply(highlight_today, axis=1).format({"entradas": utils.formatar_moeda_brl, "saidas": utils.formatar_moeda_brl, "saldo_acumulado": utils.formatar_moeda_brl}).hide(axis="index")
        st.dataframe(styled_df, column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "entradas": st.column_config.NumberColumn("Entradas"), "saidas": st.column_config.NumberColumn("Saídas"), "saldo_acumulado": st.column_config.NumberColumn("Saldo do Dia")}, use_container_width=True, hide_index=True)
