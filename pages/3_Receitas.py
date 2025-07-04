import streamlit as st
import database
import pandas as pd
import datetime
import utils
# --- Guarda de Autenticação ---
profile, user_id, username = utils.check_authentication()

# --- Conteúdo da Página ---
contas = database.get_contas(user_id)
categorias_receita = database.get_categorias(user_id, "receita")

st.title("Gerenciar Receitas")
if not contas: st.warning("Cadastre uma conta para adicionar receitas."); 
if not categorias_receita: st.warning("Cadastre uma categoria de receita para continuar."); 

contas_dict = {conta[1]: conta[0] for conta in contas}
categorias_list = [cat[1] for cat in categorias_receita]

with st.form("form_nova_receita"):
    st.markdown("### Adicionar Nova Receita")
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor", min_value=0.01, format="%.2f")
    data = st.date_input("Data", value=datetime.date.today())
    conta_nome = st.selectbox("Conta", options=list(contas_dict.keys()))
    categoria_nome = st.selectbox("Categoria", options=categorias_list)
    
    if st.form_submit_button("Adicionar Receita"):
        if not descricao.strip():
            st.toast("Descrição é obrigatória.", icon="⚠️")
        else:
            conta_id = contas_dict[conta_nome]
            database.insert_receita(user_id, conta_id, data.isoformat(), valor, categoria_nome, descricao.strip())
            st.toast("Receita adicionada com sucesso!", icon="✅")
            st.rerun()

st.markdown("---")
receitas = database.get_receitas(user_id)
if not receitas: st.info("Nenhuma receita cadastrada."); 

df = pd.DataFrame(receitas, columns=["ID", "user_id", "conta_id", "Data", "Valor", "Categoria", "Descrição"])
df["Data"] = pd.to_datetime(df["Data"]).dt.date
df["Conta"] = df["conta_id"].map({v: k for k, v in contas_dict.items()})
df["Excluir"] = False

st.markdown("### Receitas Cadastradas")
edited_df = st.data_editor(df, hide_index=True, use_container_width=True,
    column_config={
        "ID": None, "user_id": None, "conta_id": None,
        "Conta": st.column_config.SelectboxColumn(options=list(contas_dict.keys()), required=True),
        "Data": st.column_config.DateColumn(required=True),
        "Valor": st.column_config.NumberColumn(format="R$ %.2f", required=True),
        "Categoria": st.column_config.SelectboxColumn(options=categorias_list, required=True),
        "Descrição": st.column_config.TextColumn(required=True)
    }, key="receitas_editor")

c1, c2 = st.columns(2)
if c1.button("Salvar Alterações em Receitas"):
    for _, row in edited_df.iterrows():
        database.update_receita(int(row["ID"]), user_id, contas_dict[row["Conta"]], row["Data"].isoformat(), float(row["Valor"]), row["Categoria"], row["Descrição"])
    st.toast("Receitas atualizadas!", icon="✅"); st.rerun()

if c2.button("Excluir Receitas Selecionadas"):
    selected = edited_df[edited_df["Excluir"]]
    if not selected.empty:
        for _, row in selected.iterrows(): database.delete_receita(int(row["ID"]), user_id)
        st.toast(f"{len(selected)} receita(s) excluída(s)!", icon="🗑️"); st.rerun()
    else:
        st.toast("Nenhuma receita selecionada.", icon="⚠️")