# pages/🤖_Assistente.py

import streamlit as st
import utils
import insights_module
import datetime
from dateutil.relativedelta import relativedelta

# Guarda de Autenticação
profile, user_id, username, credentials, authenticator = utils.check_authentication()

tab_assistente, tab_insights = st.tabs(["Assistente", "Insights"])

with tab_assistente:
    
    st.title("🤖 Assistente Financeiro Pessoal")
    st.info("Faça uma pergunta em linguagem natural sobre suas finanças.")
    
    # Inicializa o histórico do chat na sessão se não existir
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Exibe as mensagens do histórico
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Captura a nova pergunta do usuário
    if prompt := st.chat_input("Ex: Quanto gastei com gasolina este mês?"):
        # Adiciona a pergunta do usuário ao histórico e à tela
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
    
        # Mostra uma mensagem de "pensando"
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                # Chama a nossa nova função RAG para obter a resposta
                response = insights_module.responder_pergunta_do_usuario(user_id, prompt)
                st.markdown(response)
        
        # Adiciona a resposta da IA ao histórico
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # st.markdown("---")
    # with st.expander("🕵️‍♂️ Depuração: Ver Última Query SQL Executada"):
    #     if "last_sql_query" in st.session_state:
    #         st.code(st.session_state.last_sql_query, language="sql")
    #     else:
    #         st.info("Nenhuma query foi executada nesta sessão ainda.")

with tab_insights:
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
        st.text(st.session_state.insight_gerado)
