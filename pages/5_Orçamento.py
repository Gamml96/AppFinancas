# pages/11_Orcamento.py
import streamlit as st
import database
import pandas as pd
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
try:
    profile, user_id, username = utils.check_authentication()
except Exception:
    st.info("Por favor, faça o login para acessar esta página.")
    st.stop()

st.title("Definir Orçamento Mensal")
st.info("Defina um limite de gastos para suas categorias de despesa. Deixe em 0 para não ter um limite.")

# 1. Busca todas as categorias de DESPESA do usuário
categorias_despesa = database.get_categorias(user_id, "despesa")
# 2. Busca os orçamentos JÁ definidos pelo usuário
orcamentos_definidos = database.get_orcamentos(user_id)

if not categorias_despesa:
    st.warning("Você precisa cadastrar categorias de despesa antes de poder definir um orçamento.")
else:
    orcamentos_dict = {orc[0]: orc[1] for orc in orcamentos_definidos}
    dados_editor = []
    for cat_id, cat_nome in categorias_despesa:
        limite_atual = orcamentos_dict.get(cat_nome, 0.0)
        dados_editor.append({"Categoria": cat_nome, "Limite Mensal": limite_atual})
    
    df_orcamento = pd.DataFrame(dados_editor)

    st.markdown("### Orçamento por Categoria")
    
    # O data_editor usa a chave "editor_orcamento" para guardar seu estado
    edited_df = st.data_editor(
        df_orcamento,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Categoria": st.column_config.TextColumn("Categoria", disabled=True),
            "Limite Mensal": st.column_config.NumberColumn("Limite (R$)", format="R$ %.2f", min_value=0.0, step=100.0)
        },
        key="editor_orcamento" # Esta chave é como acessamos o estado
    )

    # --- INÍCIO DA CORREÇÃO ---
    if st.button("Salvar Orçamentos", type="primary"):
        # Acessa os dados editados DIRETAMENTE do estado da sessão do editor
        if "editor_orcamento" in st.session_state:
            dados_para_salvar = st.session_state["editor_orcamento"]
            
            # Converte a lista de dicionários de volta para um DataFrame
            df_para_salvar = pd.DataFrame(dados_para_salvar)
            
            # Itera sobre o DataFrame com os dados corretos e editados
            for _, row in df_para_salvar.iterrows():
                database.set_orcamento(user_id, row["Categoria"], row["Limite Mensal"])
            
            st.success("Orçamentos salvos com sucesso!")
            # st.rerun() # O rerun é automático ao sair do if do botão, mas pode deixar para garantir
        else:
            st.warning("Nenhuma alteração para salvar.")
    # --- FIM DA CORREÇÃO ---