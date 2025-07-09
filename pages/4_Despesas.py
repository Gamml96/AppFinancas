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
contas = database.get_contas(user_id)
categorias_despesa = database.get_categorias(user_id, "despesa")

st.title("Gerenciar Despesas")
if not contas: st.warning("Cadastre uma conta para adicionar despesas."); 
if not categorias_despesa: st.warning("Cadastre uma categoria de despesa para continuar."); 

contas_dict = {conta[1]: conta[0] for conta in contas}
categorias_list = [cat[1] for cat in categorias_despesa]

with st.form("form_nova_despesa"):
    st.markdown("### Adicionar Nova Despesa")
    descricao = st.text_input("Descrição da Despesa")
    valor = st.number_input("Valor Total", min_value=0.01, format="%.2f")
    data_compra = st.date_input("Data da Compra", value=utils.get_local_today())
    categoria = st.selectbox("Categoria", options=categorias_list)
    conta_nome = st.selectbox("Conta", options=list(contas_dict.keys()))
    tipo_pagamento = st.radio("Tipo de Pagamento", ["crédito", "débito"], horizontal=True)
    parcelas = st.number_input("Nº de Parcelas", min_value=1, step=1)

    if st.form_submit_button("Adicionar Despesa"):
        if not descricao.strip():
            st.toast("A descrição é obrigatória.", icon="⚠️")
        else:
            database.insert_despesa(user_id, contas_dict[conta_nome], data_compra.isoformat(), valor, categoria, tipo_pagamento, parcelas, descricao.strip())
            st.toast(f"Despesa '{descricao}' adicionada!", icon="✅"); st.rerun()

st.markdown("---")
despesas = database.get_despesas(user_id)
if not despesas: st.info("Nenhuma despesa cadastrada."); 

df = pd.DataFrame(despesas, columns=["ID", "user_id", "conta_id", "Data Compra", "Data Vencimento", "Valor", "Categoria", "Tipo", "Parcela", "Descrição", "Recorrência", "Grupo ID"])
df["Data Compra"] = pd.to_datetime(df["Data Compra"]).dt.date
df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"]).dt.date
df["Conta"] = df["conta_id"].map({v: k for k, v in contas_dict.items()})
df["Excluir"] = False

st.markdown("### Despesas Lançadas")
st.warning("A edição na tabela afeta apenas a parcela individual. Para alterar a compra inteira, exclua as parcelas e adicione-a novamente.", icon="⚠️")
edited_df = st.data_editor(df, hide_index=True, use_container_width=True,
    column_config={
        "ID": None, "user_id": None, "conta_id": None, "Parcela": None, "Recorrência": None, "Grupo ID": None,
        "Descrição": st.column_config.TextColumn(required=True),
        "Tipo": st.column_config.SelectboxColumn(options=["crédito", "débito"], required=True),
        "Valor": st.column_config.NumberColumn(format="R$ %.2f", required=True),
        "Conta": st.column_config.SelectboxColumn(options=list(contas_dict.keys()), required=True),
        "Categoria": st.column_config.SelectboxColumn(options=categorias_list, required=True),
        "Data Compra": st.column_config.DateColumn(required=True),
        "Data Vencimento": st.column_config.DateColumn(required=True)
    }, key="despesas_editor")

c1, c2 = st.columns(2)
if c1.button("Salvar Alterações em Despesas"):
    for _, row in edited_df.iterrows():
        database.update_despesa(int(row["ID"]), user_id, contas_dict[row["Conta"]], row["Data Compra"].isoformat(), row["Data Vencimento"].isoformat(), float(row["Valor"]), row["Categoria"], row["Descrição"])
    st.toast("Despesas atualizadas!", icon="✅"); st.rerun()

if c2.button("Excluir Despesas Selecionadas"):
    selected = edited_df[edited_df["Excluir"]]
    if not selected.empty:
        for _, row in selected.iterrows(): database.delete_despesa(int(row["ID"]), user_id)
        st.toast(f"{len(selected)} despesa(s) excluída(s)!", icon="🗑️"); st.rerun()
    else:
        st.toast("Nenhuma despesa selecionada.", icon="⚠️")
