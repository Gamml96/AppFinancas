import sqlite3
from streamlit_authenticator.utilities.hasher import Hasher
import datetime
from dateutil.relativedelta import relativedelta
import streamlit as st # Importação necessária para o cache

DB_PATH = "app.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL, name TEXT NOT NULL, email TEXT,
                password TEXT NOT NULL, is_admin INTEGER DEFAULT 0 )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contas (
                conta_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                nome TEXT NOT NULL, data_inicial TEXT, saldo_inicial REAL,
                vencimento INTEGER, fechamento INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id) )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                categoria_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('receita', 'despesa')),
                nome TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(user_id) )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receitas (
                receita_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                conta_id INTEGER NOT NULL, data TEXT, valor REAL, categoria TEXT,
                descricao TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(conta_id) REFERENCES contas(conta_id) )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS despesas (
                despesa_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                conta_id INTEGER NOT NULL, data_compra TEXT NOT NULL, data_vencimento TEXT NOT NULL,
                valor REAL NOT NULL, categoria TEXT,
                tipo_pagamento TEXT NOT NULL CHECK(tipo_pagamento IN ('crédito', 'débito')),
                parcelas INTEGER, descricao TEXT, recorrencia TEXT, parcela_grupo_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(conta_id) REFERENCES contas(conta_id) )
        """)
        # Tabela para os tipos de investimento
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tipos_investimento (
                tipo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL
            )
        """)
        
        # Tabela para os ativos (ex: PETR4, BTC, MXRF11)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investimentos (
                investimento_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tipo_id INTEGER NOT NULL,
                codigo TEXT NOT NULL,
                descricao TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(tipo_id) REFERENCES tipos_investimento(tipo_id)
            )
        """)
        
        # Tabela para registrar cada compra e venda
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacoes_investimento (
                transacao_id INTEGER PRIMARY KEY AUTOINCREMENT,
                investimento_id INTEGER NOT NULL,
                tipo_transacao TEXT NOT NULL CHECK(tipo_transacao IN ('compra', 'venda')),
                data TEXT NOT NULL,
                quantidade REAL NOT NULL,
                preco_unitario REAL NOT NULL,
                FOREIGN KEY(investimento_id) REFERENCES investimentos(investimento_id)
            )
        """)

        # Insere os tipos de investimento padrão se a tabela estiver vazia
        cursor.execute("SELECT count(*) FROM tipos_investimento")
        if cursor.fetchone()[0] == 0:
            tipos = [('Ação BR',), ('Ação EUA',), ('FII',), ('Criptomoeda',), ('Renda Fixa',)]
            cursor.executemany("INSERT INTO tipos_investimento (nome) VALUES (?)", tipos)

        # Nova tabela para armazenar a lista de ativos padrão
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ativos_padrao (
                ativo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_id INTEGER NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                descricao TEXT,
                FOREIGN KEY(tipo_id) REFERENCES tipos_investimento(tipo_id)
            )
        """)
        # Insere os ativos padrão se a tabela estiver vazia
        cursor.execute("SELECT count(*) FROM ativos_padrao")
        if cursor.fetchone()[0] == 0:
            # Dicionário para mapear nome do tipo para tipo_id
            cursor.execute("SELECT nome, tipo_id FROM tipos_investimento")
            tipos_map = {nome: tipo_id for nome, tipo_id in cursor.fetchall()}
            
            ativos = [
                # Ações BR
                (tipos_map['Ação BR'], 'PETR4', 'Petrobras PN'),
                (tipos_map['Ação BR'], 'VALE3', 'Vale ON'),
                (tipos_map['Ação BR'], 'ITUB4', 'Itaú Unibanco PN'),
                (tipos_map['Ação BR'], 'BBDC4', 'Bradesco PN'),
                (tipos_map['Ação BR'], 'MGLU3', 'Magazine Luiza ON'),
                (tipos_map['Ação BR'], 'WEGE3', 'WEG ON'),
                # FIIs
                (tipos_map['FII'], 'MXRF11', 'Maxi Renda FII'),
                (tipos_map['FII'], 'HGLG11', 'CSHG Logística FII'),
                (tipos_map['FII'], 'KNCR11', 'Kinea Rendimentos Imobiliários FII'),
                # Criptomoedas
                (tipos_map['Criptomoeda'], 'BTC-USD', 'Bitcoin'),
                (tipos_map['Criptomoeda'], 'ETH-USD', 'Ethereum'),
                # Ações EUA
                (tipos_map['Ação EUA'], 'AAPL', 'Apple Inc.'),
                (tipos_map['Ação EUA'], 'MSFT', 'Microsoft Corporation'),
                (tipos_map['Ação EUA'], 'GOOGL', 'Alphabet Inc. (Google)'),
                (tipos_map['Ação EUA'], 'TSLA', 'Tesla, Inc.'),
            ]
            cursor.executemany("INSERT INTO ativos_padrao (tipo_id, codigo, descricao) VALUES (?, ?, ?)", ativos)

# -------- Usuários --------

       
def delete_user_financial_data(user_id):
    """
    Exclui TODOS os dados financeiros de um usuário (contas, categorias, transações),
    mas MANTÉM a conta do usuário (login e senha).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Exclui todos os dados financeiros associados aoa user_id
        cursor.execute("DELETE FROM receitas WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM despesas WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM categorias WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM contas WHERE user_id = ?", (user_id,))
        
        # A linha "DELETE FROM users" foi REMOVIDA
        
        conn.commit()

        # Limpa o cache para que o app reflita o estado "zerado"
        st.cache_data.clear()
        
        print(f"Dados financeiros do usuário ID: {user_id} foram excluídos. A conta foi mantida.")


