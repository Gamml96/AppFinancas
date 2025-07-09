import streamlit as st
import database
import pandas as pd
import datetime
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

contas = database.get_contas(user_id)
# --- Conteúdo da Página ---

st.title("Fatura do Cartão de Crédito")

# Filtra apenas as contas que têm dias de fechamento, assumindo que são cartões de crédito.
contas_cartao = [conta for conta in contas if conta[5] is not None and conta[5] > 0]

if not contas_cartao:
    st.info("Você não possui contas configuradas como cartão de crédito (com dia de fechamento).")
    st.write("Vá para a aba 'Contas' e edite uma conta, adicionando um valor para 'Dias antes do vencimento para fechar a fatura'.")
    

contas_dict = {conta[1]: conta[0] for conta in contas_cartao}

# --- FILTROS ---
col1, col2, col3 = st.columns(3)
with col1:
    conta_selecionada_nome = st.selectbox("Selecione o Cartão de Crédito", options=list(contas_dict.keys()))
    conta_selecionada_id = contas_dict[conta_selecionada_nome]

# Gera uma lista de meses e anos para o selectbox
meses_anos = sorted(list(set([(utils.get_local_today() + relativedelta(months=i)).strftime("%Y-%m") for i in range(-12, 2)])), reverse=True)

with col2:
    mes_ano_selecionado = st.selectbox("Selecione a Fatura (Vencimento)", options=meses_anos)

ano, mes = map(int, mes_ano_selecionado.split('-'))

# --- EXIBIÇÃO DA FATURA ---
fatura_itens = database.get_fatura_cartao(user_id, conta_selecionada_id, mes, ano)

if not fatura_itens:
    st.warning(f"Nenhuma despesa encontrada para a fatura de {mes:02d}/{ano} neste cartão.")
else:
    df_fatura = pd.DataFrame(fatura_itens, columns=['Data da Compra', 'Descrição', 'Valor'])
    df_fatura['Data da Compra'] = pd.to_datetime(df_fatura['Data da Compra']).dt.strftime('%d/%m/%Y')
    
    valor_total_fatura = df_fatura['Valor'].sum()

    st.markdown("---")
    st.metric(f"Valor Total da Fatura de {mes:02d}/{ano}", f"R$ {utils.formatar_moeda_brl(valor_total_fatura)}")
    
    st.dataframe(
        df_fatura,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn(format="R$ %.2f")
        }
    )
