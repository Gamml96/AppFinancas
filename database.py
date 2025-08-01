# database.py (versão final e completa para PostgreSQL/Supabase)
import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import bcrypt
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
import utils
import time

# --- FUNÇÃO CENTRAL DE CONEXÃO ---
def _get_db_connection():
    """
    Cria uma conexão com o banco de dados PostgreSQL usando a URI de pooling,
    que é o método mais robusto para ambientes como o Streamlit Cloud.
    """
    try:
        # Conecta usando a URI de pooling completa, que está nos segredos
        conn = psycopg2.connect(st.secrets["postgres"]["connection_uri"])
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        st.stop()

# --- FUNÇÃO CENTRAL DE EXECUÇÃO DE QUERIES ---
def _execute_query(query, params=None, fetch=None, commit=False, executemany_params=None):
    """
    Executa uma query no banco de dados de forma segura e centralizada.
    """
    conn = _get_db_connection()
    result = None
    try:
        with conn.cursor() as cur:
            if executemany_params:
                psycopg2.extras.execute_values(cur, query, executemany_params)
            else:
                cur.execute(query, params)

            if fetch == 'one':
                result = cur.fetchone()
            elif fetch == 'all':
                result = cur.fetchall()
            
            if commit:
                conn.commit()
    except Exception as e:
        st.error(f"Erro de banco de dados: {e}")
        # Em caso de erro, desfaz a transação
        conn.rollback()
    finally:
        conn.close()
    
    return result


# --- NOVAS FUNÇÕES DE INSERÇÃO EM LOTE ---

def batch_insert_receitas(user_id, dados_receitas):
    """Insere uma lista de receitas em uma única transação."""
    if not dados_receitas:
        return
    conn = _get_db_connection()
    with conn.cursor() as cur:
        # Adiciona o user_id a cada registro antes de inserir
        dados_com_user_id = [(user_id,) + tupla for tupla in dados_receitas]
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao) VALUES %s",
            dados_com_user_id
        )
    conn.commit()
    conn.close()
    st.cache_data.clear()

def batch_insert_despesas(user_id, dados_despesas):
    """Insere uma lista de despesas em uma única transação."""
    if not dados_despesas:
        return
    conn = _get_db_connection()
    with conn.cursor() as cur:
        # Adiciona o user_id a cada registro
        dados_com_user_id = [(user_id,) + tupla for tupla in dados_despesas]
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, parcela_grupo_id) VALUES %s",
            dados_com_user_id
        )
    conn.commit()
    conn.close()
    st.cache_data.clear()

def batch_insert_transacoes_investimento(dados_transacoes):
    """Insere uma lista de transações de investimento em uma única transação."""
    if not dados_transacoes:
        return
    conn = _get_db_connection()
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO transacoes_investimento (investimento_id, tipo_transacao, data, quantidade, preco_unitario) VALUES %s",
            dados_transacoes
        )
    conn.commit()
    conn.close()
    st.cache_data.clear()


# --- Funções Auxiliares (sem conexão com BD, permanecem as mesmas) ---
def _ajustar_data_para_sexta_anterior(data_obj):
    if data_obj.weekday() == 5: return data_obj - datetime.timedelta(days=1)
    if data_obj.weekday() == 6: return data_obj - datetime.timedelta(days=2)
    return data_obj

def _calcular_vencimento_credito(data_compra_obj, dia_vencimento, dias_fechamento):
    try:
        vencimento_base = (data_compra_obj + relativedelta(months=1)).replace(day=dia_vencimento)
    except ValueError:
        proximo_mes = data_compra_obj + relativedelta(months=1)
        ultimo_dia_mes = (proximo_mes.replace(day=1) + relativedelta(months=1)) - datetime.timedelta(days=1)
        vencimento_base = ultimo_dia_mes
    fechamento_preliminar = vencimento_base - datetime.timedelta(days=dias_fechamento)
    fechamento_real = _ajustar_data_para_sexta_anterior(fechamento_preliminar)
    if data_compra_obj <= fechamento_real: return vencimento_base
    else: return vencimento_base + relativedelta(months=1)

# -------- Usuários --------
def add_user(username, name, email, hashed_password, is_admin=False):
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (username, name, email, password, is_admin) VALUES (%s, %s, %s, %s, %s) RETURNING user_id", (username, name, email, hashed_password, is_admin))
            user_id = cur.fetchone()[0]
            cur.execute("SELECT tipo_id, codigo, descricao FROM ativos_padrao")
            ativos_padrao = cur.fetchall()
            if ativos_padrao:
                dados_para_inserir = [(user_id, tipo_id, codigo, descricao) for tipo_id, codigo, descricao in ativos_padrao]
                psycopg2.extras.execute_values(cur, "INSERT INTO investimentos (user_id, tipo_id, codigo, descricao) VALUES %s", dados_para_inserir)
        conn.commit()
    finally:
        conn.close()
    st.cache_data.clear()

@st.cache_data
def get_all_users():
    return _execute_query("SELECT user_id, username, name, email, is_admin FROM users", fetch='all')

@st.cache_data
def is_user_admin(username):
    user = _execute_query("SELECT is_admin FROM users WHERE username = %s", (username,), fetch='one')
    return user[0] if user else False

@st.cache_data
def get_user_profile(username):
    # Selecionamos a nova coluna junto com as outras
    user = _execute_query("SELECT user_id, name, email, consent_ai_training FROM users WHERE username = %s", (username,), fetch='one')
    # Adicionamos o novo campo ao dicionário retornado
    return {"user_id": user[0], "name": user[1], "email": user[2], "consent_ai_training": user[3]} if user else None

@st.cache_data
def get_authenticator_credentials():
    users = _execute_query("SELECT username, name, password FROM users", fetch='all')
    return {"usernames": {u[0]: {"name": u[1], "password": u[2]} for u in users}}

