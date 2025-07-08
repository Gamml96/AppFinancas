# app.py (ou Home.py) - Versão Final
import streamlit as st
import streamlit_authenticator as stauth
import database
import datetime
import pandas as pd
import utils

# --- Funções da Página Home (sem alterações) ---
def render_home_page(user_id):
    st.title("Visão Geral Financeira")
    # ... (cole aqui o conteúdo da sua função render_home_page, com os popovers de acesso rápido e os gráficos)
    # Exemplo do início:
    st.markdown("### Acesso Rápido")
    col1, col2 = st.columns(2)
    with col1:
        with st.popover("➕ Adicionar Receita", use_container_width=True):
            # ... formulário de receita ...
    with col2:
        with st.popover("➖ Adicionar Despesa", use_container_width=True):
            # ... formulário de despesa ...
    st.markdown("---")
    st.markdown("### Lançamentos Próximos")
    # ... etc ...

# --- LÓGICA PRINCIPAL DE AUTENTICAÇÃO (COM NOVO FLUXO) ---
def main():
    st.set_page_config("App Finanças", layout="wide", initial_sidebar_state="collapsed")
    
    # CSS para ocultar a sidebar INTEIRA se o usuário estiver deslogado
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

    # --- LÓGICA PARA USUÁRIO LOGADO ---
    if st.session_state.get("authentication_status"):
        with st.sidebar:
            st.subheader(f"Bem-vindo, {st.session_state['name']}!")
            authenticator.logout("Logout", "sidebar", key="logout_button")
        
        # Nova tentativa de ocultar a página de Admin para não-admins
        username = st.session_state['username']
        is_admin = database.is_user_admin(username)
        if not is_admin:
            # Este seletor tenta encontrar o link cuja URL termina com "Admin"
            # É uma abordagem mais resiliente que a anterior.
            hide_admin_page_css = """
                <style>
                    a[href$="Admin"] {
                        display: none;
                    }
                </style>
            """
            st.markdown(hide_admin_page_css, unsafe_allow_html=True)

        # Renderiza a página Home
        profile = database.get_user_profile(username)
        if profile:
            user_id = profile['user_id']
            render_home_page(user_id)
        else:
            st.error("Erro ao carregar perfil do usuário.")

    # --- NOVO FLUXO DE LOGIN / CADASTRO PARA USUÁRIO DESLOGADO ---
    else:
        # Inicializa o estado de "registro" se ele não existir
        if 'register_form' not in st.session_state:
            st.session_state.register_form = False

        # Se o estado for 'registro', mostra o formulário de cadastro
        if st.session_state.register_form:
            st.subheader("Crie sua nova conta")
            try:
                if authenticator.register_user('Criar conta', preauthorization=False):
                    st.success('Usuário criado com sucesso! Por favor, volte para fazer o login.')
                    st.session_state.register_form = False # Volta para a tela de login
                    st.rerun() 
            except Exception as e:
                st.error(e)
            
            if st.button("Voltar para Login"):
                st.session_state.register_form = False
                st.rerun()

        # Senão, mostra o formulário de login por padrão
        else:
            st.subheader("Acesse sua conta")
            authenticator.login(fields={'Form name': 'Login'})
            
            if st.session_state.get("authentication_status") is False:
                st.error("Usuário ou senha incorretos.")
            
            st.markdown("---")
            if st.button("Não tem uma conta? Crie uma aqui"):
                st.session_state.register_form = True
                st.rerun()

if __name__ == "__main__":
    # Garante que as funções do seu banco de dados estão disponíveis
    # Você não precisa mais do init_db() se estiver usando um BD na nuvem
    # database.init_db() 
    main()
