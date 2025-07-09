# app.py (versão corrigida para ser a sua Home)
import streamlit as st
import streamlit_authenticator as stauth
import database
import datetime
import pandas as pd
import utils # Certifique-se que o utils.py está na mesma pasta
import plotly.express as px
from dateutil.relativedelta import relativedelta

def render_home_page(user_id):
    st.title("Visão Geral Financeira")
    
    
    # --- INÍCIO DA NOVA SEÇÃO: BOTÕES DE ACESSO RÁPIDO ---
    st.markdown("### Acesso Rápido")
    col1, col2, col3 = st.columns(3)

    # Botão para Adicionar Receita
    with col1:
        with st.popover("➕ Adicionar Receita", use_container_width=True):
            st.markdown("#### Nova Receita")
            # Busca os dados necessários para o formulário
            contas = database.get_contas(user_id)
            categorias_receita = database.get_categorias(user_id, "receita")
            if not contas or not categorias_receita:
                st.warning("É preciso ter ao menos uma conta e uma categoria de receita cadastradas.")
            else:
                contas_dict = {conta[1]: conta[0] for conta in contas}
                categorias_list = [cat[1] for cat in categorias_receita]
                with st.form("form_popover_receita"):
                    descricao = st.text_input("Descrição da Receita", key="pop_rec_desc")
                    valor = st.number_input("Valor", min_value=0.01, format="%.2f", key="pop_rec_val")
                    data = st.date_input("Data", value=utils.get_local_today(), key="pop_rec_data")
                    conta_nome = st.selectbox("Conta", options=list(contas_dict.keys()), key="pop_rec_conta")
                    categoria_nome = st.selectbox("Categoria", options=categorias_list, key="pop_rec_cat")

                    if st.form_submit_button("Salvar Receita"):
                        if descricao.strip() and valor > 0:
                            database.insert_receita(user_id, contas_dict[conta_nome], data.isoformat(), valor, categoria_nome, descricao.strip())
                            st.toast("Receita adicionada!", icon="✅")
                            st.rerun()
                        else:
                            st.warning("Preencha todos os campos.")

    # Botão para Adicionar Despesa
    with col2:
        with st.popover("➖ Adicionar Despesa", use_container_width=True):
            st.markdown("#### Nova Despesa")
            contas = database.get_contas(user_id)
            categorias_despesa = database.get_categorias(user_id, "despesa")
            if not contas or not categorias_despesa:
                st.warning("É preciso ter ao menos uma conta e uma categoria de despesa cadastradas.")
            else:
                contas_dict_desp = {conta[1]: conta[0] for conta in contas}
                categorias_list_desp = [cat[1] for cat in categorias_despesa]
                with st.form("form_popover_despesa"):
                    descricao = st.text_input("Descrição da Despesa", key="pop_desp_desc")
                    valor = st.number_input("Valor Total", min_value=0.01, format="%.2f", key="pop_desp_val")
                    data_compra = st.date_input("Data da Compra", value=utils.get_local_today(), key="pop_desp_data")
                    tipo_pagamento = st.radio("Pagamento", ["crédito", "débito"], horizontal=True, key="pop_desp_tipo")
                    parcelas = st.number_input("Parcelas", min_value=1, step=1, value=1, key="pop_desp_parc")
                    conta_nome = st.selectbox("Conta", options=list(contas_dict_desp.keys()), key="pop_desp_conta")
                    categoria = st.selectbox("Categoria", options=categorias_list_desp, key="pop_desp_cat")

                    if st.form_submit_button("Salvar Despesa"):
                        if descricao.strip() and valor > 0:
                            database.insert_despesa(user_id, contas_dict_desp[conta_nome], data_compra.isoformat(), valor, categoria, tipo_pagamento, parcelas, descricao.strip())
                            st.toast("Despesa adicionada!", icon="✅")
                            st.rerun()
                        else:
                            st.warning("Preencha todos os campos.")
    with col3:
        with st.popover("🔄 Transferir Entre Contas", use_container_width=True):
            st.markdown("#### Nova Transferência")
            contas = database.get_contas(user_id)
            
            if len(contas) < 2:
                st.warning("Você precisa de pelo menos duas contas para fazer uma transferência.")
            else:
                contas_dict = {conta[1]: conta[0] for conta in contas}
                lista_nomes_contas = list(contas_dict.keys())
                
                with st.form("form_popover_transferencia"):
                    conta_origem_nome = st.selectbox("Conta de Origem", options=lista_nomes_contas, key="pop_transf_origem")
                    conta_destino_nome = st.selectbox("Conta de Destino", options=lista_nomes_contas, index=1, key="pop_transf_destino")
                    valor = st.number_input("Valor", min_value=0.01, format="%.2f", key="pop_transf_valor")
                    data = st.date_input("Data da Transferência", value=utils.get_local_today(), key="pop_transf_data")

                    if st.form_submit_button("Confirmar Transferência"):
                        if conta_origem_nome == conta_destino_nome:
                            st.error("As contas de origem e destino devem ser diferentes.")
                        elif valor <= 0:
                            st.error("O valor deve ser maior que zero.")
                        else:
                            try:
                                conta_origem_id = contas_dict[conta_origem_nome]
                                conta_destino_id = contas_dict[conta_destino_nome]
                                database.realizar_transferencia(user_id, conta_origem_id, conta_destino_id, valor, data)
                                st.toast("Transferência realizada com sucesso!", icon="✅")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")                        
    st.markdown("---")
    # --- FIM DA NOVA SEÇÃO ---
    # --- INÍCIO DA SEÇÃO DE FILTROS ---
    st.markdown("### Filtros da Visão Geral")
    
    # 1. Busca todas as contas para popular o filtro
    contas = database.get_contas(user_id)
    if not contas:
        st.warning("Cadastre pelo menos uma conta para começar.")
        st.stop()
        
    lista_contas = {conta[1]: conta[0] for conta in contas}
    opcoes_filtro = ["Todas as Contas"] + list(lista_contas.keys())
    
    # 2. Cria o selectbox para o filtro de conta
    conta_selecionada_nome = st.selectbox("Visualizar por conta:", options=opcoes_filtro)
    # --- FIM DA SEÇÃO DE FILTROS ---
    # Seção de Lançamentos Próximos
    st.markdown("### Lançamentos Próximos")
    conta_id_filtro = lista_contas.get(conta_selecionada_nome)
    proximos_lancamentos = database.get_proximos_lancamentos(user_id, dias_futuros=3, conta_id=conta_id_filtro)

    if not proximos_lancamentos:
        st.info("Nenhum lançamento previsto para os próximos 3 dias.")
    else:
        st.write("Fique de olho nas suas próximas movimentações:")
        for data, descricao, valor, tipo in proximos_lancamentos:
            # --- LINHA CORRIGIDA ---
            data_obj = data # A conversão strptime foi removida
            # -----------------------
            
            hoje = utils.get_local_today()
            
            if data_obj == hoje:
                dia_str = "Hoje"
            elif data_obj == hoje + datetime.timedelta(days=1):
                dia_str = "Amanhã"
            else:
                dia_str = data_obj.strftime('%d/%m/%Y')
            
            valor_formatado = utils.formatar_moeda_brl(valor)

            if tipo == 'receita':
                st.success(f"**{dia_str}:** {descricao.upper()} | **+ {valor_formatado}**", icon="💰")
            else: # tipo == 'despesa'
                st.error(f"**{dia_str}:** {descricao.upper()} | **- {valor_formatado}**", icon="💸")

    st.markdown("---")
    # Seção do Fluxo de Caixa
    st.header("Fluxo de Caixa Diário")
    transacoes = database.get_transacoes_consolidadas(user_id, conta_id=conta_id_filtro)

    if not transacoes:
        st.info("Você ainda não possui transações para exibir o fluxo de caixa.")
        return

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
        fluxo_diario = fluxo_diario.set_index('data').reindex(todos_os_dias)
        fluxo_diario[['entradas', 'saidas']] = fluxo_diario[['entradas', 'saidas']].fillna(0)
        fluxo_diario['saldo_dia'] = fluxo_diario['entradas'] - fluxo_diario['saidas']
        fluxo_diario['saldo_acumulado'] = fluxo_diario['saldo_dia'].cumsum()
        fluxo_diario = fluxo_diario.reset_index().rename(columns={'index': 'data'})

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
        st.dataframe(styled_df, column_config={"data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"), "entradas": st.column_config.NumberColumn("Entradas"), "saidas": st.column_config.NumberColumn("Saídas"), "saldo_acumulado": st.column_config.NumberColumn("Saldo do Dia")}, use_container_width=True,hide_index=True)