def update_user_password(username, new_password):
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    _execute_query("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username), commit=True)
    st.cache_data.clear()

def update_user_profile(username, new_name, new_email):
    _execute_query("UPDATE users SET name = %s, email = %s WHERE username = %s", (new_name, new_email, username), commit=True)
    st.cache_data.clear()

def update_user_admin_status(user_id, is_admin):
    _execute_query("UPDATE users SET is_admin = %s WHERE user_id = %s", (is_admin, user_id), commit=True)
    st.cache_data.clear()

def delete_all_user_data(user_id, username):
    _execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), commit=True)
    st.cache_data.clear()
    
def delete_user_financial_data(user_id):
    queries = [
        "DELETE FROM receitas WHERE user_id = %s",
        "DELETE FROM despesas WHERE user_id = %s",
        "DELETE FROM categorias WHERE user_id = %s",
        "DELETE FROM investimentos WHERE user_id = %s",
        "DELETE FROM contas WHERE user_id = %s"
    ]
    for query in queries:
        _execute_query(query, (user_id,), commit=True)
    st.cache_data.clear()

def update_user_consent(user_id, consent_status):
    """Atualiza a permissão de um usuário para o treinamento da IA."""
    _execute_query("UPDATE users SET consent_ai_training = %s WHERE user_id = %s", (consent_status, user_id), commit=True)
    st.cache_data.clear() # Limpa o cache para garantir que a próxima leitura de perfil pegue o novo valor


# -------- Contas --------
def insert_conta(user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento):
    query = "INSERT INTO contas (user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento) VALUES (%s, %s, %s, %s, %s, %s)"
    params = (user_id, nome, vencimento, data_inicial, float(saldo_inicial), fechamento)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

@st.cache_data
def get_contas(user_id):
    return _execute_query("SELECT conta_id, nome, vencimento, data_inicial, saldo_inicial, fechamento FROM contas WHERE user_id = %s", (user_id,), fetch='all')

def update_conta(conta_id, user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento):
    query = "UPDATE contas SET nome = %s, vencimento = %s, data_inicial = %s, saldo_inicial = %s, fechamento = %s WHERE conta_id = %s AND user_id = %s"
    params = (nome, vencimento, data_inicial, float(saldo_inicial), fechamento, conta_id, user_id)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_conta(conta_id, user_id):
    _execute_query("DELETE FROM contas WHERE conta_id = %s AND user_id = %s", (conta_id, user_id), commit=True)
    st.cache_data.clear()

# -------- Categorias --------
def insert_categoria(user_id, tipo, nome):
    _execute_query("INSERT INTO categorias (user_id, tipo, nome) VALUES (%s, %s, %s) ON CONFLICT (user_id, tipo, nome) DO NOTHING", (user_id, tipo, nome), commit=True)
    st.cache_data.clear()

@st.cache_data
def get_categorias(user_id, tipo):
    return _execute_query("SELECT categoria_id, nome FROM categorias WHERE user_id = %s AND tipo = %s", (user_id, tipo), fetch='all')

def update_categoria(categoria_id, user_id, nome):
    _execute_query("UPDATE categorias SET nome = %s WHERE categoria_id = %s AND user_id = %s", (nome, categoria_id, user_id), commit=True)
    st.cache_data.clear()

def delete_categoria(categoria_id, user_id):
    _execute_query("DELETE FROM categorias WHERE categoria_id = %s AND user_id = %s", (categoria_id, user_id), commit=True)
    st.cache_data.clear()

def get_or_create_categoria(user_id, nome_categoria, tipo):
    nome_cat_clean = nome_categoria.strip().capitalize()
    query_select = "SELECT nome FROM categorias WHERE user_id = %s AND lower(nome) = %s AND tipo = %s"
    result = _execute_query(query_select, (user_id, nome_cat_clean.lower(), tipo), fetch='one')
    if result:
        return result[0]
    else:
        query_insert = "INSERT INTO categorias (user_id, tipo, nome) VALUES (%s, %s, %s)"
        _execute_query(query_insert, (user_id, tipo, nome_cat_clean), commit=True)
        st.cache_data.clear()
        return nome_cat_clean

def get_or_create_categoria_despesa(user_id, nome_categoria):
    return get_or_create_categoria(user_id, nome_categoria, 'despesa')

def get_or_create_categoria_receita(user_id, nome_categoria):
    return get_or_create_categoria(user_id, nome_categoria, 'receita')

# -------- Receitas --------

# Dicionário para calcular o delta da recorrência
RECORRENCIA_MAP = {
    "Diária": relativedelta(days=1),
    "Semanal": relativedelta(weeks=1),
    "Mensal": relativedelta(months=1),
    "Bimestral": relativedelta(months=2),
    "Trimestral": relativedelta(months=3),
    "Semestral": relativedelta(months=6),
    "Anual": relativedelta(years=1),
}

def insert_receita(user_id, conta_id, data_str, valor, categoria, descricao, recorrencia_freq=None, recorrencia_vezes=1):
    valor_float = float(valor)
    data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
    grupo_id = int(time.time() * 1000)

    dados_para_inserir = []

    if recorrencia_freq and recorrencia_vezes > 1:
        delta = RECORRENCIA_MAP.get(recorrencia_freq)
        if not delta:
            raise ValueError("Frequência de recorrência inválida.")
        
        for i in range(recorrencia_vezes):
            data_lancamento = data_obj + (delta * i)
            descricao_recorrencia = f"{descricao} ({i+1}/{recorrencia_vezes})"
            dados_para_inserir.append((
                user_id, conta_id, data_lancamento.isoformat(), valor_float,
                categoria, descricao_recorrencia, recorrencia_freq, grupo_id
            ))
    else:
        # Lançamento único
        dados_para_inserir.append((
            user_id, conta_id, data_str, valor_float,
            categoria, descricao, None, None
        ))
        
    # Executa a inserção em lote
    if dados_para_inserir:
        _execute_query(
            "INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao, recorrencia, recorrencia_grupo_id) VALUES %s",
            executemany_params=dados_para_inserir,
            commit=True
        )

    st.cache_data.clear()

