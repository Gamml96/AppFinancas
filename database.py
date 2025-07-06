# database.py (versão final e completa para Turso)
import streamlit as st
import datetime
from dateutil.relativedelta import relativedelta
import bcrypt
import libsql_client

# --- FUNÇÃO CENTRAL DE CONEXÃO (VERSÃO CORRIGIDA) ---
def _get_turso_client():
    """
    Cria e retorna um cliente de conexão com o Turso usando
    o esquema de URL correto para o ambiente Streamlit.
    """
    try:
        url = st.secrets["turso"]["url"]
        auth_token = st.secrets["turso"]["auth_token"]
        
        # A MÁGICA ESTÁ AQUI:
        # Troca 'https' por 'libsql' para o cliente, mantendo a conexão via HTTPS.
        sync_url = url.replace("https://", "libsql://")

        return libsql_client.create_client(url=sync_url, auth_token=auth_token)

    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados Turso: {e}")
        st.stop()

# -------- Funções Auxiliares (sem conexão com BD) --------
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
    with _get_turso_client() as client:
        client.execute(
            "INSERT INTO users (username, name, email, password, is_admin) VALUES (?, ?, ?, ?, ?)",
            [username, name, email, hashed_password, int(is_admin)]
        )
        user_res = client.execute("SELECT user_id FROM users WHERE username = ?", [username])
        user_id = user_res.rows[0][0]
        ativos_padrao_res = client.execute("SELECT tipo_id, codigo, descricao FROM ativos_padrao")
        if ativos_padrao_res.rows:
            batch = client.batch()
            for tipo_id, codigo, descricao in ativos_padrao_res.rows:
                batch.add_execute("INSERT INTO investimentos (user_id, tipo_id, codigo, descricao) VALUES (?, ?, ?, ?)", [user_id, tipo_id, codigo, descricao])
            client.run_batch(batch)
    st.cache_data.clear()

@st.cache_data
def get_all_users():
    with _get_turso_client() as client:
        rs = client.execute("SELECT user_id, username, name, email, is_admin FROM users")
        return rs.rows

@st.cache_data
def is_user_admin(username):
    with _get_turso_client() as client:
        rs = client.execute("SELECT is_admin FROM users WHERE username = ?", [username])
        return rs.rows[0][0] == 1 if rs.rows else False

@st.cache_data
def get_user_profile(username):
    with _get_turso_client() as client:
        rs = client.execute("SELECT user_id, name, email FROM users WHERE username = ?", [username])
        if not rs.rows: return None
        return {"user_id": rs.rows[0][0], "name": rs.rows[0][1], "email": rs.rows[0][2]}

@st.cache_data
def get_authenticator_credentials():
    with _get_turso_client() as client:
        rs = client.execute("SELECT username, name, password FROM users")
        return {"usernames": {u[0]: {"name": u[1], "password": u[2]} for u in rs.rows}}

def update_user_password(username, new_password):
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    with _get_turso_client() as client:
        client.execute("UPDATE users SET password = ? WHERE username = ?", [hashed_password, username])
    st.cache_data.clear()

def update_user_profile(username, new_name, new_email):
    with _get_turso_client() as client:
        client.execute("UPDATE users SET name = ?, email = ? WHERE username = ?", [new_name, new_email, username])
    st.cache_data.clear()

def update_user_admin_status(user_id, is_admin):
    with _get_turso_client() as client:
        client.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", [int(is_admin), user_id])
    st.cache_data.clear()

def delete_all_user_data(user_id, username):
    with _get_turso_client() as client:
        invest_ids_res = client.execute("SELECT investimento_id FROM investimentos WHERE user_id = ?", [user_id])
        if invest_ids_res.rows:
            delete_trans_batch = client.batch()
            for row in invest_ids_res.rows:
                delete_trans_batch.add_execute("DELETE FROM transacoes_investimento WHERE investimento_id = ?", [row[0]])
            client.run_batch(delete_trans_batch)
        batch = client.batch()
        batch.add_execute("DELETE FROM receitas WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM despesas WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM categorias WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM contas WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM investimentos WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM users WHERE user_id = ?", [user_id])
        client.run_batch(batch)
    st.cache_data.clear()
    
def delete_user_financial_data(user_id):
    with _get_turso_client() as client:
        invest_ids_res = client.execute("SELECT investimento_id FROM investimentos WHERE user_id = ?", [user_id])
        if invest_ids_res.rows:
            delete_trans_batch = client.batch()
            for row in invest_ids_res.rows:
                delete_trans_batch.add_execute("DELETE FROM transacoes_investimento WHERE investimento_id = ?", [row[0]])
            client.run_batch(delete_trans_batch)
        batch = client.batch()
        batch.add_execute("DELETE FROM receitas WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM despesas WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM categorias WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM contas WHERE user_id = ?", [user_id])
        batch.add_execute("DELETE FROM investimentos WHERE user_id = ?", [user_id])
        client.run_batch(batch)
    st.cache_data.clear()

