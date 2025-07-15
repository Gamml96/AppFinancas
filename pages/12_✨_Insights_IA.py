# Em pages/✨_Insights_IA.py

import streamlit as st
import utils
import insights_module
import datetime
from dateutil.relativedelta import relativedelta

# Guarda de Autenticação
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("✨ Insights com Inteligência Artificial")
st.write("Selecione um período e receba uma análise personalizada sobre sua saúde financeira.")

# --- SELEÇÃO DE PERÍODO ---
st.markdown("##### 1. Escolha o período da análise")

# Define as datas padrão (últimos 30 dias)
today = utils.get_local_today()
start_date_default = today - relativedelta(days=30)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data de Início", value=start_date_default)
with col2:
    end_date = st.date_input("Data de Fim", value=today)

st.markdown("---")

# --- BOTÃO E EXIBIÇÃO DO RESULTADO ---
st.markdown("##### 2. Gere sua análise")

# Inicializa o estado da sessão para armazenar o insight
if 'insight_gerado' not in st.session_state:
    st.session_state.insight_gerado = None

if st.button("Analisar Período Selecionado", type="primary", use_container_width=True):
    if start_date > end_date:
        st.error("A data de início não pode ser posterior à data de fim.")
    else:
        with st.spinner("Analisando seus dados e consultando a IA... 🧠"):
            # Passa as datas selecionadas para a função da IA
            insight = insights_module.gerar_insights_financeiros(user_id, start_date, end_date)
            st.session_state.insight_gerado = insight

# Exibe o insight gerado se ele existir
if st.session_state.insight_gerado:
    st.markdown("---")
    st.subheader("Análise da IA:")
    st.info(st.session_state.insight_gerado)