@st.cache_data
def get_receitas(user_id):
    return _execute_query("SELECT receita_id, user_id, conta_id, data, valor, categoria, descricao FROM receitas WHERE user_id = %s", (user_id,), fetch='all')

def update_receita(receita_id, user_id, conta_id, data, valor, categoria, descricao):
    query = "UPDATE receitas SET conta_id = %s, data = %s, valor = %s, categoria = %s, descricao = %s WHERE receita_id = %s AND user_id = %s"
    params = (conta_id, data, float(valor), categoria, descricao, receita_id, user_id)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_receita(receita_id, user_id):
    _execute_query("DELETE FROM receitas WHERE receita_id = %s AND user_id = %s", (receita_id, user_id), commit=True)
    st.cache_data.clear()

# -------- Despesas --------

# No arquivo database.py

def insert_despesa(user_id, conta_id, data_compra_str, valor, categoria, tipo_pagamento, parcelas, descricao, recorrencia_freq=None, recorrencia_vezes=1):
    """
    Insere despesas com uma lógica unificada e corrigida para todos os cenários.
    """
    valor_float = float(valor)
    data_compra_base = datetime.datetime.strptime(data_compra_str, "%Y-%m-%d").date()
    grupo_id = int(time.time() * 1000)
    
    dados_para_inserir = []

    # --- Decisão Crítica: Determina o modo de operação ---
    is_recorrencia_mode = recorrencia_freq is not None and recorrencia_vezes > 1
    loop_count = recorrencia_vezes if is_recorrencia_mode else parcelas

    # --- Busca de dados do cartão (se necessário) ---
    dia_vencimento, dias_fechamento = None, None
    if tipo_pagamento == 'Crédito':
        contas = get_contas(user_id)
        conta_info = next((c for c in contas if c[0] == conta_id), None)
        if not conta_info: raise ValueError("Conta de Crédito não encontrada.")
        dia_vencimento, dias_fechamento = conta_info[2], conta_info[5]

    # --- Loop Único e Centralizado ---
    for i in range(loop_count):
        data_compra_iteracao = data_compra_base
        valor_iteracao = valor_float
        descricao_iteracao = descricao
        num_parcela = i + 1

        # --- Lógica de Recorrência ---
        if is_recorrencia_mode:
            delta = RECORRENCIA_MAP[recorrencia_freq]
            data_compra_iteracao = data_compra_base + (delta * i)
            descricao_iteracao = f"{descricao} ({i+1}/{loop_count})"
            num_parcela = 1 # Para recorrências, a parcela é sempre 1

        # --- Lógica de Parcelamento (ou lançamento único) ---
        else:
            if loop_count > 1: # Apenas se for parcelado
                descricao_iteracao = f"{descricao} ({i+1}/{loop_count})"
            if i == 0:
                valor_parcela_padrao = round(valor_float / loop_count, 2)
                diferenca = round(valor_float - (valor_parcela_padrao * loop_count), 2)
                valor_iteracao = valor_parcela_padrao + diferenca
            else:
                valor_iteracao = round(valor_float / loop_count, 2)

        # --- Cálculo de Vencimento (unificado) ---
        vencimento_iteracao = data_compra_iteracao
        if tipo_pagamento == 'Crédito':
            if is_recorrencia_mode:
                vencimento_iteracao = _calcular_vencimento_credito(data_compra_iteracao, dia_vencimento, dias_fechamento)
            else:
                primeiro_vencimento = _calcular_vencimento_credito(data_compra_base, dia_vencimento, dias_fechamento)
                vencimento_iteracao = primeiro_vencimento + relativedelta(months=i)
        
        # <<< A CORREÇÃO ESTÁ AQUI >>>
        elif tipo_pagamento == 'Débito' and not is_recorrencia_mode:
            # Para Débito parcelado, o vencimento também avança mensalmente, a partir da data da compra.
            vencimento_iteracao = data_compra_base + relativedelta(months=i)
        
        # Monta o registro para inserção
        dados_para_inserir.append((
            user_id, conta_id, data_compra_iteracao.isoformat(), vencimento_iteracao.isoformat(),
            valor_iteracao, categoria, tipo_pagamento, num_parcela,
            descricao_iteracao, recorrencia_freq if is_recorrencia_mode else None,
            grupo_id if loop_count > 1 else None
        ))

    # Inserção em lote no banco
    if dados_para_inserir:
        _execute_query(
            "INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, recorrencia, parcela_grupo_id) VALUES %s",
            executemany_params=dados_para_inserir, commit=True
        )
    st.cache_data.clear()

    
def get_despesas(user_id):
    """
    Busca todas as despesas de um usuário, garantindo que TODAS as 12 colunas sejam retornadas.
    """
    conn = _get_db_connection() # Usando a conexão do Supabase/PostgreSQL
    with conn.cursor() as cur:
        # Query CORRIGIDA, selecionando TODAS as 12 colunas
        query = """
            SELECT 
                despesa_id, user_id, conta_id, data_compra, data_vencimento, 
                valor, categoria, tipo_pagamento, parcelas, descricao, 
                recorrencia, parcela_grupo_id 
            FROM despesas 
            WHERE user_id = %s 
            ORDER BY data_vencimento DESC
        """
        cur.execute(query, (user_id,))
        despesas = cur.fetchall()
    conn.close()
    return despesas

def update_despesa(despesa_id, user_id, conta_id, data_compra, data_vencimento, valor, categoria, descricao):
    query = "UPDATE despesas SET conta_id = %s, data_compra = %s, data_vencimento = %s, valor = %s, categoria = %s, descricao = %s WHERE despesa_id = %s AND user_id = %s"
    params = (conta_id, data_compra, data_vencimento, float(valor), categoria, descricao, despesa_id, user_id)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_despesa(despesa_id, user_id):
    _execute_query("DELETE FROM despesas WHERE despesa_id = %s AND user_id = %s", (despesa_id, user_id), commit=True)
    st.cache_data.clear()

