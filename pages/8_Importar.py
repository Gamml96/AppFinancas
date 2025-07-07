import streamlit as st
import database
import pandas as pd
import datetime
import utils
# --- Guarda de Autenticação ---
profile, user_id, username = utils.check_authentication()



# FUNÇÕES
@st.cache_data
def gerar_template_csv_despesas():
    """Cria um DataFrame de exemplo e o converte para CSV para download."""
    template_data = {
        'data_compra': ['2025-07-03'],
        'descricao': ['Café na padaria'],
        'valor_total': ['25.50'],
        'conta': ['Carteira'],
        'categoria': ['Alimentação'],
        'tipo_pagamento': ['débito'],
        'parcelas': [1]
    }
    df_template = pd.DataFrame(template_data)
    # Usamos ';' como separador, comum no Brasil para CSVs abertos no Excel
    return df_template.to_csv(index=False, sep=';').encode('utf-8')

@st.cache_data
def gerar_template_csv_receitas():
    """Cria um DataFrame de exemplo para receitas e o converte para CSV."""
    template_data = {
        'data': ['2025-07-04'],
        'descricao': ['Salário do Mês'],
        'valor': ['5000.00'],
        'conta': ['Conta Corrente'],
        'categoria': ['Salário']
    }
    df_template = pd.DataFrame(template_data)
    return df_template.to_csv(index=False, sep=';').encode('utf-8')

@st.cache_data
def gerar_template_csv_investimentos():
    """Cria um DataFrame de exemplo para transações de investimento, agora com tipo_ativo."""
    template_data = {
        'data': ['2025-01-15', '2025-02-20', '2025-03-10', '2025-04-05'],
        'codigo_ativo': ['PETR4', 'BTC-USD', 'AAPL', 'MXRF11'],
        'tipo_transacao': ['compra', 'venda', 'venda', 'compra'],
        'quantidade': [100, 1.1,200,100],
        'preco_unitario': [35.50, 350000, 150, 10],
        'tipo_ativo': ['Ação BR', 'Criptomoeda', 'Ação EUA', 'FII'] 
    }
    df_template = pd.DataFrame(template_data)
    return df_template.to_csv(index=False, sep=';').encode('utf-8')


# --- FUNÇÕES DE PROCESSAMENTO OTIMIZADAS ---

def processar_importacao_receitas(df, user_id, contas):
    contas_dict = {conta[1].lower(): conta[0] for conta in contas}
    dados_para_inserir = []
    erros = []
    for index, row in df.iterrows():
        try:
            descricao = str(row['descricao'])
            valor = float(str(row['valor']).replace(",", "."))
            data = pd.to_datetime(row['data'], dayfirst=True).date()
            conta_nome = str(row['conta']).lower()
            categoria_nome = str(row['categoria'])
            if conta_nome not in contas_dict: raise ValueError(f"Conta '{row['conta']}' não encontrada.")
            categoria_final = database.get_or_create_categoria_receita(user_id, categoria_nome)
            dados_para_inserir.append((contas_dict[conta_nome], data.isoformat(), valor, categoria_final, descricao))
        except Exception as e:
            erros.append(f"Linha {index + 2}: {row.get('descricao', 'N/A')} - Erro: {e}")
    
    if dados_para_inserir:
        database.batch_insert_receitas(user_id, dados_para_inserir)
        st.success(f"{len(dados_para_inserir)} receitas importadas com sucesso!")
    if erros:
        st.error(f"{len(erros)} linhas não puderam ser importadas:")
        with st.expander("Ver detalhes dos erros"): [st.write(erro) for erro in erros]

def processar_importacao_despesas(df, user_id, contas):
    contas_dict = {conta[1].lower(): conta[0] for conta in contas}
    dados_para_inserir = []
    erros = []
    for index, row in df.iterrows():
        try:
            descricao_base = str(row['descricao'])
            valor = float(str(row['valor_total']).replace(",", "."))
            data_compra = pd.to_datetime(row['data_compra'], dayfirst=True).date()
            conta_nome = str(row['conta']).lower()
            categoria_nome = str(row['categoria'])
            tipo_pagamento = str(row['tipo_pagamento']).lower()
            parcelas = int(row['parcelas'])

            if conta_nome not in contas_dict: raise ValueError(f"Conta '{row['conta']}' não encontrada.")
            if tipo_pagamento not in ['crédito', 'débito']: raise ValueError("Tipo de pagamento inválido.")
            
            conta_id = contas_dict[conta_nome]
            categoria_final = database.get_or_create_categoria_despesa(user_id, categoria_nome)
            
            # Lógica de cálculo de parcelas (movida para cá)
            valor_parcela_padrao = round(valor / parcelas, 2)
            diferenca = round(valor - (valor_parcela_padrao * parcelas), 2)
            valor_primeira_parcela = valor_parcela_padrao + diferenca
            grupo_id = int(datetime.datetime.now().timestamp() * 1000) + index

            if tipo_pagamento == 'crédito':
                conta_info = next((c for c in contas if c[0] == conta_id), None)
                primeiro_vencimento = utils._calcular_vencimento_credito(data_compra, conta_info[2], conta_info[5])
            else:
                primeiro_vencimento = data_compra

            for i in range(parcelas):
                valor_a_inserir = valor_primeira_parcela if i == 0 else valor_parcela_padrao
                vencimento_parcela = primeiro_vencimento + relativedelta(months=i)
                descricao_parcela = f"{descricao_base} ({i+1}/{parcelas})" if parcelas > 1 else descricao_base
                dados_para_inserir.append((conta_id, data_compra.isoformat(), vencimento_parcela.isoformat(), valor_a_inserir, categoria_final, tipo_pagamento, i + 1, descricao_parcela, grupo_id))

        except Exception as e:
            erros.append(f"Linha {index + 2}: {row.get('descricao', 'N/A')} - Erro: {e}")

    if dados_para_inserir:
        database.batch_insert_despesas(user_id, dados_para_inserir)
        st.success(f"{len(dados_para_inserir)} parcelas de despesas importadas com sucesso!")
    if erros:
        st.error(f"{len(erros)} linhas não puderam ser importadas:")
        with st.expander("Ver detalhes dos erros"): [st.write(erro) for erro in erros]

