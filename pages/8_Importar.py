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

def processar_importacao_receitas(df, user_id, contas):
    """Função que itera sobre o DataFrame e insere as receitas no banco."""
    contas_dict = {conta[1].lower(): conta[0] for conta in contas}
    sucessos = 0
    erros = []

    colunas_necessarias = ['data', 'descricao', 'valor', 'conta', 'categoria']
    if not all(col in df.columns for col in colunas_necessarias):
        st.error(f"O arquivo enviado não contém todas as colunas necessárias. Verifique o template. Colunas esperadas: {colunas_necessarias}")
        return

    progress_bar = st.progress(0, text="Iniciando importação de receitas...")
    total_rows = len(df)

    for index, row in df.iterrows():
        try:
            descricao = str(row['descricao'])
            valor_str = str(row['valor']).replace("R$", "").replace(".", "").replace(",", ".").strip()
            valor = float(valor_str)
            data = pd.to_datetime(row['data'], dayfirst=True).date()
            conta_nome = str(row['conta']).lower()
            categoria_nome = str(row['categoria'])
            
            if conta_nome not in contas_dict:
                raise ValueError(f"Conta '{row['conta']}' não encontrada.")

            categoria_final = database.get_or_create_categoria_receita(user_id, categoria_nome)
            
            database.insert_receita(
                user_id=user_id,
                conta_id=contas_dict[conta_nome],
                data=data.isoformat(),
                valor=valor,
                categoria=categoria_final,
                descricao=descricao
            )
            sucessos += 1
        except Exception as e:
            erros.append(f"Linha {index + 2}: {descricao} - Erro: {e}")
        
        progress_bar.progress((index + 1) / total_rows, text=f"Processando receita {index + 1}/{total_rows}")

    st.success(f"Importação concluída! {sucessos} receita(s) importada(s) com sucesso.")
    if erros:
        st.error("Algumas linhas não puderam ser importadas:")
        with st.expander("Ver detalhes dos erros"):
            for erro in erros:
                st.write(erro)

def processar_importacao_despesas(df, user_id, contas):
    """
    Função simplificada que itera sobre o DataFrame e insere as despesas,
    assumindo que as colunas seguem o template e criando categorias automaticamente.
    """
    contas_dict = {conta[1].lower(): conta[0] for conta in contas}

    sucessos = 0
    erros = []
    
    # Validação de colunas antes de iniciar
    colunas_necessarias = ['data_compra', 'descricao', 'valor_total', 'conta', 'categoria', 'tipo_pagamento', 'parcelas']
    if not all(col in df.columns for col in colunas_necessarias):
        st.error(f"O arquivo enviado não contém todas as colunas necessárias. Verifique o template. Colunas esperadas: {colunas_necessarias}")
        return

    progress_bar = st.progress(0, text="Iniciando importação...")
    total_rows = len(df)

    for index, row in df.iterrows():
        try:
            # Extrai e limpa os dados usando nomes de coluna fixos
            descricao = str(row['descricao'])
            valor_str = str(row['valor_total']).replace("R$", "").replace(".", "").replace(",", ".").strip()
            valor = float(valor_str)
            data_compra = pd.to_datetime(row['data_compra'], dayfirst=True).date()
            conta_nome = str(row['conta']).lower()
            categoria_nome = str(row['categoria'])
            tipo_pagamento = str(row['tipo_pagamento']).lower()
            parcelas = int(row['parcelas'])
            
            # Validações
            if conta_nome not in contas_dict:
                raise ValueError(f"Conta '{row['conta']}' não encontrada no seu cadastro.")
            if tipo_pagamento not in ['crédito', 'débito']:
                raise ValueError(f"Tipo de pagamento '{tipo_pagamento}' inválido (deve ser 'crédito' ou 'débito').")

            # **NOVIDADE: Busca ou cria a categoria automaticamente**
            categoria_final = database.get_or_create_categoria_despesa(user_id, categoria_nome)
            
            database.insert_despesa(
                user_id=user_id,
                conta_id=contas_dict[conta_nome],
                data_compra_str=data_compra.isoformat(),
                valor=valor,
                categoria=categoria_final,
                tipo_pagamento=tipo_pagamento,
                parcelas=parcelas,
                descricao=descricao
            )
            sucessos += 1
        except Exception as e:
            erros.append(f"Linha {index + 2}: {descricao} - Erro: {e}")
        
        progress_bar.progress((index + 1) / total_rows, text=f"Processando linha {index + 1}/{total_rows}")

    st.success(f"Importação concluída! {sucessos} item(ns) importado(s) com sucesso.")
    if erros:
        st.error("Algumas linhas não puderam ser importadas:")
        with st.expander("Ver detalhes dos erros"):
            for erro in erros:
                st.write(erro)

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

# ADICIONE ESTA NOVA FUNÇÃO DE PROCESSAMENTO
def processar_importacao_investimentos(df, user_id):
    """Função que itera sobre o DataFrame e insere as transações, criando ativos se necessário."""
    sucessos = 0
    erros = []

    # A coluna 'tipo_ativo' agora é necessária
    colunas_necessarias = ['data', 'codigo_ativo', 'tipo_transacao', 'quantidade', 'preco_unitario', 'tipo_ativo']
    if not all(col in df.columns for col in colunas_necessarias):
        st.error(f"O arquivo enviado não contém todas as colunas necessárias. Verifique o template. Colunas esperadas: {colunas_necessarias}")
        return

    progress_bar = st.progress(0, text="Iniciando importação de investimentos...")
    total_rows = len(df)

    for index, row in df.iterrows():
        try:
            codigo_ativo = str(row['codigo_ativo'])
            tipo_transacao = str(row['tipo_transacao']).lower()
            data = pd.to_datetime(row['data'], dayfirst=True).date()
            quantidade = float(row['quantidade'])
            preco_unitario = float(str(row['preco_unitario']).replace(",", "."))
            tipo_ativo = str(row['tipo_ativo']) # <-- NOVO CAMPO

            if tipo_transacao not in ['compra', 'venda']:
                raise ValueError(f"Tipo de transação '{row['tipo_transacao']}' inválido. Use 'compra' ou 'venda'.")

            # --- LÓGICA ALTERADA ---
            # Em vez de procurar em um dicionário, chamamos a nova função que busca ou cria.
            investimento_id = database.get_or_create_investimento(user_id, codigo_ativo, tipo_ativo)
            
            database.add_transacao_investimento(investimento_id, tipo_transacao, data.isoformat(), quantidade, preco_unitario)
            sucessos += 1
        except Exception as e:
            erros.append(f"Linha {index + 2}: Ativo '{row['codigo_ativo']}' - Erro: {e}")
        
        progress_bar.progress((index + 1) / total_rows, text=f"Processando transação {index + 1}/{total_rows}")

    st.success(f"Importação concluída! {sucessos} transação(ões) de investimento importada(s) com sucesso.")
    if erros:
        st.error("Algumas linhas não puderam ser importadas:")
        with st.expander("Ver detalhes dos erros"):
            for erro in erros:
                st.write(erro)

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