def realizar_transferencia(user_id, conta_origem_id, conta_destino_id, valor, data):
    """
    Registra uma transferência entre contas como uma despesa na origem
    e uma receita no destino. Usa uma única transação para garantir a atomicidade.
    """
    if conta_origem_id == conta_destino_id:
        raise ValueError("A conta de origem e destino não podem ser a mesma.")
    
    valor_float = float(valor)
    data_iso = data.isoformat()
    
    # Descrições e categoria padrão para identificar as transações de transferência
    descricao_despesa = f"Transferência enviada"
    descricao_receita = f"Transferência recebida"
    categoria_transferencia = "Transferência"
    
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # Garante que a categoria "Transferência" exista
            # Usando a função que já existe para buscar ou criar
            get_or_create_categoria(user_id, categoria_transferencia, 'despesa')
            get_or_create_categoria(user_id, categoria_transferencia, 'receita')

            # 1. Registra a saída (despesa) na conta de origem
            cur.execute(
                """
                INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao)
                VALUES (%s, %s, %s, %s, %s, %s, 'Débito', 1, %s)
                """,
                (user_id, conta_origem_id, data_iso, data_iso, valor_float, categoria_transferencia, descricao_despesa)
            )
            
            # 2. Registra a entrada (receita) na conta de destino
            cur.execute(
                """
                INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, conta_destino_id, data_iso, valor_float, categoria_transferencia, descricao_receita)
            )
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
            
    st.cache_data.clear()

# -------- Investimentos --------
@st.cache_data
def get_tipos_investimento():
    return _execute_query("SELECT tipo_id, nome FROM tipos_investimento ORDER BY nome", fetch='all')

def add_investimento(user_id, tipo_id, codigo, descricao, indexador=None, taxa_percentual=None, data_vencimento=None):
    # Converte data de vencimento para string se não for nula
    data_vencimento_str = data_vencimento.isoformat() if data_vencimento else None
    query = """
        INSERT INTO investimentos (user_id, tipo_id, codigo, descricao, indexador, taxa_percentual, data_vencimento) 
        VALUES (%s, %s, %s, %s, %s, %s, %s) 
        ON CONFLICT (user_id, codigo) DO NOTHING
    """
    params = (user_id, tipo_id, codigo.upper(), descricao, indexador, taxa_percentual, data_vencimento_str)
    _execute_query(query, params,commit=True)
    st.cache_data.clear()

def get_or_create_investimento(user_id, codigo, tipo_nome, descricao="", indexador=None, taxa_percentual=None, data_vencimento=None):
    """
    Verifica se um ativo existe. Se não, cria um novo com todos os detalhes.
    Retorna o ID do investimento.
    """
    codigo_upper = codigo.strip().upper()
    if not codigo_upper:
        raise ValueError("O código do ativo não pode ser vazio.")

    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT investimento_id FROM investimentos WHERE user_id = %s AND codigo = %s", (user_id, codigo_upper))
            result = cur.fetchone()
            
            if result:
                return result[0] # Retorna o ID do ativo existente
            else:
                cur.execute("SELECT tipo_id FROM tipos_investimento WHERE lower(nome) = %s", (tipo_nome.lower(),))
                tipo_result = cur.fetchone()
                if not tipo_result:
                    raise ValueError(f"O tipo de ativo '{tipo_nome}' não é válido.")
                tipo_id = tipo_result[0]

                # Query de inserção atualizada para incluir os novos campos
                query = """
                    INSERT INTO investimentos (user_id, tipo_id, codigo, descricao, indexador, taxa_percentual, data_vencimento)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING investimento_id
                """
                params = (user_id, tipo_id, codigo_upper, descricao.strip(), indexador, taxa_percentual, data_vencimento)
                cur.execute(query, params)
                new_id = cur.fetchone()[0]
                conn.commit()
                st.cache_data.clear()
                return new_id
    finally:
        conn.close()

def add_transacao_investimento(investimento_id, tipo_transacao, data, quantidade, preco_unitario):
    query = "INSERT INTO transacoes_investimento (investimento_id, tipo_transacao, data, quantidade, preco_unitario) VALUES (%s, %s, %s, %s, %s)"
    params = (investimento_id, tipo_transacao, data, quantidade, preco_unitario)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

@st.cache_data
def get_portfolio_consolidado(user_id):
    """
    Calcula a posição atual de cada ativo do usuário, mostrando apenas ativos
    que possuem transações e cuja posição atual é maior que zero.
    """
    # A query agora usa INNER JOIN para excluir ativos sem transações
    # e tem um HAVING simplificado para mostrar apenas posições > 0.
    query = """
        SELECT
            i.investimento_id, i.codigo, i.descricao, ti.nome as tipo,
            SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE -t.quantidade END) as quantidade_total,
            SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade * t.preco_unitario ELSE 0 END) / NULLIF(SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE 0 END), 0) as preco_medio_compra,
            i.indexador, i.taxa_percentual, i.data_vencimento
        FROM investimentos i
        INNER JOIN transacoes_investimento t ON i.investimento_id = t.investimento_id
        JOIN tipos_investimento ti ON i.tipo_id = ti.tipo_id
        WHERE i.user_id = %s
        GROUP BY i.investimento_id, i.codigo, i.descricao, ti.nome
        HAVING SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE -t.quantidade END) > 0.00000001
        ORDER BY i.codigo
    """
    # Usamos _execute_query que já foi refatorada para o Supabase
    return _execute_query(query, (user_id,), fetch='all')

@st.cache_data
def get_investimentos_usuario(user_id):
    return _execute_query("SELECT investimento_id, codigo FROM investimentos WHERE user_id = %s ORDER BY codigo", (user_id,), fetch='all')

@st.cache_data
def get_all_transacoes(user_id):
    query = "SELECT t.transacao_id, i.codigo, t.tipo_transacao, t.data, t.quantidade, t.preco_unitario FROM transacoes_investimento t JOIN investimentos i ON t.investimento_id = i.investimento_id WHERE i.user_id = %s ORDER BY t.data DESC"
    return _execute_query(query, (user_id,), fetch='all')

def update_transacao_investimento(transacao_id, data, quantidade, preco_unitario):
    query = "UPDATE transacoes_investimento SET data = %s, quantidade = %s, preco_unitario = %s WHERE transacao_id = %s"
    _execute_query(query, (data, quantidade, preco_unitario, transacao_id), commit=True)
    st.cache_data.clear()

def delete_transacao_investimento(transacao_id):
    _execute_query("DELETE FROM transacoes_investimento WHERE transacao_id = %s", (transacao_id,), commit=True)
    st.cache_data.clear()

@st.cache_data
def get_transacoes_por_investimento_id(investimento_id):
    """Busca as transações de um único ativo, útil para Renda Fixa."""
    query = "SELECT data, quantidade, preco_unitario FROM transacoes_investimento WHERE investimento_id = %s AND tipo_transacao = 'compra' ORDER BY data"
    return _execute_query(query, (investimento_id,), fetch='all')
    
@st.cache_data
def get_all_ativos_usuario(user_id):
    """Busca TODOS os ativos cadastrados por um usuário, com todos os detalhes."""
    query = """
        SELECT i.investimento_id, i.codigo, i.descricao, ti.nome as tipo, 
               i.indexador, i.taxa_percentual, i.data_vencimento
        FROM investimentos i
        JOIN tipos_investimento ti ON i.tipo_id = ti.tipo_id
        WHERE i.user_id = %s
        ORDER BY i.codigo
    """
    return _execute_query(query, (user_id,), fetch='all')

def update_ativo(investimento_id, user_id, descricao, indexador, taxa_percentual, data_vencimento):
    """Atualiza os detalhes de um ativo específico."""
    data_vencimento_str = data_vencimento.isoformat() if data_vencimento else None
    query = """
        UPDATE investimentos 
        SET descricao = %s, indexador = %s, taxa_percentual = %s, data_vencimento = %s
        WHERE investimento_id = %s AND user_id = %s
    """
    params = (descricao, indexador, taxa_percentual, data_vencimento_str, investimento_id, user_id)
    # A CORREÇÃO CRÍTICA ESTÁ AQUI: adicionar commit=True
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_ativo(investimento_id, user_id):
    """Exclui um ativo. A constraint ON DELETE CASCADE no banco de dados
       garante que as transações associadas também sejam removidas.
    """
    # A exceção será levantada pelo SGBD se a foreign key não tiver CASCADE
    # e houver transações, o que será capturado na interface.
    query = "DELETE FROM investimentos WHERE investimento_id = %s AND user_id = %s"
    _execute_query(query, (investimento_id, user_id), commit=True)
    st.cache_data.clear()


# --- Orçamento ---

@st.cache_data
def get_orcamentos(user_id):
    """Busca todos os orçamentos definidos por um usuário."""
    query = "SELECT categoria_nome, limite_mensal FROM orcamentos WHERE user_id = %s"
    return _execute_query(query, (user_id,), fetch='all')

def set_orcamento(user_id, categoria_nome, limite):
    """
    Insere ou atualiza o limite de orçamento para uma categoria específica.
    Usa a funcionalidade 'ON CONFLICT' do PostgreSQL para fazer um 'UPSERT'.
    """
    query = """
        INSERT INTO orcamentos (user_id, categoria_nome, limite_mensal)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, categoria_nome) 
        DO UPDATE SET limite_mensal = EXCLUDED.limite_mensal;
    """
    _execute_query(query, (user_id, categoria_nome, float(limite)),commit=True)
    st.cache_data.clear()


# -------- Relatórios e Consolidações --------
@st.cache_data
def get_proximos_lancamentos(user_id, dias_futuros=7, conta_id=None):
    """
    Busca receitas e despesas futuras, com filtro opcional por conta.
    """
    lancamentos = []
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=dias_futuros)

    filtro_sql = " AND conta_id = %s" if conta_id else ""
    params_base = [user_id]
    if conta_id:
        params_base.extend([today.isoformat(), end_date.isoformat(), conta_id])
    else:
        params_base.extend([today.isoformat(), end_date.isoformat()])

    conn = _get_db_connection()
    with conn.cursor() as cur:
        query_receitas = "SELECT data, descricao, valor, 'receita' as tipo FROM receitas WHERE user_id = %s AND data BETWEEN %s AND %s" + filtro_sql
        cur.execute(query_receitas, tuple(params_base))
        lancamentos.extend(cur.fetchall())

        query_despesas = "SELECT data_vencimento, descricao, valor, 'despesa' as tipo FROM despesas WHERE user_id = %s AND data_vencimento BETWEEN %s AND %s" + filtro_sql
        cur.execute(query_despesas, tuple(params_base))
        lancamentos.extend(cur.fetchall())
        
    conn.close()
    lancamentos.sort(key=lambda x: x[0])
    return lancamentos

@st.cache_data
def get_despesas_por_categoria(user_id, dt_start, dt_end):
    query = "SELECT categoria, SUM(valor) FROM despesas WHERE user_id = %s AND data_vencimento BETWEEN %s AND %s AND categoria GROUP BY categoria != 'Transfêrencia' ORDER BY SUM(valor) DESC"
    return _execute_query(query, (user_id, dt_start, dt_end), fetch='all')

@st.cache_data
def get_total_receitas_mensal(user_id):
    query = "SELECT TO_CHAR(data, 'YYYY-MM') as mes, SUM(valor) FROM receitas WHERE user_id = %s GROUP BY mes ORDER BY mes"
    return _execute_query(query, (user_id,), fetch='all')

@st.cache_data
def get_total_despesas_mensal(user_id):
    query = "SELECT TO_CHAR(data_vencimento, 'YYYY-MM') as mes, SUM(valor) FROM despesas WHERE user_id = %s GROUP BY mes ORDER BY mes"
    return _execute_query(query, (user_id,), fetch='all')

@st.cache_data
def get_fatura_cartao(user_id, conta_id, mes, ano):
    mes_ano_str = f"{ano:04d}-{mes:02d}"
    query = "SELECT data_compra, descricao, valor FROM despesas WHERE user_id = %s AND conta_id = %s AND tipo_pagamento = 'Crédito' AND TO_CHAR(data_vencimento, 'YYYY-MM') = %s ORDER BY data_compra"
    return _execute_query(query, (user_id, conta_id, mes_ano_str), fetch='all')

@st.cache_data
def get_historico_faturas(user_id, conta_id):
    """
    Busca o valor total de faturas de um cartão de crédito específico ao longo do tempo.
    """
    query = """
        SELECT
            TO_CHAR(data_vencimento, 'YYYY-MM') as mes_fatura,
            SUM(valor) as total_fatura
        FROM despesas
        WHERE user_id = %s AND conta_id = %s AND tipo_pagamento = 'Crédito'
        GROUP BY mes_fatura
        ORDER BY mes_fatura ASC
    """
    return _execute_query(query, (user_id, conta_id), fetch='all')

@st.cache_data
def get_transacoes_consolidadas(user_id, conta_id=None):
    """
    Busca e consolida todas as transações, com um filtro opcional por conta.
    """
    transacoes = []
    
    # Constrói a cláusula WHERE dinamicamente
    filtro_sql = " AND conta_id = %s" if conta_id else ""
    params_base = [user_id]
    if conta_id:
        params_base.append(conta_id)
    
    conn = _get_db_connection()
    with conn.cursor() as cur:
        # Busca Saldos Iniciais (se for uma conta específica, pega só o dela)
        query_contas = "SELECT data_inicial, nome, saldo_inicial FROM contas WHERE user_id = %s" + filtro_sql
        cur.execute(query_contas, tuple(params_base))
        for data, nome, saldo in cur.fetchall():
            if data and saldo != 0:
                transacoes.append((data, f"Saldo Inicial - {nome}", saldo))
        
        # Busca Receitas
        query_receitas = "SELECT data, descricao, valor FROM receitas WHERE user_id = %s" + filtro_sql
        cur.execute(query_receitas, tuple(params_base))
        transacoes.extend(cur.fetchall())
            
        # Busca Despesas
        query_despesas = "SELECT data_vencimento, descricao, valor FROM despesas WHERE user_id = %s" + filtro_sql
        cur.execute(query_despesas, tuple(params_base))
        for data, descricao, valor in cur.fetchall():
            transacoes.append((data, descricao, -valor))
            
    conn.close()
    return transacoes

# -------- Operações Estruturadas com Opções --------

def add_operacao_estruturada(user_id, ativo_subjacente, nome_estrategia, data_montagem, pernas, data_desmontagem=None):
    """
    Adiciona uma nova operação estruturada e suas pernas em uma única transação.
    Se data_desmontagem for fornecida, a operação já entra como 'Fechada'.
    """
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            status = 'Fechada' if data_desmontagem else 'Aberta'
            resultado_final = None

            if status == 'Fechada':
                resultado_final = 0
                for p in pernas:
                    preco_saida = p.get('preco_saida', 0.0)
                    if p['tipo_operacao'] == 'compra':
                        resultado_perna = (preco_saida - p['preco_entrada']) * p['quantidade']
                    else:
                        resultado_perna = (p['preco_entrada'] - preco_saida) * p['quantidade']
                    resultado_final += resultado_perna

            cur.execute(
                "INSERT INTO operacoes_estruturadas (user_id, ativo_subjacente, nome_estrategia, data_montagem, status, data_desmontagem, resultado) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING operacao_id",
                (user_id, ativo_subjacente, nome_estrategia, data_montagem, status, data_desmontagem, resultado_final)
            )
            operacao_id = cur.fetchone()[0]

            dados_pernas = [
                (
                    operacao_id, p['codigo_opcao'], p['tipo_opcao'], p['tipo_operacao'],
                    p['strike'], p['quantidade'], p['preco_entrada'], p['data_vencimento'],
                    p.get('preco_saida') if status == 'Fechada' else None
                )
                for p in pernas
            ]
            
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO operacoes_pernas (operacao_id, codigo_opcao, tipo_opcao, tipo_operacao, strike, quantidade, preco_entrada, data_vencimento, preco_saida) VALUES %s",
                dados_pernas
            )
            
            conn.commit()
    except Exception as e:
        conn.rollback(); raise e
    finally:
        conn.close()
    st.cache_data.clear()

@st.cache_data
def get_operacoes_estruturadas(user_id, status="Aberta"):
    """
    Busca todas as operações estruturadas de um usuário com um determinado status.
    --- VERSÃO ATUALIZADA PARA INCLUIR strike E perna_id ---
    """
    query = """
        SELECT
            op.operacao_id, op.ativo_subjacente, op.nome_estrategia,
            op.data_montagem, op.status, p.perna_id, p.codigo_opcao,
            p.tipo_opcao, p.tipo_operacao, p.strike, p.quantidade, -- <<< STRIKE ADICIONADO AQUI
            p.preco_entrada, p.data_vencimento
        FROM operacoes_estruturadas op
        JOIN operacoes_pernas p ON op.operacao_id = p.operacao_id
        WHERE op.user_id = %s AND op.status = %s
        ORDER BY op.data_montagem DESC, op.operacao_id, p.perna_id
    """
    return _execute_query(query, (user_id, status), fetch='all')

def desmontar_operacao(operacao_id, data_desmontagem, pernas_saida):
    """
    Atualiza os preços de saída das pernas, fecha a operação e calcula o resultado.
    'pernas_saida' é um dicionário {codigo_opcao: preco_saida}
    """
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            resultado_final = 0
            
            # Pega todas as pernas da operação para calcular o resultado
            cur.execute("SELECT codigo_opcao, tipo_operacao, quantidade, preco_entrada FROM operacoes_pernas WHERE operacao_id = %s", (operacao_id,))
            todas_pernas = cur.fetchall()
            
            for codigo, tipo_op, qtd, preco_ent in todas_pernas:
                preco_saida = pernas_saida.get(codigo, 0.0)
                
                # Atualiza o preço de saída no banco
                cur.execute(
                    "UPDATE operacoes_pernas SET preco_saida = %s WHERE operacao_id = %s AND codigo_opcao = %s",
                    (preco_saida, operacao_id, codigo)
                )
                
                # Calcula o resultado da perna
                if tipo_op == 'compra': # Comprou na entrada, vendeu na saída
                    resultado_perna = (preco_saida - preco_ent) * qtd
                else: # Vendeu na entrada, comprou na saída
                    resultado_perna = (preco_ent - preco_saida) * qtd
                
                resultado_final += resultado_perna

            # Atualiza a operação principal com o resultado e a data de desmontagem
            cur.execute(
                "UPDATE operacoes_estruturadas SET status = 'Fechada', data_desmontagem = %s, resultado = %s WHERE operacao_id = %s",
                (data_desmontagem, resultado_final, operacao_id)
            )
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    st.cache_data.clear()

def update_operacao_header(operacao_id, ativo_subjacente, nome_estrategia, data_montagem):
    """Atualiza os dados principais (cabeçalho) de uma operação."""
    query = """
        UPDATE operacoes_estruturadas 
        SET ativo_subjacente = %s, nome_estrategia = %s, data_montagem = %s
        WHERE operacao_id = %s
    """
    _execute_query(query, (ativo_subjacente, nome_estrategia, data_montagem, operacao_id), commit=True)
    st.cache_data.clear()

def update_operacao_perna(perna_id, codigo_opcao, tipo_operacao, strike, quantidade, preco_entrada, data_vencimento):
    """
    Atualiza os detalhes de uma única perna da operação.
    --- VERSÃO ATUALIZADA PARA INCLUIR STRIKE ---
    """
    tipo_opcao = "CALL" if 'C' in codigo_opcao.upper() else "PUT"
    query = "UPDATE operacoes_pernas SET codigo_opcao = %s, tipo_opcao = %s, tipo_operacao = %s, strike = %s, quantidade = %s, preco_entrada = %s, data_vencimento = %s WHERE perna_id = %s"
    params = (codigo_opcao, tipo_opcao, tipo_operacao, strike, quantidade, preco_entrada, data_vencimento, perna_id)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_operacao_perna(perna_id):
    """Exclui uma única perna de uma operação."""
    _execute_query("DELETE FROM operacoes_pernas WHERE perna_id = %s", (perna_id,), commit=True)
    st.cache_data.clear()

def delete_operacao_inteira(operacao_id):
    """
    Exclui uma operação estruturada inteira. 
    A configuração 'ON DELETE CASCADE' no banco de dados cuidará de excluir as pernas associadas.
    """
    _execute_query("DELETE FROM operacoes_estruturadas WHERE operacao_id = %s", (operacao_id,), commit=True)
    st.cache_data.clear()

@st.cache_data
def get_operacoes_finalizadas(user_id):
    """
    Busca todas as operações com status 'Fechada' ou 'Expirada'.
    --- VERSÃO ATUALIZADA PARA INCLUIR TODOS OS DETALHES DAS PERNAS ---
    """
    query = """
        SELECT
            op.operacao_id,
            op.ativo_subjacente,
            op.nome_estrategia,
            op.data_montagem,
            op.data_desmontagem,
            op.status,
            op.resultado,
            p.codigo_opcao,    -- Adicionado
            p.tipo_opcao,      -- Adicionado
            p.tipo_operacao,   -- Adicionado
            p.strike,
            p.quantidade
        FROM operacoes_estruturadas op
        JOIN operacoes_pernas p ON op.operacao_id = p.operacao_id
        WHERE op.user_id = %s AND op.status IN ('Fechada', 'Expirada')
        ORDER BY op.data_desmontagem DESC, op.operacao_id
    """
    return _execute_query(query, (user_id,), fetch='all')

def reabrir_operacao(operacao_id):
    """
    Reabre uma operação finalizada, revertendo seu status e limpando os dados de saída.
    """
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Limpa os dados de saída das pernas
            cur.execute(
                "UPDATE operacoes_pernas SET preco_saida = NULL WHERE operacao_id = %s",
                (operacao_id,)
            )

            # 2. Reverte o status da operação principal
            cur.execute(
                "UPDATE operacoes_estruturadas SET status = 'Aberta', data_desmontagem = NULL, resultado = NULL WHERE operacao_id = %s",
                (operacao_id,)
            )
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    st.cache_data.clear()

# --- IA ---
def get_all_despesas_for_training():
    """
    Busca as colunas 'Descrição' e 'Categoria' de todas as despesas de usuários
    que deram consentimento para o uso de seus dados.
    """
    query = """
        SELECT d.descricao, d.categoria
        FROM despesas d
        JOIN users u ON d.user_id = u.user_id
        WHERE u.consent_ai_training = TRUE
    """
    return _execute_query(query, fetch='all')

def get_financial_summary_for_ai(user_id, start_date, end_date):
    """
    Coleta um resumo dos dados financeiros em um período específico para ser usado pela IA.
    """
    conn = _get_db_connection()
    summary = {}
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Gastos totais por categoria no período selecionado
            cur.execute("""
                SELECT categoria, SUM(valor) as total
                FROM despesas
                WHERE user_id = %s AND data_vencimento BETWEEN %s AND %s
                GROUP BY categoria
                ORDER BY total DESC;
            """, (user_id, start_date, end_date))
            summary['gastos_recentes'] = cur.fetchall()

            # Receitas totais no período selecionado
            cur.execute("""
                SELECT SUM(valor) as total
                FROM receitas
                WHERE user_id = %s AND data BETWEEN %s AND %s;
            """, (user_id, start_date, end_date))
            summary['receitas_recentes'] = cur.fetchone()['total'] or 0

            # Orçamentos definidos pelo usuário (continua o mesmo)
            cur.execute("""
                SELECT categoria_nome, limite_mensal
                FROM orcamentos
                WHERE user_id = %s;
            """, (user_id,))
            summary['orcamentos'] = cur.fetchall()
            
    finally:
        conn.close()
        
    return summary

def get_full_database_schema():
    """
    Inspeciona o banco de dados e retorna uma string descrevendo o schema
    de tabelas relevantes para as perguntas do usuário.
    """
    conn = _get_db_connection()
    schema_info = ""
    try:
        with conn.cursor() as cur:
            # Lista de tabelas que a IA pode consultar
            tabelas = ['despesas', 'receitas', 'contas', 'categorias', 'orcamentos']
            for tabela in tabelas:
                schema_info += f"Tabela '{tabela}':\n"
                # Usamos a view information_schema para obter os detalhes das colunas
                cur.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{tabela}';
                """)
                colunas = cur.fetchall()
                for col in colunas:
                    schema_info += f"  - {col[0]} ({col[1]})\n"
                schema_info += "\n"
    except Exception as e:
        return f"Erro ao buscar schema: {e}"
    finally:
        conn.close()
    return schema_info

