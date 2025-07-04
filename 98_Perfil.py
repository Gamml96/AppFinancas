import streamlit as st
import database
import pandas as pd
import datetime
import utils
# --- Guarda de Autenticação ---
profile, user_id, username = utils.check_authentication()

# ---- FUNÇÕES ----
def change_user_password(username):
    st.subheader("Trocar senha")
    with st.form("form_trocar_senha"):
        new_pass = st.text_input("Nova senha", type="password")
        confirm_pass = st.text_input("Confirmar nova senha", type="password")
        if st.form_submit_button("Atualizar senha"):
            if not new_pass or not confirm_pass:
                st.toast("Preencha ambos os campos.", icon="⚠️")
            elif new_pass != confirm_pass:
                st.toast("As senhas não conferem.", icon="❌")
            else:
                database.update_user_password(username, new_pass)
                st.toast("Senha atualizada com sucesso!", icon="✅")


# --- Conteúdo da Página ---

st.title("Meu Perfil")

with st.form("form_perfil"):
    new_name = st.text_input("Nome", value=profile["name"] or "")
    new_email = st.text_input("Email", value=profile["email"] or "")
    if st.form_submit_button("Salvar Alterações no Perfil"):
        if not new_name.strip():
            st.toast("O campo Nome não pode ser vazio.", icon="⚠️")
        else:
            database.update_user_profile(username, new_name.strip(), new_email.strip())
            st.toast("Perfil atualizado com sucesso!", icon="✅")
            st.rerun()

st.markdown("---")
change_user_password(username)

st.markdown("---")

st.markdown("### Apagar Dados Financeiros")

with st.expander("Resetar todos os dados"):
    # Texto alterado para refletir que a conta não será excluída
    st.error("Atenção: Esta ação é irreversível. Todos os seus dados financeiros (contas, categorias, receitas e despesas) serão permanentemente apagados. Sua conta de usuário e senha serão mantidas.")
    
    if st.button("Eu entendo, desejo resetar meus dados", type="primary"):
        st.session_state['confirm_reset_step'] = True

    if st.session_state.get('confirm_reset_step'):
        with st.form("form_reset_account"):
            st.warning(f"Para confirmar o reset de todos os seus dados, por favor, digite seu nome de usuário **'{username}'** no campo abaixo.")
            
            confirmation_text = st.text_input("Digite seu nome de usuário para confirmar:")
            
            submitted = st.form_submit_button("Confirmar Reset Permanente dos Dados")

            if submitted:
                if confirmation_text == username:
                    with st.spinner("Excluindo seus dados financeiros..."):
                        # Chama a nova função que NÃO exclui o usuário
                        database.delete_user_financial_data(user_id)
                        
                        # --- LÓGICA DE LOGOUT REMOVIDA ---
                        # O usuário permanecerá logado.
                        st.session_state['confirm_reset_step'] = False # Reseta o estado
                        
                        # Mensagem de sucesso alterada
                        st.success("Todos os seus dados financeiros foram excluídos com sucesso. Seu perfil foi mantido.")
                        st.rerun()
                else:
                    st.error("O nome de usuário digitado está incorreto. O reset foi cancelado.")
                    st.session_state['confirm_reset_step'] = False
                    st.rerun()

# --- Conteúdo da Página ---