def add_user(username, name, email, hashed_password, is_admin=False):
    """
    Adiciona um novo usuário e, em seguida, associa a lista de ativos padrão a ele.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. Insere o novo usuário
        cursor.execute("""
            INSERT INTO users (username, name, email, password, is_admin)
            VALUES (?, ?, ?, ?, ?)
        """, (username, name, email, hashed_password, int(is_admin)))
        
        # Pega o ID do usuário que acabamos de criar
        user_id = cursor.lastrowid

        # 2. Copia os ativos da tabela padrão para a tabela de investimentos do novo usuário
        # Esta query insere na tabela 'investimentos' selecionando os dados da 'ativos_padrao'
        # e adicionando o user_id do novo usuário.
        query_copia_ativos = """
            INSERT INTO investimentos (user_id, tipo_id, codigo, descricao)
            SELECT ?, tipo_id, codigo, descricao
            FROM ativos_padrao
        """
        cursor.execute(query_copia_ativos, (user_id,))
        st.cache_data.clear()

def get_all_users():
    """Busca todos os usuários do banco de dados para a página de administração."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, name, email, is_admin FROM users")
        return cursor.fetchall()

def update_user_admin_status(user_id, is_admin):
    """Atualiza o status de administrador de um usuário específico."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (int(is_admin), user_id))
    # Limpa o cache para garantir que as permissões sejam recarregadas
    st.cache_data.clear()

@st.cache_data
def is_user_admin(username):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        return result is not None and result[0] == 1

@st.cache_data
def get_user_profile(username):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, email FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return {"user_id": row[0], "name": row[1], "email": row[2]} if row else None

# @st.cache_data
def get_authenticator_credentials():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, name, password FROM users")
        rows = cursor.fetchall()
        return {"usernames": {u[0]: {"name": u[1], "password": u[2]} for u in rows}}

def update_user_password(username, new_password):
    hashed = Hasher().hash(new_password)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, username))
    st.cache_data.clear()

def update_user_profile(username, new_name, new_email):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET name = ?, email = ? WHERE username = ?", (new_name, new_email, username))
    st.cache_data.clear()

# -------- Contas --------

def insert_conta(user_id, nome, vencimento, data_inicial=None, saldo_inicial=0.0, fechamento=None):
    try:
        saldo_inicial = float(saldo_inicial)
    except (ValueError, TypeError):
        raise ValueError("Saldo inicial deve ser um número válido")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contas (user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, nome, vencimento, data_inicial, saldo_inicial, fechamento))
    st.cache_data.clear()


def get_contas(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT conta_id, nome, vencimento, data_inicial, saldo_inicial, fechamento FROM contas WHERE user_id = ?", (user_id,))
        return cursor.fetchall()
    st.cache_data.clear()


def update_conta(conta_id, user_id, nome, vencimento, data_inicial=None, saldo_inicial=0.0, fechamento=None):
    try:
        saldo_inicial = float(saldo_inicial)
    except (ValueError, TypeError):
        raise ValueError("Saldo inicial deve ser um número válido")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE contas SET nome = ?, vencimento = ?, data_inicial = ?, saldo_inicial = ?, fechamento = ?
            WHERE conta_id = ? AND user_id = ?
        """, (nome, vencimento, data_inicial, saldo_inicial, fechamento, conta_id, user_id))
    st.cache_data.clear()