def execute_generated_sql(query, params=None):
    """
    Executa uma query SQL gerada pela IA de forma segura.
    Retorna os resultados como uma lista de dicionários.
    """
    # Medida de segurança CRÍTICA: só permite queries de leitura.
    if not query.strip().upper().startswith("SELECT"):
        raise ValueError("Ação não permitida. Apenas consultas SELECT são autorizadas.")
        
    conn = _get_db_connection()
    results = []
    try:
        # Usamos RealDictCursor para obter resultados como dicionários, mais fácil para a IA ler.
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            results = cur.fetchall()
    finally:
        conn.close()
    return results


def get_resultados_operacoes_estruturadas_por_ativo(user_id):
    """
    Busca o resultado consolidado de todas as operações estruturadas fechadas,
    agrupado por ativo subjacente.
    """
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            # A consulta SQL faz o trabalho pesado:
            # - Filtra por usuário e por operações 'Fechada'
            # - Agrupa os resultados pelo 'ativo_subjacente'
            # - Soma (SUM) os resultados de cada grupo
            # - Conta (COUNT) quantas operações formam aquele grupo
            cur.execute("""
                SELECT 
                    ativo_subjacente, 
                    SUM(resultado) AS resultado_total,
                    COUNT(operacao_id) AS quantidade_operacoes
                FROM 
                    operacoes_estruturadas
                WHERE 
                    user_id = %s AND status = 'Fechada'
                GROUP BY 
                    ativo_subjacente
                ORDER BY 
                    resultado_total DESC;
            """, (user_id,))
            
            # Retorna uma lista de tuplas com (ativo, resultado_total, quantidade)
            resultados = cur.fetchall()
            return resultados
    finally:
        conn.close()