# -------- Contas --------
def insert_conta(user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento):
    with _get_turso_client() as client:
        client.execute("INSERT INTO contas (user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento) VALUES (?, ?, ?, ?, ?, ?)", [user_id, nome, vencimento, data_inicial, float(saldo_inicial), fechamento])
    st.cache_data.clear()

@st.cache_data
def get_contas(user_id):
    with _get_turso_client() as client:
        rs = client.execute("SELECT conta_id, nome, vencimento, data_inicial, saldo_inicial, fechamento FROM contas WHERE user_id = ?", [user_id])
        return rs.rows

def update_conta(conta_id, user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento):
    with _get_turso_client() as client:
        client.execute("UPDATE contas SET nome = ?, vencimento = ?, data_inicial = ?, saldo_inicial = ?, fechamento = ? WHERE conta_id = ? AND user_id = ?", [nome, vencimento, data_inicial, float(saldo_inicial), fechamento, conta_id, user_id])
    st.cache_data.clear()

def delete_conta(conta_id, user_id):
    with _get_turso_client() as client:
        client.execute("DELETE FROM contas WHERE conta_id = ? AND user_id = ?", [conta_id, user_id])
    st.cache_data.clear()

# -------- Categorias --------
def insert_categoria(user_id, tipo, nome):
    with _get_turso_client() as client:
        client.execute("INSERT INTO categorias (user_id, tipo, nome) VALUES (?, ?, ?)", [user_id, tipo, nome])
    st.cache_data.clear()

@st.cache_data
def get_categorias(user_id, tipo):
    with _get_turso_client() as client:
        rs = client.execute("SELECT categoria_id, nome FROM categorias WHERE user_id = ? AND tipo = ?", [user_id, tipo])
        return rs.rows

def update_categoria(categoria_id, user_id, nome):
     with _get_turso_client() as client:
        client.execute("UPDATE categorias SET nome = ? WHERE categoria_id = ? AND user_id = ?", [nome, categoria_id, user_id])
     st.cache_data.clear()

def delete_categoria(categoria_id, user_id):
    with _get_turso_client() as client:
        client.execute("DELETE FROM categorias WHERE categoria_id = ? AND user_id = ?", [categoria_id, user_id])
    st.cache_data.clear()
    
def get_or_create_categoria_despesa(user_id, nome_categoria):
    nome_cat_clean = nome_categoria.strip().capitalize()
    with _get_turso_client() as client:
        rs = client.execute("SELECT nome FROM categorias WHERE user_id = ? AND lower(nome) = ? AND tipo = 'despesa'", [user_id, nome_cat_clean.lower()])
        if rs.rows: return rs.rows[0][0]
        client.execute("INSERT INTO categorias (user_id, tipo, nome) VALUES (?, 'despesa', ?)", [user_id, nome_cat_clean])
    st.cache_data.clear()
    return nome_cat_clean

def get_or_create_categoria_receita(user_id, nome_categoria):
    nome_cat_clean = nome_categoria.strip().capitalize()
    with _get_turso_client() as client:
        rs = client.execute("SELECT nome FROM categorias WHERE user_id = ? AND lower(nome) = ? AND tipo = 'receita'", [user_id, nome_cat_clean.lower()])
        if rs.rows: return rs.rows[0][0]
        client.execute("INSERT INTO categorias (user_id, tipo, nome) VALUES (?, 'receita', ?)", [user_id, nome_cat_clean])
    st.cache_data.clear()
    return nome_cat_clean

# -------- Receitas --------
def insert_receita(user_id, conta_id, data, valor, categoria, descricao):
    with _get_turso_client() as client:
        client.execute("INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao) VALUES (?, ?, ?, ?, ?, ?)", [user_id, conta_id, data, float(valor), categoria, descricao])
    st.cache_data.clear()

@st.cache_data
def get_receitas(user_id):
    with _get_turso_client() as client:
        rs = client.execute("SELECT receita_id, conta_id, data, valor, categoria, descricao FROM receitas WHERE user_id = ?", [user_id])
        return rs.rows

def update_receita(receita_id, user_id, conta_id, data, valor, categoria, descricao):
    with _get_turso_client() as client:
        client.execute("UPDATE receitas SET conta_id = ?, data = ?, valor = ?, categoria = ?, descricao = ? WHERE receita_id = ? AND user_id = ?", [conta_id, data, float(valor), categoria, descricao, receita_id, user_id])
    st.cache_data.clear()

def delete_receita(receita_id, user_id):
    with _get_turso_client() as client:
        client.execute("DELETE FROM receitas WHERE receita_id = ? AND user_id = ?", [receita_id, user_id])
    st.cache_data.clear()