def delete_conta(conta_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contas WHERE conta_id = ? AND user_id = ?", (conta_id, user_id))
    st.cache_data.clear()

# -------- Categorias --------

def insert_categoria(user_id, tipo, nome):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (user_id, tipo, nome) VALUES (?, ?, ?)", (user_id, tipo, nome))
    st.cache_data.clear()

def get_categorias(user_id, tipo):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT categoria_id, nome FROM categorias WHERE user_id = ? AND tipo = ?", (user_id, tipo))
        return cursor.fetchall()
    st.cache_data.clear()

def update_categoria(categoria_id, user_id, nome):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE categorias SET nome = ? WHERE categoria_id = ? AND user_id = ?", (nome, categoria_id, user_id))
    st.cache_data.clear()

def delete_categoria(categoria_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categorias WHERE categoria_id = ? AND user_id = ?", (categoria_id, user_id))
    st.cache_data.clear()

# -------- Receitas --------

def insert_receita(user_id, conta_id, data, valor, categoria, descricao):
    try:
        valor = float(valor)
        if valor < 0: raise ValueError("Valor não pode ser negativo")
    except (ValueError, TypeError):
        raise ValueError("Valor deve ser um número válido")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO receitas (user_id, conta_id, data, valor, categoria, descricao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, conta_id, data, valor, categoria, descricao))
    st.cache_data.clear()


def get_receitas(user_id, dt_start=None, dt_end=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = "SELECT receita_id, user_id, conta_id, data, valor, categoria, descricao FROM receitas WHERE user_id = ?"
        params = [user_id]
        if dt_start and dt_end:
            query += " AND data BETWEEN ? AND ?"
            params.extend([dt_start, dt_end])
        cursor.execute(query, params)
        st.cache_data.clear()
        return cursor.fetchall()

def update_receita(receita_id, user_id, conta_id, data, valor, categoria, descricao):
    try:
        valor = float(valor)
        if valor < 0: raise ValueError("Valor não pode ser negativo")
    except (ValueError, TypeError):
        raise ValueError("Valor deve ser um número válido")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE receitas SET conta_id = ?, data = ?, valor = ?, categoria = ?, descricao = ?
            WHERE receita_id = ? AND user_id = ?
        """, (conta_id, data, valor, categoria, descricao, receita_id, user_id))
        st.cache_data.clear()

def delete_receita(receita_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM receitas WHERE receita_id = ? AND user_id = ?", (receita_id, user_id))
        st.cache_data.clear()

def get_or_create_categoria_receita(user_id, nome_categoria):
    """
    Verifica se uma categoria de receita existe.
    Se existir, retorna o nome original. Se não, cria a nova categoria e a retorna.
    """
    nome_categoria_clean = nome_categoria.strip().capitalize()
    if not nome_categoria_clean:
        raise ValueError("O nome da categoria não pode ser vazio.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM categorias WHERE user_id = ? AND lower(nome) = ? AND tipo = 'receita'", 
                       (user_id, nome_categoria_clean.lower()))
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            cursor.execute("INSERT INTO categorias (user_id, tipo, nome) VALUES (?, 'receita', ?)", 
                           (user_id, nome_categoria_clean))
            st.cache_data.clear()
            return nome_categoria_clean


# -------- Despesas --------

def _calcular_vencimento_credito(data_compra_obj, dia_vencimento, dias_fechamento):
    """
    Calcula a data de vencimento de uma compra no crédito, considerando o
    fechamento da fatura e ajustando-o para dias úteis (sexta-feira).
    """
    try:
        # 1. Tenta calcular o vencimento e fechamento para o MÊS ATUAL da compra
        vencimento_mes_atual = data_compra_obj.replace(day=dia_vencimento) + relativedelta(months=1)
    except ValueError:
        # Lida com meses que não têm o dia de vencimento (ex: vencimento dia 31 em fevereiro)
        # Encontra o último dia do mês e usa como base
        ultimo_dia_mes = (data_compra_obj.replace(day=1) + relativedelta(months=1)) - datetime.timedelta(days=1)
        vencimento_mes_atual = ultimo_dia_mes.replace(day=ultimo_dia_mes.day)+ relativedelta(months=1)

    fechamento_preliminar = vencimento_mes_atual - datetime.timedelta(days=dias_fechamento)
    
    # 2. AJUSTA a data de fechamento caso caia no fim de semana
    fechamento_real = _ajustar_data_para_sexta_anterior(fechamento_preliminar)

    # 3. Compara a data da compra com a data de fechamento REAL
    if data_compra_obj <= fechamento_real:
        # Se a compra foi feita ANTES ou NO DIA do fechamento, vence neste mês.
        return vencimento_mes_atual
    else:
        # Se a compra foi feita DEPOIS do fechamento, vence no PRÓXIMO mês.
        return vencimento_mes_atual + relativedelta(months=1)
    

def _ajustar_data_para_sexta_anterior(data_obj):
    """
    Recebe uma data e, se for sábado ou domingo, retorna a sexta-feira anterior.
    Caso contrário, retorna a própria data.
    """
    # Em Python, weekday() retorna 0 para segunda ... 5 para sábado e 6 para domingo.
    if data_obj.weekday() == 5:  # Se for sábado
        return data_obj - datetime.timedelta(days=1)
    elif data_obj.weekday() == 6:  # Se for domingo
        return data_obj - datetime.timedelta(days=2)
    else:  # Se for dia de semana
        return data_obj


def insert_despesa(user_id, conta_id, data_compra_str, valor, categoria, tipo_pagamento, parcelas, descricao):
    """
    Insere uma nova despesa, calculando o vencimento, tratando as parcelas
    e corrigindo a diferença de arredondamento no valor das parcelas.
    """
    try:
        valor_total = float(valor)
        if valor_total < 0: raise ValueError("Valor da despesa não pode ser negativo")
    except (ValueError, TypeError):
        raise ValueError("Valor da despesa deve ser um número válido")
    
    data_compra_obj = datetime.datetime.strptime(data_compra_str, "%Y-%m-%d").date()

    ## --- INÍCIO DA LÓGICA DE CORREÇÃO DE ARREDONDAMENTO ---
    
    # Calcula o valor padrão da parcela, arredondado para 2 casas decimais.
    valor_parcela_padrao = round(valor_total / parcelas, 2)
    
    # Calcula o total que teríamos somando todas as parcelas arredondadas.
    total_arredondado = valor_parcela_padrao * parcelas
    
    # Encontra a diferença (geralmente de R$ 0,01 ou R$ -0,01).
    diferenca = round(valor_total - total_arredondado, 2)
    
    # O valor da primeira parcela será o valor padrão mais a diferença.
    valor_primeira_parcela = valor_parcela_padrao + diferenca
    
    ## --- FIM DA LÓGICA DE CORREÇÃO DE ARREDONDAMENTO ---

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # O ID do grupo de parcelas é gerado uma vez para a compra inteira.
        grupo_id = int(datetime.datetime.now().timestamp() * 1000)

        # A lógica de cálculo do vencimento e da descrição da parcela
        # continua a mesma, dependendo do tipo de pagamento.
        primeiro_vencimento = None
        if tipo_pagamento == 'débito':
            primeiro_vencimento = data_compra_obj
        elif tipo_pagamento == 'crédito':
            cursor.execute("SELECT vencimento, fechamento FROM contas WHERE conta_id = ? AND user_id = ?", (conta_id, user_id))
            conta_info = cursor.fetchone()
            if not conta_info: raise ValueError("Conta de crédito não encontrada ou inválida.")
            dia_vencimento, dias_fechamento = conta_info
            primeiro_vencimento = _calcular_vencimento_credito(data_compra_obj, dia_vencimento, dias_fechamento)

        # Loop para inserir cada parcela no banco de dados.
        for i in range(parcelas):
            # Define o valor correto para a parcela atual.
            valor_a_inserir = valor_primeira_parcela if i == 0 else valor_parcela_padrao
            
            # Calcula o vencimento e a descrição da parcela atual.
            vencimento_parcela = primeiro_vencimento + relativedelta(months=i)
            descricao_parcela = f"{descricao} ({i+1}/{parcelas})" if parcelas > 1 else descricao

            cursor.execute("""
                INSERT INTO despesas (user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, parcela_grupo_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, conta_id, data_compra_str, vencimento_parcela.isoformat(), valor_a_inserir, categoria, tipo_pagamento, i + 1, descricao_parcela, grupo_id))
        

def get_despesas(user_id, dt_start=None, dt_end=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = "SELECT despesa_id, user_id, conta_id, data_compra, data_vencimento, valor, categoria, tipo_pagamento, parcelas, descricao, recorrencia, parcela_grupo_id FROM despesas WHERE user_id = ?"
        params = [user_id]
        if dt_start and dt_end:
            query += " AND data_vencimento BETWEEN ? AND ?"
            params.extend([dt_start, dt_end])
        query += " ORDER BY data_vencimento"
        cursor.execute(query, params)
        return cursor.fetchall()

def update_despesa(despesa_id, user_id, conta_id, data_compra, data_vencimento, valor, categoria, descricao):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE despesas SET conta_id = ?, data_compra = ?, data_vencimento = ?, valor = ?, categoria = ?, descricao = ?
            WHERE despesa_id = ? AND user_id = ?
        """, (conta_id, data_compra, data_vencimento, valor, categoria, descricao, despesa_id, user_id))
        st.cache_data.clear()

def delete_despesa(despesa_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM despesas WHERE despesa_id = ? AND user_id = ?", (despesa_id, user_id))
        st.cache_data.clear()

def get_or_create_categoria_despesa(user_id, nome_categoria):
    """
    Verifica se uma categoria de despesa existe (ignorando maiúsculas/minúsculas).
    Se existir, retorna o nome original. Se não, cria a nova categoria e a retorna.
    """
    # Padroniza o nome da categoria (remove espaços e capitaliza)
    nome_categoria_clean = nome_categoria.strip().capitalize()
    if not nome_categoria_clean:
        raise ValueError("O nome da categoria não pode ser vazio.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Procura pela categoria existente
        cursor.execute("SELECT nome FROM categorias WHERE user_id = ? AND lower(nome) = ? AND tipo = 'despesa'", 
                       (user_id, nome_categoria_clean.lower()))
        result = cursor.fetchone()

        if result:
            # Categoria já existe, retorna o nome com a capitalização correta do banco
            return result[0]
        else:
            # Categoria não existe, então cria
            cursor.execute("INSERT INTO categorias (user_id, tipo, nome) VALUES (?, 'despesa', ?)", 
                           (user_id, nome_categoria_clean))
            # Limpa o cache para que a nova categoria apareça em outros locais do app
            st.cache_data.clear()
            return nome_categoria_clean

# -------- Investimentos --------

@st.cache_data
def get_tipos_investimento():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT tipo_id, nome FROM tipos_investimento ORDER BY nome")
        return cursor.fetchall()

def add_investimento(user_id, tipo_id, codigo, descricao):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Evita duplicatas
        cursor.execute("SELECT investimento_id FROM investimentos WHERE user_id = ? AND lower(codigo) = ?", (user_id, codigo.lower()))
        if cursor.fetchone():
            raise ValueError("Este ativo já está cadastrado.")
        cursor.execute("INSERT INTO investimentos (user_id, tipo_id, codigo, descricao) VALUES (?, ?, ?, ?)",
                       (user_id, tipo_id, codigo.upper(), descricao))
        st.cache_data.clear() # Limpa o cache para atualizar listas de ativos

def add_transacao_investimento(investimento_id, tipo_transacao, data, quantidade, preco_unitario):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transacoes_investimento (investimento_id, tipo_transacao, data, quantidade, preco_unitario)
            VALUES (?, ?, ?, ?, ?)
        """, (investimento_id, tipo_transacao, data, quantidade, preco_unitario))
        st.cache_data.clear()

@st.cache_data
def get_portfolio_consolidado(user_id):
    """
    Calcula a posição atual de cada ativo do usuário.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            SELECT
                i.codigo,
                i.descricao,
                ti.nome as tipo,
                SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE -t.quantidade END) as quantidade_total,
                SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade * t.preco_unitario ELSE 0 END) / SUM(CASE WHEN t.tipo_transacao = 'compra' THEN t.quantidade ELSE 0 END) as preco_medio_compra
            FROM investimentos i
            JOIN transacoes_investimento t ON i.investimento_id = t.investimento_id
            JOIN tipos_investimento ti ON i.tipo_id = ti.tipo_id
            WHERE i.user_id = ?
            GROUP BY i.investimento_id
            HAVING quantidade_total > 0
            ORDER BY i.codigo
        """
        cursor.execute(query, (user_id,))
        return cursor.fetchall()

@st.cache_data
def get_investimentos_usuario(user_id):
    """Busca todos os ativos cadastrados pelo usuário para preencher selectboxes."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT investimento_id, codigo FROM investimentos WHERE user_id = ? ORDER BY codigo", (user_id,))
        return cursor.fetchall()
    
@st.cache_data
def get_all_transacoes(user_id):
    """Busca todas as transações de investimento de um usuário para edição."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            SELECT
                t.transacao_id,
                i.codigo,
                t.tipo_transacao,
                t.data,
                t.quantidade,
                t.preco_unitario
            FROM transacoes_investimento t
            JOIN investimentos i ON t.investimento_id = i.investimento_id
            WHERE i.user_id = ?
            ORDER BY t.data DESC
        """
        cursor.execute(query, (user_id,))
        return cursor.fetchall()

def update_transacao_investimento(transacao_id, data, quantidade, preco_unitario):
    """Atualiza os dados de uma transação de investimento específica."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE transacoes_investimento
            SET data = ?, quantidade = ?, preco_unitario = ?
            WHERE transacao_id = ?
        """, (data, quantidade, preco_unitario, transacao_id))
    st.cache_data.clear()

def delete_transacao_investimento(transacao_id):
    """Exclui uma transação de investimento específica."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transacoes_investimento WHERE transacao_id = ?", (transacao_id,))
    st.cache_data.clear()

