# app.py (versão corrigida para ser a sua Home)
import streamlit as st
import streamlit_authenticator as stauth
import database
import datetime
import pandas as pd
import utils # Certifique-se que o utils.py está na mesma pasta
import plotly.express as px
from dateutil.relativedelta import relativedelta


def main():
    st.set_page_config("App Finanças", layout="wide", initial_sidebar_state= 'expanded',page_icon="🪙")
    
    # CSS para ocultar a sidebar se o usuário estiver deslogado
    hide_sidebar_nav_css = """
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """
    if not st.session_state.get("authentication_status"):
        st.markdown(hide_sidebar_nav_css, unsafe_allow_html=True)

    # 1. Configuração da página (com o ícone)
    st.set_page_config(
        page_title="App Finanças",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="auto" # 'auto' é melhor para a experiência de login
    )

    # 2. Lógica de Autenticação
    credentials = database.get_authenticator_credentials()
    authenticator = stauth.Authenticate(
        credentials, 
        cookie_name="app_fin_cookie",
        key="app_fin_key", 
        cookie_expiry_days=30
    )

    # Verifica se o usuário está logado
    if st.session_state.get("authentication_status"):
        # Se logado, mostra a saudação na barra lateral e o botão de logout
        with st.sidebar:
            # st.subheader(f"Bem-vindo, {st.session_state['name']}!")
            # st.markdown("---")
            authenticator.logout("Logout", "sidebar", key="logout_button")
        
        # Mensagem de boas-vindas na página principal
        # O Streamlit automaticamente redirecionará para a primeira página da pasta 'pages'
        st.title(f"Bem-vindo, {st.session_state['name']}! 👋")
        st.info("👈 Selecione uma opção na barra lateral para começar.")

    else:
        # Se não estiver logado, mostra a tela de login
        st.subheader("Acesse sua conta")
        authenticator.login(fields={'Form name': 'Login'})
        
        if st.session_state.get("authentication_status") is False:
            st.error("Usuário ou senha incorretos.")
        elif st.session_state.get("authentication_status") is None:
            st.warning("Por favor, insira seu usuário e senha.")

if __name__ == "__main__":
    main()
