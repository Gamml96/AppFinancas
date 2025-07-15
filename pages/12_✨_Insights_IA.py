# pages/✨_Insights_IA.py

import streamlit as st
import utils
import insights_module # Nosso novo módulo de IA

# Guarda de Autenticação
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("✨ Insights com Inteligência Artificial")
st.write("Receba uma análise rápida e personalizada sobre sua saúde financeira nos últimos 30 dias, gerada pela IA do Google.")

# Inicializa o estado da sessão para armazenar o insight
if 'insight_gerado' not in st.session_state:
    st.session_state.insight_gerado = None

if st.button("Gerar Análise Financeira", type="primary", use_container_width=True):
    # Mostra um spinner enquanto a IA processa a informação
    with st.spinner("Analisando seus dados e consultando a IA... 🧠"):
        # Chama a função principal do nosso módulo de insights
        insight = insights_module.gerar_insights_financeiros(user_id)
        st.session_state.insight_gerado = insight

# Exibe o insight gerado se ele existir
if st.session_state.insight_gerado:
    st.markdown("---")
    st.subheader("Análise da IA:")
    st.info(st.session_state.insight_gerado)