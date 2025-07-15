# pages/🤖_Assistente.py

import streamlit as st
import utils
import insights_module

# Guarda de Autenticação
profile, user_id, username, credentials, authenticator = utils.check_authentication()

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

st.markdown("---")
with st.expander("🕵️‍♂️ Depuração: Ver Última Query SQL Executada"):
    if "last_sql_query" in st.session_state:
        st.code(st.session_state.last_sql_query, language="sql")
    else:
        st.info("Nenhuma query foi executada nesta sessão ainda.")