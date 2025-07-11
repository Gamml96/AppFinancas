# database.py (versão final, completa e estável)

import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import bcrypt
import psycopg2
import psycopg2.extras
import os
import time

# --- FUNÇÃO CENTRAL DE CONEXÃO ---
def _get_db_connection():
    """Cria uma conexão com o banco de dados PostgreSQL."""
    try:
        # Garante que as secrets do Streamlit estão sendo usadas para a conexão
        conn = psycopg2.connect(**st.secrets["postgres"])
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        st.stop()

# --- FUNÇÃO CENTRAL DE EXECUÇÃO DE QUERIES (ESTÁVEL) ---
def _execute_query(query, params=None, fetch=None, commit=False, executemany_params=None):
    """
    Executa uma query no banco de dados e retorna apenas o resultado da busca (fetch).
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
        conn.rollback()
        # Propaga o erro para a interface poder tratar
        raise e
    finally:
        conn.close()
    
    return result

# --- FUNÇÕES AUXILIARES ---
RECORRENCIA_MAP = {
    "Diária": relativedelta(days=1), "Semanal": relativedelta(weeks=1),
    "Mensal": relativedelta(months=1), "Bimestral": relativedelta(months=2),
    "Trimestral": relativedelta(months=3), "Semestral": relativedelta(months=6),
    "Anual": relativedelta(years=1),
}

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


# -------- USUÁRIOS --------
@st.cache_data
def get_authenticator_credentials():
    """Busca credenciais para o autenticador."""
    try:
        users_data = _execute_query("SELECT username, name, password FROM users", fetch='all')
        if not users_data: return {"usernames": {}}
        credentials = {"usernames": {}}
        for user_tuple in users_data:
            username, name, password = user_tuple
            if username and str(username).strip():
                credentials["usernames"][username] = {"name": name, "password": password}
        return credentials
    except Exception as e:
        st.error(f"Erro ao carregar credenciais: {e}")
        return {"usernames": {}}

@st.cache_data
def get_user_profile(username):
    """Busca o perfil do usuário."""
    user = _execute_query("SELECT user_id, name, email FROM users WHERE username = %s", (username,), fetch='one')
    return {"user_id": user[0], "name": user[1], "email": user[2]} if user else None

def add_user(username, name, email, hashed_password, is_admin=False):
    """Adiciona um novo usuário."""
    _execute_query("INSERT INTO users (username, name, email, password, is_admin) VALUES (%s, %s, %s, %s, %s)",
                   (username, name, email, hashed_password, is_admin), commit=True)
    st.cache_data.clear()

def update_user_password(username, new_password):
    """Atualiza a senha de um usuário."""
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    _execute_query("UPDATE users SET password = %s WHERE username = %s", (hashed_password, username), commit=True)
    st.cache_data.clear()

def update_user_profile(username, new_name, new_email):
    """Atualiza o perfil de um usuário."""
    _execute_query("UPDATE users SET name = %s, email = %s WHERE username = %s", (new_name, new_email, username), commit=True)
    st.cache_data.clear()

@st.cache_data
def get_all_users():
    """Busca todos os usuários para o painel de admin."""
    return _execute_query("SELECT user_id, username, name, email, is_admin FROM users", fetch='all')

@st.cache_data
def is_user_admin(username):
    """Verifica se um usuário é administrador."""
    user = _execute_query("SELECT is_admin FROM users WHERE username = %s", (username,), fetch='one')
    return user[0] if user else False

def update_user_admin_status(user_id, is_admin):
    """Atualiza o status de admin de um usuário."""
    _execute_query("UPDATE users SET is_admin = %s WHERE user_id = %s", (is_admin, user_id), commit=True)
    st.cache_data.clear()

def delete_user_financial_data(user_id):
    """Deleta todos os dados financeiros de um usuário, mas mantém o perfil."""
    queries = [
        "DELETE FROM receitas WHERE user_id = %s",
        "DELETE FROM despesas WHERE user_id = %s",
        "DELETE FROM categorias WHERE user_id = %s",
        "DELETE FROM investimentos WHERE user_id = %s", # ON DELETE CASCADE cuidará das transações
        "DELETE FROM contas WHERE user_id = %s"
    ]
    for query in queries:
        _execute_query(query, (user_id,), commit=True)
    st.cache_data.clear()

def delete_all_user_data(user_id):
    """Deleta um usuário e todos os seus dados (via ON DELETE CASCADE no DB)."""
    _execute_query("DELETE FROM users WHERE user_id = %s", (user_id,), commit=True)
    st.cache_data.clear()


# -------- CONTAS --------
@st.cache_data
def get_contas(user_id):
    """Busca todas as contas de um usuário."""
    return _execute_query("SELECT conta_id, nome, vencimento, data_inicial, saldo_inicial, fechamento FROM contas WHERE user_id = %s ORDER BY nome", (user_id,), fetch='all')

def insert_conta(user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento):
    """Insere uma nova conta."""
    query = "INSERT INTO contas (user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento) VALUES (%s, %s, %s, %s, %s, %s)"
    params = (user_id, nome, vencimento, data_inicial, float(saldo_inicial), fechamento)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def update_conta(conta_id, user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento):
    """Atualiza uma conta existente."""
    query = "UPDATE contas SET nome = %s, vencimento = %s, data_inicial = %s, saldo_inicial = %s, fechamento = %s WHERE conta_id = %s AND user_id = %s"
    params = (nome, vencimento, data_inicial, float(saldo_inicial), fechamento, conta_id, user_id)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_conta(conta_id, user_id):
    """Deleta uma conta."""
    _execute_query("DELETE FROM contas WHERE conta_id = %s AND user_id = %s", (conta_id, user_id), commit=True)
    st.cache_data.clear()


# -------- CATEGORIAS --------
@st.cache_data
def get_categorias(user_id, tipo):
    """Busca categorias por tipo (receita ou despesa)."""
    return _execute_query("SELECT categoria_id, nome FROM categorias WHERE user_id = %s AND tipo = %s ORDER BY nome", (user_id, tipo), fetch='all')

def insert_categoria(user_id, tipo, nome):
    """Insere uma nova categoria, evitando duplicatas."""
    _execute_query("INSERT INTO categorias (user_id, tipo, nome) VALUES (%s, %s, %s) ON CONFLICT (user_id, tipo, nome) DO NOTHING",
                   (user_id, tipo, nome), commit=True)
    st.cache_data.clear()

def update_categoria(categoria_id, user_id, nome):
    """Atualiza o nome de uma categoria."""
    _execute_query("UPDATE categorias SET nome = %s WHERE categoria_id = %s AND user_id = %s", (nome, categoria_id, user_id), commit=True)
    st.cache_data.clear()

def delete_categoria(categoria_id, user_id):
    """Deleta uma categoria."""
    _execute_query("DELETE FROM categorias WHERE categoria_id = %s AND user_id = %s", (categoria_id, user_id), commit=True)
    st.cache_data.clear()

def get_or_create_categoria(user_id, nome_categoria, tipo):
    """Busca uma categoria pelo nome; se não existir, a cria."""
    nome_cat_clean = nome_categoria.strip().capitalize()
    query_select = "SELECT nome FROM categorias WHERE user_id = %s AND lower(nome) = %s AND tipo = %s"
    result = _execute_query(query_select, (user_id, nome_cat_clean.lower(), tipo), fetch='one')
    if result:
        return result[0]
    else:
        insert_categoria(user_id, tipo, nome_cat_clean)
        return nome_cat_clean

def get_or_create_categoria_despesa(user_id, nome_categoria):
    return get_or_create_categoria(user_id, nome_categoria, 'despesa')

def get_or_create_categoria_receita(user_id, nome_categoria):
    return get_or_create_categoria(user_id, nome_categoria, 'receita')


# -------- RECEITAS E DESPESAS --------
def insert_receita(user_id, conta_id, data_str, valor, categoria, descricao, recorrencia_freq=None, recorrencia_vezes=1):
    """Insere receitas, lidando com recorrências."""
    grupo_id = int(time.time() * 1000)
    dados_para_inserir = []
    data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d").date()

    if recorrencia_freq and recorrencia_vezes > 1:
        delta = RECORRENCIA_MAP.get(recorrencia_freq, relativedelta(months=1))
        for i in range(recorrencia_vezes):
            data_lancamento = data_obj + (delta * i)
            desc_recorrencia = f"{descricao} ({i+1}/{recorrencia_vezes})"
            dados_para_inserir.append((user_id, conta_id, data_lancamento.isoformat(), valor, categoria, desc_recorrencia, recorrencia_freq, grupo_id))
    else:
        dados_para_inserir.append((user_id, conta_id, data_str, valor, categoria, descricao, None, None))
    
    _execute_query("INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao, recorrencia, recorrencia_grupo_id) VALUES %s",
                   executemany_params=dados_para_inserir, commit=True)
    st.cache_data.clear()

def insert_despesa(user_id, conta_id, data_compra_str, valor, categoria, tipo_pagamento, parcelas, descricao, recorrencia_freq=None, recorrencia_vezes=1):
    """Insere despesas, lidando com parcelas e recorrências."""
    grupo_id = int(time.time() * 1000)
    dados_para_inserir = []
    data_compra_obj = datetime.datetime.strptime(data_compra_str, "%Y-%m-%d").date()

    is_recorrencia = recorrencia_freq and recorrencia_vezes > 1
    loop_count = recorrencia_vezes if is_recorrencia else parcelas

    dia_vencimento, dias_fechamento = None, None
    if tipo_pagamento == 'crédito':
        contas = get_contas(user_id)
        conta_info = next((c for c in contas if c[0] == conta_id), None)
        if conta_info: dia_vencimento, dias_fechamento = conta_info[2], conta_info[5]

    for i in range(loop_count):
        if is_recorrencia:
            delta = RECORRENCIA_MAP.get(recorrencia_freq)
            data_compra_iteracao = data_compra_obj + (delta * i)
            valor_iteracao = float(valor)
            descricao_iteracao = f"{descricao} ({i+1}/{loop_count})"
            num_parcela = 1
            vencimento_iteracao = _calcular_vencimento_credito(data_compra_iteracao, dia_vencimento, dias_fechamento) if tipo_pagamento == 'crédito' else data_compra_iteracao
        else: # Lógica de Parcelamento
            data_compra_iteracao = data_compra_obj
            valor_parcela_padrao = round(float(valor) / parcelas, 2)
            valor_iteracao = valor_parcela_padrao + round(float(valor) - (valor_parcela_padrao * parcelas), 2) if i == 0 else valor_parcela_padrao
            descricao_iteracao = f"{descricao} ({i+1}/{loop_count})" if loop_count > 1 else descricao
            num_parcela = i + 1
            primeiro_vencimento = _calcular_vencimento_credito(data_compra_obj, dia_vencimento, dias_fechamento) if tipo_pagamento == 'crédito' else data_compra_obj
            vencimento_iteracao = primeiro_vencimento + relativedelta(months=i)

        dados_para_inserir.append((user_id, conta_id, data_compra_iteracao.isoformat(), vencimento_iteracao.isoformat(),
                                   valor_iteracao, categoria, tipo_pagamento, num_parcela, descricao_iteracao,
                                   recorrencia_freq if is_recorrencia else None, grupo_id if loop_count > 1 else None))

    _execute_query("INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, recorrencia, parcela_grupo_id) VALUES %s",
                   executemany_params=dados_para_inserir, commit=True)
    st.cache_data.clear()

# -------- Funções de Relatórios e Consultas --------
@st.cache_data
def get_receitas(user_id):
    """Busca todas as receitas de um usuário."""
    return _execute_query("SELECT receita_id, user_id, conta_id, data, valor, categoria, descricao FROM receitas WHERE user_id = %s ORDER BY data DESC", (user_id,), fetch='all')

@st.cache_data
def get_despesas(user_id):
    """Busca todas as despesas de um usuário."""
    return _execute_query("SELECT despesa_id, user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, recorrencia, parcela_grupo_id FROM despesas WHERE user_id = %s ORDER BY data_vencimento DESC", (user_id,), fetch='all')

# -------- Funções de Atualização e Exclusão --------
def update_receita(receita_id, user_id, conta_id, data, valor, categoria, descricao):
    """Atualiza uma receita."""
    query = "UPDATE receitas SET conta_id = %s, data = %s, valor = %s, categoria = %s, descricao = %s WHERE receita_id = %s AND user_id = %s"
    _execute_query(query, (conta_id, data, float(valor), categoria, descricao, receita_id, user_id), commit=True)
    st.cache_data.clear()

def delete_receita(receita_id, user_id):
    """Deleta uma receita."""
    _execute_query("DELETE FROM receitas WHERE receita_id = %s AND user_id = %s", (receita_id, user_id), commit=True)
    st.cache_data.clear()

def update_despesa(despesa_id, user_id, conta_id, data_compra, data_vencimento, valor, categoria, descricao):
    """Atualiza uma despesa."""
    query = "UPDATE despesas SET conta_id = %s, data_compra = %s, data_vencimento = %s, valor = %s, categoria = %s, descricao = %s WHERE despesa_id = %s AND user_id = %s"
    _execute_query(query, (conta_id, data_compra, data_vencimento, float(valor), categoria, descricao, despesa_id, user_id), commit=True)
    st.cache_data.clear()

def delete_despesa(despesa_id, user_id):
    """Deleta uma despesa."""
    _execute_query("DELETE FROM despesas WHERE despesa_id = %s AND user_id = %s", (despesa_id, user_id), commit=True)
    st.cache_data.clear()

# -------- Funções de Lote para Importação --------
def batch_insert_receitas(user_id, dados_receitas):
    """Insere uma lista de receitas em uma única transação."""
    if not dados_receitas: return
    dados_com_user_id = [(user_id,) + tupla for tupla in dados_receitas]
    _execute_query("INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao) VALUES %s",
                   executemany_params=dados_com_user_id, commit=True)
    st.cache_data.clear()

def batch_insert_despesas(user_id, dados_despesas):
    """Insere uma lista de despesas em uma única transação."""
    if not dados_despesas: return
    dados_com_user_id = [(user_id,) + tupla for tupla in dados_despesas]
    _execute_query("INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, parcela_grupo_id) VALUES %s",
                   executemany_params=dados_com_user_id, commit=True)
    st.cache_data.clear()

def batch_insert_transacoes_investimento(dados_transacoes):
    """Insere uma lista de transações de investimento."""
    if not dados_transacoes: return
    _execute_query("INSERT INTO transacoes_investimento (investimento_id, tipo_transacao, data, quantidade, preco_unitario) VALUES %s",
                   executemany_params=dados_transacoes, commit=True)
    st.cache_data.clear()
    
# -------- Funções de Investimentos --------
@st.cache_data
def get_all_ativos_usuario(user_id):
    """Busca todos os ativos cadastrados por um usuário."""
    query = """
        SELECT i.investimento_id, i.codigo, i.descricao, ti.nome as tipo, 
               i.indexador, i.taxa_percentual, i.data_vencimento
        FROM investimentos i
        JOIN tipos_investimento ti ON i.tipo_id = ti.tipo_id
        WHERE i.user_id = %s ORDER BY i.codigo
    """
    return _execute_query(query, (user_id,), fetch='all')

def add_investimento(user_id, tipo_id, codigo, descricao, indexador, taxa_percentual, data_vencimento):
    """Insere ou atualiza um ativo (UPSERT)."""
    data_vencimento_str = data_vencimento.isoformat() if data_vencimento else None
    query = """
        INSERT INTO investimentos (user_id, tipo_id, codigo, descricao, indexador, taxa_percentual, data_vencimento) 
        VALUES (%s, %s, %s, %s, %s, %s, %s) 
        ON CONFLICT (user_id, codigo) 
        DO UPDATE SET
            descricao = EXCLUDED.descricao, tipo_id = EXCLUDED.tipo_id, indexador = EXCLUDED.indexador,
            taxa_percentual = EXCLUDED.taxa_percentual, data_vencimento = EXCLUDED.data_vencimento;
    """
    params = (user_id, tipo_id, codigo.upper(), descricao, indexador, taxa_percentual, data_vencimento_str)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def add_transacao_investimento(investimento_id, tipo_transacao, data, quantidade, preco_unitario):
    """Adiciona uma transação de investimento."""
    query = "INSERT INTO transacoes_investimento (investimento_id, tipo_transacao, data, quantidade, preco_unitario) VALUES (%s, %s, %s, %s, %s)"
    _execute_query(query, (investimento_id, tipo_transacao, data, quantidade, preco_unitario), commit=True)
    st.cache_data.clear()

def update_ativo(investimento_id, user_id, descricao, indexador, taxa_percentual, data_vencimento):
    """Atualiza os dados de um ativo."""
    data_vencimento_str = data_vencimento.isoformat() if data_vencimento else None
    query = "UPDATE investimentos SET descricao = %s, indexador = %s, taxa_percentual = %s, data_vencimento = %s WHERE investimento_id = %s AND user_id = %s"
    params = (descricao, indexador, taxa_percentual, data_vencimento_str, investimento_id, user_id)
    _execute_query(query, params, commit=True)
    st.cache_data.clear()

def delete_ativo(investimento_id, user_id):
    """Deleta um ativo. Depende da regra ON DELETE CASCADE no DB."""
    _execute_query("DELETE FROM investimentos WHERE investimento_id = %s AND user_id = %s", (investimento_id, user_id), commit=True)
    st.cache_data.clear()
    
# --- Funções para Módulo de Opções ---
def add_estrategia_opcoes(user_id, ativo_objeto, nome_estrategia, data_montagem, pernas):
    """Adiciona uma estratégia de opções completa."""
    custo_total = sum(p['preco_pago'] * p['quantidade'] for p in pernas)
    conn = _get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO estrategias_opcoes (user_id, ativo_objeto, nome_estrategia, data_montagem, custo_montagem) VALUES (%s, %s, %s, %s, %s) RETURNING estrategia_id",
                        (user_id, ativo_objeto, nome_estrategia, data_montagem, custo_total))
            estrategia_id = cur.fetchone()[0]
            
            dados_pernas = [(estrategia_id, p['codigo_opcao'], p['tipo_opcao'], p['tipo_operacao'], p['quantidade'], p['strike'], p['preco_pago'], p['data_vencimento']) for p in pernas]
            
            psycopg2.extras.execute_values(cur, "INSERT INTO pernas_estrategia (estrategia_id, codigo_opcao, tipo_opcao, tipo_operacao, quantidade, strike, preco_pago, data_vencimento) VALUES %s", dados_pernas)
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    st.cache_data.clear()

@st.cache_data
def get_estrategias_com_pernas(user_id):
    """Busca todas as estratégias e suas pernas."""
    query_estrategias = "SELECT estrategia_id, ativo_objeto, nome_estrategia, data_montagem, status, custo_montagem FROM estrategias_opcoes WHERE user_id = %s ORDER BY data_montagem DESC"
    estrategias = _execute_query(query_estrategias, (user_id,), fetch='all')

    if not estrategias: return {}

    query_pernas = "SELECT p.estrategia_id, p.codigo_opcao, p.tipo_opcao, p.tipo_operacao, p.quantidade, p.strike, p.preco_pago, p.data_vencimento FROM pernas_estrategia p JOIN estrategias_opcoes e ON p.estrategia_id = e.estrategia_id WHERE e.user_id = %s"
    pernas = _execute_query(query_pernas, (user_id,), fetch='all')
    df_pernas = pd.DataFrame(pernas, columns=['estrategia_id', 'codigo_opcao', 'tipo_opcao', 'tipo_operacao', 'quantidade', 'strike', 'preco_pago', 'data_vencimento'])

    resultado = {}
    for e in estrategias:
        estrategia_id = e[0]
        resultado[estrategia_id] = {'info': e, 'pernas': df_pernas[df_pernas['estrategia_id'] == estrategia_id].to_dict('records')}
        
    return resultado

# --- Demais Funções ---
@st.cache_data
def get_orcamentos(user_id):
    return _execute_query("SELECT categoria_nome, limite_mensal FROM orcamentos WHERE user_id = %s", (user_id,), fetch='all')

def set_orcamento(user_id, categoria_nome, limite):
    query = """
        INSERT INTO orcamentos (user_id, categoria_nome, limite_mensal) VALUES (%s, %s, %s)
        ON CONFLICT (user_id, categoria_nome) DO UPDATE SET limite_mensal = EXCLUDED.limite_mensal;
    """
    _execute_query(query, (user_id, categoria_nome, float(limite)), commit=True)
    st.cache_data.clear()
    
@st.cache_data
def get_fatura_cartao(user_id, conta_id, mes, ano):
    mes_ano_str = f"{ano:04d}-{mes:02d}"
    query = "SELECT data_compra, descricao, valor FROM despesas WHERE user_id = %s AND conta_id = %s AND tipo_pagamento = 'crédito' AND TO_CHAR(data_vencimento, 'YYYY-MM') = %s ORDER BY data_compra"
    return _execute_query(query, (user_id, conta_id, mes_ano_str), fetch='all')

# E qualquer outra função que você tenha adicionado e que eu possa ter perdido...