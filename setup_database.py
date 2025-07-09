# setup_database.py (versão para PostgreSQL)
import os
import psycopg2
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- DEFINIÇÃO DA ESTRUTURA DO BANCO DE DADOS ---
# Lista de todos os comandos para criar as tabelas.
# SERIAL PRIMARY KEY é o auto-incremento no PostgreSQL.
# ON DELETE CASCADE garante que ao deletar um usuário, todos os seus dados sejam apagados.
SQL_COMMANDS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT,
        password TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE
    )""",
    """
    CREATE TABLE IF NOT EXISTS contas (
        conta_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        data_inicial DATE,
        saldo_inicial REAL,
        vencimento INTEGER,
        fechamento INTEGER
    )""",
    """
    CREATE TABLE IF NOT EXISTS categorias (
        categoria_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        tipo TEXT NOT NULL,
        nome TEXT NOT NULL,
        UNIQUE(user_id, tipo, nome)
    )""",
    """
    CREATE TABLE IF NOT EXISTS receitas (
        receita_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        conta_id INTEGER REFERENCES contas(conta_id) ON DELETE SET NULL,
        data DATE,
        valor REAL,
        categoria TEXT,
        descricao TEXT
    )""",
    """
    CREATE TABLE IF NOT EXISTS despesas (
        despesa_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        conta_id INTEGER REFERENCES contas(conta_id) ON DELETE SET NULL,
        data_compra DATE NOT NULL,
        data_vencimento DATE NOT NULL,
        valor REAL NOT NULL,
        categoria TEXT,
        tipo_pagamento TEXT NOT NULL,
        parcelas INTEGER,
        descricao TEXT,
        recorrencia TEXT,
        parcela_grupo_id BIGINT
    )""",
    """
    CREATE TABLE IF NOT EXISTS tipos_investimento (
        tipo_id SERIAL PRIMARY KEY,
        nome TEXT UNIQUE NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS investimentos (
        investimento_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        tipo_id INTEGER REFERENCES tipos_investimento(tipo_id),
        codigo TEXT NOT NULL,
        descricao TEXT,
        UNIQUE(user_id, codigo)
    )""",
    """
    CREATE TABLE IF NOT EXISTS transacoes_investimento (
        transacao_id SERIAL PRIMARY KEY,
        investimento_id INTEGER REFERENCES investimentos(investimento_id) ON DELETE CASCADE,
        tipo_transacao TEXT NOT NULL,
        data DATE NOT NULL,
        quantidade REAL NOT NULL,
        preco_unitario REAL NOT NULL
    )""",
    """
    CREATE TABLE IF NOT EXISTS ativos_padrao (
        ativo_id SERIAL PRIMARY KEY,
        tipo_id INTEGER REFERENCES tipos_investimento(tipo_id),
        codigo TEXT UNIQUE NOT NULL,
        descricao TEXT
    )""",
    """
    CREATE TABLE IF NOT EXISTS orcamentos (
        orcamento_id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
        categoria_nome TEXT NOT NULL,
        limite_mensal REAL NOT NULL,
        UNIQUE(user_id, categoria_nome)
    )
    """
]

def init_db_postgres():
    """Conecta ao banco PostgreSQL e cria/popula as tabelas necessárias."""
    conn = None
    try:
        # Conecta ao banco de dados usando as variáveis de ambiente
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            dbname=os.getenv("PG_DBNAME"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD")
        )
        with conn.cursor() as cur:
            print("Conexão bem-sucedida. Criando tabelas...")
            for command in SQL_COMMANDS:
                cur.execute(command)
            print("Estrutura de tabelas verificada/criada com sucesso.")
            
            # --- POPULANDO TABELAS PADRÃO ---
            
            # Popula tipos_investimento
            cur.execute("SELECT count(*) FROM tipos_investimento")
            if cur.fetchone()[0] == 0:
                tipos = [('Ação BR',), ('Ação EUA',), ('FII',), ('Criptomoeda',), ('Renda Fixa',)]
                cur.executemany("INSERT INTO tipos_investimento (nome) VALUES (%s)", tipos)
                print("Tipos de investimento padrão inseridos.")

            # Popula ativos_padrao
            cur.execute("SELECT count(*) FROM ativos_padrao")
            if cur.fetchone()[0] == 0:
                cur.execute("SELECT nome, tipo_id FROM tipos_investimento")
                tipos_map = {nome: tipo_id for nome, tipo_id in cur.fetchall()}
                ativos = [
                    (tipos_map['Ação BR'], 'PETR4', 'Petrobras PN'),
                    (tipos_map['Ação BR'], 'VALE3', 'Vale ON'),
                    (tipos_map['Ação BR'], 'ITUB4', 'Itaú Unibanco PN'),
                    (tipos_map['FII'], 'MXRF11', 'Maxi Renda FII'),
                    (tipos_map['FII'], 'HGLG11', 'CSHG Logística FII'),
                    (tipos_map['Criptomoeda'], 'BTC-USD', 'Bitcoin'),
                    (tipos_map['Criptomoeda'], 'ETH-USD', 'Ethereum'),
                    (tipos_map['Ação EUA'], 'AAPL', 'Apple Inc.'),
                    (tipos_map['Ação EUA'], 'MSFT', 'Microsoft Corporation'),
                ]
                cur.executemany("INSERT INTO ativos_padrao (tipo_id, codigo, descricao) VALUES (%s, %s, %s)", ativos)
                print("Ativos padrão inseridos.")

    except Exception as e:
        print(f"Ocorreu um erro durante o setup do banco de dados: {e}")
    finally:
        if conn:
            conn.commit()
            conn.close()
            print("Setup finalizado e conexão fechada.")

if __name__ == "__main__":
    init_db_postgres()