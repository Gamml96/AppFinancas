import streamlit as st
import database
import pandas as pd
import datetime
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
st.title("Gerenciar Contas")
with st.form("form_nova_conta"):
    st.markdown("### Adicionar Nova Conta")
    nome = st.text_input("Nome da Conta")
    data_inicial = st.date_input("Data Inicial", value=datetime.date.today())
    saldo_inicial = st.number_input("Saldo Inicial", value=0.0, format="%.2f")
    vencimento = st.number_input("Dia do Vencimento da Fatura", min_value=1, max_value=31, value=1)
    fechamento = st.number_input("Dias antes do vencimento para fechar a fatura", min_value=1, max_value=31, value=10)
    
    if st.form_submit_button("Adicionar Conta"):
        if not nome.strip():
            st.toast("O nome da conta é obrigatório.", icon="⚠️")
        else:
            database.insert_conta(user_id, nome.strip(), vencimento, data_inicial.isoformat(), saldo_inicial, fechamento)
            st.toast(f"Conta '{nome}' adicionada com sucesso!", icon="✅")
            st.rerun()

st.markdown("---")
contas = database.get_contas(user_id)
if not contas:
    st.info("Nenhuma conta cadastrada.")


df_contas = pd.DataFrame(contas, columns=["ID", "Nome", "Vencimento", "Data Inicial", "Saldo Inicial", "Fechamento"])
df_contas["Data Inicial"] = pd.to_datetime(df_contas["Data Inicial"]).dt.date
df_contas["Saldo Inicial"] = pd.to_numeric(df_contas["Saldo Inicial"]).fillna(0.0)
df_contas["Excluir"] = False

st.markdown("### Contas Cadastradas")
search_term = st.text_input("Buscar contas por nome", key="search_contas")
if search_term:
    df_contas = df_contas[df_contas["Nome"].str.contains(search_term, case=False, na=False)]

edited_df = st.data_editor(df_contas, use_container_width=True, hide_index=True,
    column_config={
        "ID": None, "Nome": st.column_config.TextColumn(required=True),
        "Vencimento": st.column_config.NumberColumn(min_value=1, max_value=31, required=True),
        "Data Inicial": st.column_config.DateColumn(required=True),
        "Saldo Inicial": st.column_config.NumberColumn(format="R$ %.2f", required=True),
        "Fechamento": st.column_config.NumberColumn(min_value=1, max_value=31, required=True),
        "Excluir": st.column_config.CheckboxColumn(default=False)
    }, key="contas_editor")

col1, col2 = st.columns(2)
if col1.button("Salvar Alterações", key="save_contas"):
    for _, row in edited_df.iterrows():
        database.update_conta(int(row["ID"]), user_id, row["Nome"], int(row["Vencimento"]), row["Data Inicial"].isoformat(), float(row["Saldo Inicial"]), int(row["Fechamento"]))
    st.toast("Contas atualizadas com sucesso!", icon="✅")
    st.rerun()

if col2.button("Excluir Selecionados", key="delete_contas"):
    selected = edited_df[edited_df["Excluir"]]
    if not selected.empty:
        for _, row in selected.iterrows():
            database.delete_conta(int(row["ID"]), user_id)
        st.toast(f"{len(selected)} conta(s) excluída(s) com sucesso!", icon="🗑️")
        st.rerun()
    else:
        st.toast("Nenhuma conta selecionada para exclusão.", icon="⚠️")