def processar_importacao_investimentos(df, user_id):
    dados_para_inserir = []
    erros = []
    for index, row in df.iterrows():
        try:
            codigo_ativo = str(row['codigo_ativo'])
            tipo_transacao = str(row['tipo_transacao']).lower()
            data = pd.to_datetime(row['data'], dayfirst=True).date()
            quantidade = float(row['quantidade'])
            preco_unitario = float(str(row['preco_unitario']).replace(",", "."))
            tipo_ativo = str(row['tipo_ativo'])
            if tipo_transacao not in ['compra', 'venda']: raise ValueError("Tipo de transação inválido.")
            investimento_id = database.get_or_create_investimento(user_id, codigo_ativo, tipo_ativo)
            dados_para_inserir.append((investimento_id, tipo_transacao, data.isoformat(), quantidade, preco_unitario))
        except Exception as e:
            erros.append(f"Linha {index + 2}: {row.get('codigo_ativo', 'N/A')} - Erro: {e}")

    if dados_para_inserir:
        database.batch_insert_transacoes_investimento(dados_para_inserir)
        st.success(f"{len(dados_para_inserir)} transações de investimento importadas com sucesso!")
    if erros:
        st.error(f"{len(erros)} linhas não puderam ser importadas:")
        with st.expander("Ver detalhes dos erros"): [st.write(erro) for erro in erros]

# --- Conteúdo da Página ---
contas = database.get_contas(user_id)
st.title("Importar Transações")

tab_despesas, tab_receitas, tab_investimentos = st.tabs(["Importar Despesas", "Importar Receitas", "Importar Investimentos"])

with tab_despesas:
    st.markdown("### 1. Baixe e Preencha o Template de Despesas")
    st.info("Use este modelo para importar suas despesas. **Os nomes das colunas não devem ser alterados.**")
    st.download_button(
        label="Baixar Template de Despesas",
        data=gerar_template_csv_despesas(),
        file_name="template_despesas.csv",
        mime="text/csv",
    )
    st.markdown("---")
    st.markdown("### 2. Faça o Upload do Arquivo Preenchido")
    uploaded_file_despesas = st.file_uploader("Escolha um arquivo CSV de despesas", type="csv", key="uploader_despesas")
    if uploaded_file_despesas is not None:
        try:
            df_upload = pd.read_csv(uploaded_file_despesas, sep=';')
            st.success("Arquivo de despesas carregado:")
            st.dataframe(df_upload.head())
            if st.button("Confirmar e Iniciar Importação de Despesas", type="primary"):
                processar_importacao_despesas(df_upload, user_id, contas)
                # st.rerun() foi REMOVIDO
        except Exception as e:
            st.error(f"Erro ao ler o arquivo de despesas: {e}.")

with tab_receitas:
    st.markdown("### 1. Baixe e Preencha o Template de Receitas")
    st.info("Use este modelo para importar suas receitas. **Os nomes das colunas não devem ser alterados.**")
    st.download_button(
        label="Baixar Template de Receitas",
        data=gerar_template_csv_receitas(),
        file_name="template_receitas.csv",
        mime="text/csv",
    )
    st.markdown("---")
    st.markdown("### 2. Faça o Upload do Arquivo Preenchido")
    uploaded_file_receitas = st.file_uploader("Escolha um arquivo CSV de receitas", type="csv", key="uploader_receitas")
    if uploaded_file_receitas is not None:
        try:
            df_upload = pd.read_csv(uploaded_file_receitas, sep=';')
            st.success("Arquivo de receitas carregado. Veja uma prévia:")
            st.dataframe(df_upload.head())
            if st.button("Confirmar e Iniciar Importação de Receitas", type="primary", key="btn_import_receitas"):
                processar_importacao_receitas(df_upload, user_id, contas)
                # st.rerun() foi REMOVIDO
        except Exception as e:
            st.error(f"Erro ao ler o arquivo de receitas: {e}.")

with tab_investimentos:
    st.markdown("### 1. Baixe e Preencha o Template de Investimentos")
    # Pequeno ajuste no texto para refletir a nova funcionalidade
    st.info("Use este modelo para importar suas transações. Ativos não encontrados serão cadastrados automaticamente.")
    st.download_button(
        label="Baixar Template de Investimentos",
        data=gerar_template_csv_investimentos(),
        file_name="template_investimentos.csv",
        mime="text/csv",
    )
    st.markdown("---")
    st.markdown("### 2. Faça o Upload do Arquivo Preenchido")
    uploaded_file_investimentos = st.file_uploader("Escolha um arquivo CSV de investimentos", type="csv", key="uploader_investimentos")
    if uploaded_file_investimentos is not None:
        try:
            df_upload = pd.read_csv(uploaded_file_investimentos, sep=';')
            st.success("Arquivo de investimentos carregado:")
            st.dataframe(df_upload.head())
            if st.button("Confirmar e Iniciar Importação de Investimentos", type="primary", key="btn_import_inv"):
                processar_importacao_investimentos(df_upload, user_id)
                # st.rerun() foi REMOVIDO
        except Exception as e:
            st.error(f"Erro ao ler o arquivo de investimentos: {e}.")