def get_resultados_operacoes_normais_por_ativo(user_id):
    """
    Calcula o resultado de todas as operações de compra e venda (trade) finalizadas,
    agrupado por ativo. Utiliza o método do preço médio para apuração.
    """
    # 1. Buscar todas as transações do usuário, ordenadas por data para cálculo correto do preço médio
    query_transacoes = """
        SELECT
            i.codigo,
            t.tipo_transacao,
            t.data,
            t.quantidade,
            t.preco_unitario
        FROM transacoes_investimento t
        JOIN investimentos i ON t.investimento_id = i.investimento_id
        WHERE i.user_id = %s
        ORDER BY i.codigo, t.data;
    """
    transacoes = _execute_query(query_transacoes, (user_id,), fetch='all')

    if not transacoes:
        return []

    # 2. Processar os resultados em Python para lidar com a lógica do preço médio
    resultados = {}         # Dicionário para armazenar o resultado final por ativo
    posicao_atual = {}      # Dicionário para rastrear a quantidade e o custo total de cada ativo em carteira

    for codigo, tipo, data, qtd, preco in transacoes:
        # Inicializa os dicionários se for o primeiro registro do ativo
        if codigo not in posicao_atual:
            posicao_atual[codigo] = {'qtd_total': 0, 'custo_total': 0}
        if codigo not in resultados:
            resultados[codigo] = {'resultado_total': 0, 'vendas_realizadas': 0}

        if tipo == 'compra':
            # Se for compra, adiciona à posição atual
            posicao_atual[codigo]['custo_total'] += qtd * preco
            posicao_atual[codigo]['qtd_total'] += qtd
        
        elif tipo == 'venda':
            # Se for venda, e houver posição no ativo, calcula o lucro/prejuízo
            if posicao_atual[codigo]['qtd_total'] > 0:
                # Calcula o preço médio do ativo no momento da venda
                preco_medio = posicao_atual[codigo]['custo_total'] / posicao_atual[codigo]['qtd_total']
                
                # Calcula o custo da quantidade que está sendo vendida
                custo_da_venda = qtd * preco_medio
                # Calcula o lucro ou prejuízo da operação
                lucro_prejuizo = (qtd * preco) - custo_da_venda

                # Acumula o resultado para o ativo
                resultados[codigo]['resultado_total'] += lucro_prejuizo
                resultados[codigo]['vendas_realizadas'] += 1

                # Abate o valor e a quantidade da posição atual
                posicao_atual[codigo]['custo_total'] -= custo_da_venda
                posicao_atual[codigo]['qtd_total'] -= qtd

    # 3. Formatar a lista de saída
    output = []
    for codigo, data in resultados.items():
        # Apenas inclui no relatório os ativos que tiveram operações de venda
        if data['vendas_realizadas'] > 0:
            output.append((
                codigo,
                data['resultado_total'],
                data['vendas_realizadas']
            ))

    # Ordena a lista do maior para o menor resultado
    output.sort(key=lambda x: x[1], reverse=True)
    
    return output