def get_or_create_investimento(user_id, codigo, tipo_nome, descricao=""):
    """
    Verifica se um ativo existe para o usuário. Se não, cria um novo.
    Retorna o ID do investimento.
    """
    codigo_upper = codigo.strip().upper()
    if not codigo_upper:
        raise ValueError("O código do ativo não pode ser vazio.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. Verifica se o ativo já existe para este usuário
        cursor.execute("SELECT investimento_id FROM investimentos WHERE user_id = ? AND codigo = ?", (user_id, codigo_upper))
        result = cursor.fetchone()
        
        if result:
            return result[0] # Retorna o ID do ativo existente
        else:
            # 2. Se não existe, busca o ID do tipo de investimento
            cursor.execute("SELECT tipo_id FROM tipos_investimento WHERE lower(nome) = ?", (tipo_nome.lower(),))
            tipo_result = cursor.fetchone()
            if not tipo_result:
                # Se o tipo for inválido, podemos criar um padrão ou lançar um erro. Lançar erro é mais seguro.
                raise ValueError(f"O tipo de ativo '{tipo_nome}' não é válido.")
            
            tipo_id = tipo_result[0]

            # 3. Cria o novo ativo
            cursor.execute("INSERT INTO investimentos (user_id, tipo_id, codigo, descricao) VALUES (?, ?, ?, ?)",
                           (user_id, tipo_id, codigo_upper, descricao.strip()))
            st.cache_data.clear() # Limpa o cache para que o novo ativo apareça em outros lugares
            
            # Retorna o ID do ativo que acabamos de criar
            return cursor.lastrowid
        

#---- Relatorios ----

@st.cache_data
def get_transacoes_consolidadas(user_id):
    """
    Busca e consolida todas as transações financeiras do usuário:
    saldos iniciais, receitas e despesas (pela data de vencimento).
    Retorna uma lista de tuplas no formato (data, descrição, valor).
    """
    transacoes = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 1. Obter saldos iniciais das contas
        cursor.execute("SELECT data_inicial, nome, saldo_inicial FROM contas WHERE user_id = ?", (user_id,))
        for data, nome, saldo in cursor.fetchall():
            if data and saldo > 0:
                transacoes.append((data, f"Saldo Inicial - {nome}", saldo))

        # 2. Obter todas as receitas
        cursor.execute("SELECT data, descricao, valor FROM receitas WHERE user_id = ?", (user_id,))
        for data, descricao, valor in cursor.fetchall():
            transacoes.append((data, descricao, valor))
            
        # 3. Obter todas as despesas (considerando a data de VENCIMENTO)
        cursor.execute("SELECT data_vencimento, descricao, valor FROM despesas WHERE user_id = ?", (user_id,))
        for data, descricao, valor in cursor.fetchall():
            # Despesas são registradas como valores negativos
            transacoes.append((data, descricao, -valor))
            
    return transacoes

@st.cache_data
def get_despesas_por_categoria(user_id, dt_start, dt_end):
    """Retorna o valor total de despesas agrupado por categoria para um período."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            SELECT categoria, SUM(valor) 
            FROM despesas 
            WHERE user_id = ? AND data_vencimento BETWEEN ? AND ?
            GROUP BY categoria
            ORDER BY SUM(valor) DESC
        """
        cursor.execute(query, (user_id, dt_start, dt_end))
        return cursor.fetchall()

@st.cache_data
def get_total_receitas_mensal(user_id):
    """Retorna o valor total de receitas agrupado por mês/ano."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            SELECT strftime('%Y-%m', data) as mes, SUM(valor)
            FROM receitas
            WHERE user_id = ?
            GROUP BY mes
            ORDER BY mes
        """
        cursor.execute(query, (user_id,))
        return cursor.fetchall()

@st.cache_data
def get_total_despesas_mensal(user_id):
    """Retorna o valor total de despesas agrupado por mês/ano."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        query = """
            SELECT strftime('%Y-%m', data_vencimento) as mes, SUM(valor)
            FROM despesas
            WHERE user_id = ?
            GROUP BY mes
            ORDER BY mes
        """
        cursor.execute(query, (user_id,))
        return cursor.fetchall()
    
@st.cache_data
def get_fatura_cartao(user_id, conta_id, mes, ano):
    """
    Busca todas as despesas de um cartão de crédito para uma fatura específica (mês/ano de vencimento).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Busca todas as despesas daquela conta que vencem no mês e ano especificados.
        # O formato 'YYYY-MM' é usado para a comparação.
        mes_ano_str = f"{ano:04d}-{mes:02d}"
        query = """
            SELECT data_compra, descricao, valor
            FROM despesas
            WHERE user_id = ? AND conta_id = ? AND tipo_pagamento = 'crédito'
            AND strftime('%Y-%m', data_vencimento) = ?
            ORDER BY data_compra
        """
        cursor.execute(query, (user_id, conta_id, mes_ano_str))
        return cursor.fetchall()

@st.cache_data
def get_proximos_lancamentos(user_id, dias_futuros=3):
    """
    Busca receitas e despesas com vencimento nos próximos X dias.
    Retorna uma lista de tuplas no formato (data, descricao, valor, tipo).
    """
    lancamentos = []
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=dias_futuros)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 1. Buscar receitas futuras
        query_receitas = """
            SELECT data, descricao, valor, 'receita' as tipo
            FROM receitas
            WHERE user_id = ? AND data BETWEEN ? AND ?
        """
        cursor.execute(query_receitas, (user_id, today.isoformat(), end_date.isoformat()))
        lancamentos.extend(cursor.fetchall())

        # 2. Buscar despesas futuras pela data de vencimento
        query_despesas = """
            SELECT data_vencimento, descricao, valor, 'despesa' as tipo
            FROM despesas
            WHERE user_id = ? AND data_vencimento BETWEEN ? AND ?
        """
        cursor.execute(query_despesas, (user_id, today.isoformat(), end_date.isoformat()))
        lancamentos.extend(cursor.fetchall())

    # 3. Ordena todos os lançamentos por data
    lancamentos.sort(key=lambda x: x[0])
    return lancamentos