# -------- Despesas --------
def insert_despesa(user_id, conta_id, data_compra_str, valor, categoria, tipo_pagamento, parcelas, descricao):
    valor_total = float(valor)
    data_compra_obj = datetime.datetime.strptime(data_compra_str, "%Y-%m-%d").date()
    valor_parcela_padrao = round(valor_total / parcelas, 2)
    diferenca = round(valor_total - (valor_parcela_padrao * parcelas), 2)
    valor_primeira_parcela = valor_parcela_padrao + diferenca
    grupo_id = int(datetime.datetime.now().timestamp() * 1000)
    
    with _get_turso_client() as client:
        if tipo_pagamento == 'crédito':
            conta_res = client.execute("SELECT vencimento, fechamento FROM contas WHERE conta_id = ? AND user_id = ?", [conta_id, user_id])
            if not conta_res.rows: raise ValueError("Conta de crédito não encontrada.")
            dia_vencimento, dias_fechamento = conta_res.rows[0]
            primeiro_vencimento = _calcular_vencimento_credito(data_compra_obj, dia_vencimento, dias_fechamento)
        else: # débito
            primeiro_vencimento = data_compra_obj

        batch = client.batch()
        for i in range(parcelas):
            valor_a_inserir = valor_primeira_parcela if i == 0 else valor_parcela_padrao
            vencimento_parcela = primeiro_vencimento + relativedelta(months=i)
            descricao_parcela = f"{descricao} ({i+1}/{parcelas})" if parcelas > 1 else descricao
            batch.add_execute("INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, parcela_grupo_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [user_id, conta_id, data_compra_str, vencimento_parcela.isoformat(), valor_a_inserir, categoria, tipo_pagamento, i + 1, descricao_parcela, grupo_id])
        client.run_batch(batch)
    st.cache_data.clear()

@st.cache_data
def get_despesas(user_id):
     with _get_turso_client() as client:
        rs = client.execute("SELECT despesa_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao FROM despesas WHERE user_id = ?", [user_id])
        return rs.rows

# -------- Investimentos --------
@st.cache_data
def get_tipos_investimento():
    with _get_turso_client() as client:
        rs = client.execute("SELECT tipo_id, nome FROM tipos_investimento ORDER BY nome")
        return rs.rows

def add_investimento(user_id, tipo_id, codigo, descricao):
    with _get_turso_client() as client:
        rs = client.execute("SELECT investimento_id FROM investimentos WHERE user_id = ? AND lower(codigo) = ?", [user_id, codigo.lower()])
        if rs.rows: raise ValueError("Este ativo já está cadastrado.")
        client.execute("INSERT INTO investimentos (user_id, tipo_id, codigo, descricao) VALUES (?, ?, ?, ?)", [user_id, tipo_id, codigo.upper(), descricao])
    st.cache_data.clear()

def add_transacao_investimento(investimento_id, tipo_transacao, data, quantidade, preco_unitario):
    with _get_turso_client() as client:
        client.execute("INSERT INTO transacoes_investimento (investimento_id, tipo_transacao, data, quantidade, preco_unitario) VALUES (?, ?, ?, ?, ?)", [investimento_id, tipo_transacao, data, quantidade, preco_unitario])
    st.cache_data.clear()

@st.cache_data
def get_portfolio_consolidado(user_id):
    with _get_turso_client() as client:
        query = "SELECT i.codigo, i.descricao, ti.nome as tipo, SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE -t.quantidade END) as quantidade_total, SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade * t.preco_unitario ELSE 0 END) / SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE 0 END) as preco_medio_compra FROM investimentos i JOIN transacoes_investimento t ON i.investimento_id = t.investimento_id JOIN tipos_investimento ti ON i.tipo_id = ti.tipo_id WHERE i.user_id = ? GROUP BY i.investimento_id HAVING quantidade_total > 0 ORDER BY i.codigo"
        rs = client.execute(query, [user_id])
        return rs.rows

@st.cache_data
def get_investimentos_usuario(user_id):
    with _get_turso_client() as client:
        rs = client.execute("SELECT investimento_id, codigo FROM investimentos WHERE user_id = ? ORDER BY codigo", [user_id])
        return rs.rows

def get_or_create_investimento(user_id, codigo, tipo_nome, descricao=""):
    codigo_upper = codigo.strip().upper()
    with _get_turso_client() as client:
        rs = client.execute("SELECT investimento_id FROM investimentos WHERE user_id = ? AND codigo = ?", [user_id, codigo_upper])
        if rs.rows: return rs.rows[0][0]
        tipo_res = client.execute("SELECT tipo_id FROM tipos_investimento WHERE lower(nome) = ?", [tipo_nome.lower()])
        if not tipo_res.rows: raise ValueError(f"O tipo de ativo '{tipo_nome}' não é válido.")
        tipo_id = tipo_res.rows[0][0]
        client.execute("INSERT INTO investimentos (user_id, tipo_id, codigo, descricao) VALUES (?, ?, ?, ?)", [user_id, tipo_id, codigo_upper, descricao.strip()])
        id_res = client.execute("SELECT investimento_id FROM investimentos WHERE user_id = ? AND codigo = ?", [user_id, codigo_upper])
    st.cache_data.clear()
    return id_res.rows[0][0]

@st.cache_data
def get_all_transacoes(user_id):
    with _get_turso_client() as client:
        query = "SELECT t.transacao_id, i.codigo, t.tipo_transacao, t.data, t.quantidade, t.preco_unitario FROM transacoes_investimento t JOIN investimentos i ON t.investimento_id = i.investimento_id WHERE i.user_id = ? ORDER BY t.data DESC"
        rs = client.execute(query, [user_id])
        return rs.rows

def update_transacao_investimento(transacao_id, data, quantidade, preco_unitario):
    with _get_turso_client() as client:
        client.execute("UPDATE transacoes_investimento SET data = ?, quantidade = ?, preco_unitario = ? WHERE transacao_id = ?", [data, quantidade, preco_unitario, transacao_id])
    st.cache_data.clear()

def delete_transacao_investimento(transacao_id):
    with _get_turso_client() as client:
        client.execute("DELETE FROM transacoes_investimento WHERE transacao_id = ?", [transacao_id])
    st.cache_data.clear()

# -------- Relatórios e Consolidações --------
@st.cache_data
def get_proximos_lancamentos(user_id, dias_futuros=3):
    lancamentos = []
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=dias_futuros)
    with _get_turso_client() as client:
        receitas_res = client.execute("SELECT data, descricao, valor, 'receita' as tipo FROM receitas WHERE user_id = ? AND data BETWEEN ? AND ?", [user_id, today.isoformat(), end_date.isoformat()])
        lancamentos.extend(receitas_res.rows)
        despesas_res = client.execute("SELECT data_vencimento, descricao, valor, 'despesa' as tipo FROM despesas WHERE user_id = ? AND data_vencimento BETWEEN ? AND ?", [user_id, today.isoformat(), end_date.isoformat()])
        lancamentos.extend(despesas_res.rows)
    lancamentos.sort(key=lambda x: x[0])
    return lancamentos

