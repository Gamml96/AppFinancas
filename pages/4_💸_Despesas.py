import streamlit as st
import database
import pandas as pd
import datetime
import utils
import ai_module

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

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
        # --- PONTO CENTRAL DA INTELIGÊNCIA ARTIFICIAL ---
    # 1. Tenta prever a categoria com base no que foi digitado na descrição.
    sugestao_categoria = None
    if descricao:  # A previsão só acontece se o campo "Descrição" não estiver vazio.
        # Chama a função do ai_module que carrega o modelo global e faz a previsão.
        sugestao_categoria = ai_module.prever_categoria(descricao)

    # 2. Prepara o selectbox para usar a sugestão da IA.
    index_sugestao = 0  # O padrão é a primeira categoria da lista.
    # Se a IA retornou uma sugestão válida e essa sugestão existe na lista de categorias do usuário...
    if sugestao_categoria and sugestao_categoria in categorias_list:
        # ...encontramos o índice dessa categoria para pré-selecioná-la.
        index_sugestao = categorias_list.index(sugestao_categoria)
    # --- FIM DA LÓGICA DE IA ---
    valor = st.number_input("Valor", min_value=0.01, format="%.2f", help="Para parcelas, insira o valor total da compra. Para recorrências, insira o valor de cada ocorrência.")
    data_compra = st.date_input("Data da Primeira Ocorrência/Compra", value=utils.get_local_today())
    categoria = st.selectbox("Categoria", options=categorias_list)
    conta_nome = st.selectbox("Conta", options=list(contas_dict.keys()))

    st.markdown("---")
    st.markdown("#### Detalhes de Pagamento e Repetição")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_pagamento = st.radio("Tipo de Pagamento", ["Crédito", "Débito"], horizontal=True, key="tipo_pagamento")
        # Ajustamos o help para maior clareza
        parcelas_input = st.number_input("Nº de Parcelas", min_value=1, step=1, help="Para compras parceladas. Para assinaturas, use a Recorrência ao lado.")
    
    with col2:
        recorrencia_freq_input = st.selectbox("Frequência da Recorrência", ["Única", "Diária", "Semanal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"], key="recorrencia_freq")
        recorrencia_vezes_input = st.number_input("Repetir por (vezes)", min_value=1, step=1, help="Deixe 1 para um lançamento único.")

    if st.form_submit_button("Adicionar Despesa"):
        if not descricao.strip() or valor <= 0:
            st.warning("Descrição é obrigatória e o valor deve ser positivo.")
        else:
            # --- LÓGICA DE SANITIZAÇÃO DE ENTRADA ---
            # Por padrão, consideramos um lançamento único.
            parcelas_final = parcelas_input
            recorrencia_freq_final = None
            recorrencia_vezes_final = 1

            # DECISÃO: Se o usuário escolheu uma recorrência, ela tem prioridade.
            if recorrencia_freq_input != "Única" and recorrencia_vezes_input > 1:
                # Estamos no modo RECORRÊNCIA
                recorrencia_freq_final = recorrencia_freq_input
                recorrencia_vezes_final = recorrencia_vezes_input
                # Forçamos as parcelas para 1 para evitar conflito na lógica do backend.
                parcelas_final = 1
            
            # Se não for uma recorrência, usamos o valor das parcelas.
            # O valor de recorrencia_freq_final já é None.
            
            # Chamada para o banco de dados com os dados JÁ LIMPOS E VALIDADOS.
            try:
                database.insert_despesa(
                    user_id=user_id,
                    conta_id=contas_dict[conta_nome],
                    data_compra_str=data_compra.isoformat(),
                    valor=valor,
                    categoria=categoria,
                    tipo_pagamento=tipo_pagamento,
                    parcelas=parcelas_final,
                    descricao=descricao.strip(),
                    recorrencia_freq=recorrencia_freq_final,
                    recorrencia_vezes=recorrencia_vezes_final
                )
                st.toast(f"Despesa '{descricao}' adicionada com sucesso!", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Ocorreu um erro ao salvar a despesa: {e}")


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
        "Tipo": st.column_config.SelectboxColumn(options=["Crédito", "Débito"], required=True),
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
