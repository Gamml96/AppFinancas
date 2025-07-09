import streamlit as st
import database
import pandas as pd
import datetime
import plotly.express as px 
from dateutil.relativedelta import relativedelta
import utils

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

st.title("Relatórios Financeiros")

# --- FILTROS ---
st.markdown("### Filtros")
# Define o primeiro e o último dia do mês atual como padrão
today = utils.get_local_today()
start_of_month = today.replace(day=1)
end_of_month = (start_of_month + relativedelta(months=1)) - datetime.timedelta(days=1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data de Início", value=start_of_month)
with col2:
    end_date = st.date_input("Data de Fim", value=end_of_month)

st.markdown("---")

# --- GRÁFICO DE DESPESAS POR CATEGORIA (PIZZA) ---
st.markdown("### Despesas por Categoria no Período")
despesas_cat = database.get_despesas_por_categoria(user_id, start_date.isoformat(), end_date.isoformat())

if not despesas_cat:
    st.info("Nenhuma despesa encontrada no período selecionado.")
else:
    df_despesas_cat = pd.DataFrame(despesas_cat, columns=['Categoria', 'Total'])
    fig = px.pie(df_despesas_cat, names='Categoria', values='Total', 
                    title='Distribuição de Despesas', hole=.3)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- HISTÓRICO MENSAL (RECEITA VS DESPESA) ---
st.markdown("### Histórico Mensal")
receitas_mensal = database.get_total_receitas_mensal(user_id)
despesas_mensal = database.get_total_despesas_mensal(user_id)

if not receitas_mensal and not despesas_mensal:
    st.info("Nenhuma movimentação mensal encontrada para gerar o histórico.")
else:
    df_receitas = pd.DataFrame(receitas_mensal, columns=['Mês', 'Receitas'])
    df_despesas = pd.DataFrame(despesas_mensal, columns=['Mês', 'Despesas'])
    
    # Junta os dois DataFrames para ter uma única fonte para o gráfico
    df_historico = pd.merge(df_receitas, df_despesas, on='Mês', how='outer').fillna(0)
    df_historico = df_historico.sort_values(by='Mês').set_index('Mês')
    
    st.bar_chart(df_historico)

st.markdown("---")
st.markdown("### Acompanhamento do Orçamento no Período")

# 1. Pega os gastos e os orçamentos
gastos_no_periodo = df_despesas_cat # Reutiliza o DataFrame do gráfico de pizza
orcamentos = database.get_orcamentos(user_id)
df_orcamentos = pd.DataFrame(orcamentos, columns=['Categoria', 'Orçamento'])

if df_orcamentos.empty:
    st.info("Você ainda não definiu nenhum orçamento. Vá para a página 'Orçamento' para começar.")
else:
    # 2. Junta as informações de gastos e orçamentos
    df_comparativo = pd.merge(gastos_no_periodo, df_orcamentos, on='Categoria', how='left').fillna(0)
    # Filtra apenas as categorias que têm um orçamento definido > 0
    df_comparativo = df_comparativo[df_comparativo['Orçamento'] > 0]

    if df_comparativo.empty:
        st.info("Nenhum gasto nas categorias com orçamento definido para este período.")
    else:
        df_comparativo['Progresso'] = df_comparativo['Total'] / df_comparativo['Orçamento']
        df_comparativo['Restante'] = df_comparativo['Orçamento'] - df_comparativo['Total']

        # 3. Mostra as barras de progresso
        for _, row in df_comparativo.iterrows():
            st.markdown(f"**{row['Categoria']}**")
            gasto_fmt = utils.formatar_moeda_brl(row['Total'])
            orcamento_fmt = utils.formatar_moeda_brl(row['Orçamento'])
            
            # Muda a cor do texto se o gasto estourou o orçamento
            if row['Progresso'] > 1:
                st.error(f"Gasto: {gasto_fmt} de {orcamento_fmt}")
            else:
                st.write(f"Gasto: {gasto_fmt} de {orcamento_fmt}")
            
            # A barra de progresso fica vermelha se passar de 100%
            st.progress(min(row['Progresso'], 1.0))
