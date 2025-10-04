import streamlit as st
import database
import pandas as pd
import datetime
import utils
import calendar

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# --- Conteúdo da Página ---
contas = database.get_contas(user_id)
categorias_receita = database.get_categorias(user_id, "receita")

st.title("Gerenciar Receitas")
if not contas:
    st.warning("Cadastre uma conta para adicionar receitas.")
if not categorias_receita:
    st.warning("Cadastre uma categoria de receita para continuar.")

contas_dict = {conta[1]: conta[0] for conta in contas}
categorias_list = [cat[1] for cat in categorias_receita]

with st.form("form_nova_receita"):
    st.markdown("### Adicionar Nova Receita")
    descricao = st.text_input("Descrição")
    valor = st.number_input("Valor (de cada ocorrência)", min_value=0.01, format="%.2f")
    data = st.date_input("Data da Primeira Ocorrência", value=utils.get_local_today())
    categoria_nome = st.selectbox("Categoria", options=categorias_list)
    conta_nome = st.selectbox("Conta", options=list(contas_dict.keys()))

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        recorrencia_freq = st.selectbox("Frequência da Recorrência", ["Única", "Diária", "Semanal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"])
    with col2:
        recorrencia_vezes = st.number_input("Repetir por (vezes)", min_value=1, step=1)

    if st.form_submit_button("Adicionar Receita"):
        if not descricao.strip():
            st.toast("Descrição é obrigatória.", icon="⚠️")
        else:
            conta_id = contas_dict[conta_nome]
            database.insert_receita(
                user_id, conta_id, data.isoformat(), valor, categoria_nome, descricao.strip(),
                recorrencia_freq if recorrencia_freq != 'Única' else None,
                recorrencia_vezes
            )
            st.toast("Receita adicionada com sucesso!", icon="✅")
            st.rerun()

st.markdown("---")
receitas = database.get_receitas(user_id)
if not receitas:
    st.info("Nenhuma receita cadastrada.")
else:
    df = pd.DataFrame(receitas, columns=["ID", "user_id", "conta_id", "Data", "Valor", "Categoria", "Descrição"])
    df["Data"] = pd.to_datetime(df["Data"])
    df["Conta"] = df["conta_id"].map({v: k for k, v in contas_dict.items()})
    df["Excluir"] = False

    # ==== FILTROS EM COLUNAS ====
    st.markdown("### Filtros das Receitas")

    meses = {i: calendar.month_name[i] for i in range(1, 13)}
    meses_keys = list(meses.keys())
    meses_keys.insert(0, "Todos")
    anos = sorted(df["Data"].dt.year.unique())
    ano_atual = datetime.datetime.now().year
    index_ano = anos.index(ano_atual) if ano_atual in anos else 0

    filtro_cols = st.columns(4)
    with filtro_cols[0]:
        mes_selecionado = st.selectbox(
            "Mês",
            options=meses_keys,
            format_func=lambda x: "Todos" if x == "Todos" else meses[x],
            key="mes_receita_filtro"
        )
    with filtro_cols[1]:
        ano_selecionado = st.selectbox("Ano", options=anos, index=index_ano, key="ano_receita_filtro")
    with filtro_cols[2]:
        categoria_filtro = st.selectbox("Categoria", options=["Todas"] + categorias_list, key="categoria_receita_filtro")
    with filtro_cols[3]:
        conta_filtro = st.selectbox("Conta", options=["Todas"] + list(contas_dict.keys()), key="conta_receita_filtro")

    # ==== FILTRAGEM ====
    df_filtrado = df.copy()
    if mes_selecionado != "Todos":
        df_filtrado = df_filtrado[
            (df_filtrado["Data"].dt.month == mes_selecionado) &
            (df_filtrado["Data"].dt.year == ano_selecionado)
        ]
    else:
        df_filtrado = df_filtrado[
            (df_filtrado["Data"].dt.year == ano_selecionado)
        ]
    if categoria_filtro != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Categoria"] == categoria_filtro]
    if conta_filtro != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Conta"] == conta_filtro]

    st.markdown("### Receitas Cadastradas (Filtradas)")
    edited_df = st.data_editor(
        df_filtrado,
        hide_index=True,
        use_container_width=True,
        column_config={
            "ID": None, "user_id": None, "conta_id": None,
            "Conta": st.column_config.SelectboxColumn(options=list(contas_dict.keys()), required=True),
            "Data": st.column_config.DateColumn(required=True),
            "Valor": st.column_config.NumberColumn(format="R$ %.2f", required=True),
            "Categoria": st.column_config.SelectboxColumn(options=categorias_list, required=True),
            "Descrição": st.column_config.TextColumn(required=True)
        },
        key="receitas_editor"
    )
    c1, c2 = st.columns(2)
    if c1.button("Salvar Alterações em Receitas"):
        for _, row in edited_df.iterrows():
            database.update_receita(int(row["ID"]), user_id, contas_dict[row["Conta"]], row["Data"].isoformat(), float(row["Valor"]), row["Categoria"], row["Descrição"])
        st.toast("Receitas atualizadas!", icon="✅")
        st.rerun()
    if c2.button("Excluir Receitas Selecionadas"):
        selected = edited_df[edited_df["Excluir"]]
        if not selected.empty:
            for _, row in selected.iterrows():
                database.delete_receita(int(row["ID"]), user_id)
            st.toast(f"{len(selected)} receita(s) excluída(s)!", icon="🗑️")
            st.rerun()
        else:
            st.toast("Nenhuma receita selecionada.", icon="⚠️")