@st.cache_data
def get_despesas_por_categoria(user_id, dt_start, dt_end):
    with _get_turso_client() as client:
        query = "SELECT categoria, SUM(valor) FROM despesas WHERE user_id = ? AND data_vencimento BETWEEN ? AND ? GROUP BY categoria ORDER BY SUM(valor) DESC"
        rs = client.execute(query, [user_id, dt_start, dt_end])
        return rs.rows

@st.cache_data
def get_total_receitas_mensal(user_id):
    with _get_turso_client() as client:
        query = "SELECT strftime('%Y-%m', data) as mes, SUM(valor) FROM receitas WHERE user_id = ? GROUP BY mes ORDER BY mes"
        rs = client.execute(query, [user_id])
        return rs.rows

@st.cache_data
def get_total_despesas_mensal(user_id):
    with _get_turso_client() as client:
        query = "SELECT strftime('%Y-%m', data_vencimento) as mes, SUM(valor) FROM despesas WHERE user_id = ? GROUP BY mes ORDER BY mes"
        rs = client.execute(query, [user_id])
        return rs.rows

@st.cache_data
def get_fatura_cartao(user_id, conta_id, mes, ano):
    mes_ano_str = f"{ano:04d}-{mes:02d}"
    with _get_turso_client() as client:
        query = "SELECT data_compra, descricao, valor FROM despesas WHERE user_id = ? AND conta_id = ? AND tipo_pagamento = 'crédito' AND strftime('%Y-%m', data_vencimento) = ? ORDER BY data_compra"
        rs = client.execute(query, [user_id, conta_id, mes_ano_str])
        return rs.rows

@st.cache_data
def get_transacoes_consolidadas(user_id):
    transacoes = []
    with _get_turso_client() as client:
        receitas_res = client.execute("SELECT data, descricao, valor FROM receitas WHERE user_id = ?", [user_id])
        for data, desc, val in receitas_res.rows: transacoes.append((data, desc, val))
        despesas_res = client.execute("SELECT data_vencimento, descricao, valor FROM despesas WHERE user_id = ?", [user_id])
        for data, desc, val in despesas_res.rows: transacoes.append((data, desc, -val))
        contas_res = client.execute("SELECT data_inicial, nome, saldo_inicial FROM contas WHERE user_id = ?", [user_id])
        for data, nome, saldo in contas_res.rows:
            if data and saldo > 0: transacoes.append((data, f"Saldo Inicial - {nome}", saldo))
    return transacoes
