import streamlit as st
import database
import pandas as pd
import datetime
import utils
import bcrypt

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
except:
    st.info("Por favor, faça o login para acessar esta página.")
    st.stop()

# Guarda de Permissão (Etapa 2: verifica se é admin)
if not database.is_user_admin(username):
    st.error("Acesso negado. Esta página é restrita a administradores.")
    st.stop()

# --- Conteúdo da Página ---

st.title("Painel de Administração")
st.markdown("Gerencie os usuários do sistema.")

all_users = database.get_all_users()
if not all_users:
    st.info("Nenhum usuário encontrado além de você.")
    

df_users = pd.DataFrame(all_users, columns=["ID", "Usuário", "Nome", "Email", "É Admin"])

# --- INÍCIO DA NOVA SEÇÃO: RESET DE SENHA ---

st.markdown("---")
st.markdown("### Resetar Senha de Usuário")

# Cria um dicionário para mapear nome de usuário para ID
user_list = df_users['Usuário'].tolist()

with st.form("form_reset_password"):
    selected_user = st.selectbox("Selecione o usuário para resetar a senha:", user_list)
    new_password = st.text_input("Digite a NOVA senha temporária:", type="password")
    confirm_password = st.text_input("Confirme a NOVA senha temporária:", type="password")
    
    submitted = st.form_submit_button("Resetar Senha")

    if submitted:
        if not new_password or not confirm_password:
            st.warning("Por favor, preencha e confirme a nova senha.")
        elif new_password != confirm_password:
            st.error("As senhas não conferem.")
        elif selected_user:
            try:
                # Reutiliza a função de atualização de senha
                database.update_user_password(selected_user, new_password)
                st.success(f"A senha do usuário '{selected_user}' foi resetada com sucesso!")
            except Exception as e:
                st.error(f"Ocorreu um erro ao resetar a senha: {e}")
        else:
            st.error("Usuário selecionado inválido.")

# --- FIM DA NOVA SEÇÃO: RESET DE SENHA ---

st.markdown("---")
st.markdown("### Gerenciamento de Permissões e Exclusão")
df_users["Excluir"] = False

st.warning("Cuidado: as alterações feitas aqui são imediatas. Evite remover seu próprio status de administrador ou excluir sua própria conta para não perder o acesso.")

edited_df = st.data_editor(
    df_users,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ID": st.column_config.NumberColumn(disabled=True),
        "Usuário": st.column_config.TextColumn(disabled=True),
        "Nome": st.column_config.TextColumn(disabled=True),
        "Email": st.column_config.TextColumn(disabled=True),
        "É Admin": st.column_config.CheckboxColumn(default=False),
        "Excluir": st.column_config.CheckboxColumn("Excluir Usuário?", default=False)
    },
    key="admin_editor"
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Salvar Alterações de Status", type="primary"):
        for _, row in edited_df.iterrows():
            user_id_alvo = int(row["ID"])
            is_admin = bool(row["É Admin"])
            
            if user_id_alvo == user_id and not is_admin:
                st.error("Você não pode remover seu próprio status de administrador.")
                continue
            
            database.update_user_admin_status(user_id, is_admin)
        
        st.success("Status dos usuários atualizado com sucesso!")
        st.rerun()

with col2:
    if st.button("Excluir Usuários Selecionados"):
        selected_to_delete = edited_df[edited_df["Excluir"]]
        
        if not selected_to_delete.empty:
            for _, row in selected_to_delete.iterrows():
                user_id_alvo = int(row["ID"])
                username_alvo = row["Usuário"]
                
                if user_id_alvo == user_id:
                    st.error("Você não pode excluir sua própria conta a partir deste painel.")
                    continue
                
                database.delete_all_user_data(user_id_alvo, username_alvo)
            
            st.success("Usuários selecionados foram excluídos permanentemente!")
            st.rerun()
        else:
            st.info("Nenhum usuário selecionado para exclusão.")

# --- INÍCIO DA NOVA SEÇÃO: ADICIONAR NOVO USUÁRIO ---
st.markdown("---")
st.markdown("### Adicionar Novo Usuário")

with st.form("form_add_user"):
    st.write("Preencha os dados para criar um novo usuário.")
    
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Nome de usuário (para login)")
        new_name = st.text_input("Nome completo")
        new_email = st.text_input("Email")
    with col2:
        new_password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar Senha", type="password")
        is_admin = st.checkbox("Este usuário será administrador?")

    submitted = st.form_submit_button("Adicionar Usuário")

    if submitted:
        if not all([new_username, new_name, new_password, confirm_password]):
            st.warning("Por favor, preencha todos os campos.")
        elif new_password != confirm_password:
            st.error("As senhas não conferem.")
        else:
            try:
                # Criptografa a senha antes de enviar para o banco de dados
                password_bytes = new_password.encode('utf-8')
                hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
                hashed_password_str = hashed_bytes.decode('utf-8')

                # Reutiliza a função add_user que já existe
                database.add_user(
                    username=new_username,
                    name=new_name,
                    email=new_email,
                    hashed_password=hashed_password_str,
                    is_admin=is_admin
                )
                st.success(f"Usuário '{new_username}' criado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Ocorreu um erro ao criar o usuário: {e}")

# --- FIM DA NOVA SEÇÃO ---