# --- LÓGICA PRINCIPAL DE AUTENTICAÇÃO ---
# --- LÓGICA PRINCIPAL DE AUTENTICAÇÃO ---
def main():
    st.set_page_config("App Finanças", layout="wide", initial_sidebar_state="collapsed")
    
    # CSS para ocultar a sidebar se o usuário estiver deslogado
    hide_sidebar_nav_css = """
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """
    if not st.session_state.get("authentication_status"):
        st.markdown(hide_sidebar_nav_css, unsafe_allow_html=True)

    credentials = database.get_authenticator_credentials()
    
    authenticator = stauth.Authenticate(
        credentials, 
        cookie_name="app_fin_cookie",
        key="app_fin_key", 
        cookie_expiry_days=30
    )

    # Lógica para usuário LOGADO
    if st.session_state.get("authentication_status"):
        username = st.session_state['username']
        
        with st.sidebar:
            st.subheader(f"Bem-vindo, {st.session_state['name']}!")
            st.markdown("---")
            authenticator.logout("Logout", "sidebar", key="logout_button")
        
        # Renderiza a página Home
        profile = database.get_user_profile(username)
        if profile:
            user_id = profile['user_id']
            render_home_page(user_id)
        else:
            st.error("Erro ao carregar perfil do usuário.")

    # Lógica para usuário DESLOGADO (sem cadastro)
    else:
        st.subheader("Acesse sua conta")
        authenticator.login(fields={'Form name': 'Login'})
        
        if st.session_state.get("authentication_status") is False:
            st.error("Usuário ou senha incorretos.")
        elif st.session_state.get("authentication_status") is None:
            st.warning("Por favor, insira seu usuário e senha.")

if __name__ == "__main__":
    main()
