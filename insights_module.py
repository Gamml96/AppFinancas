# insights_module.py

import streamlit as st
import google.generativeai as genai
import database
import json
from openai import OpenAI # Importamos a biblioteca da OpenAI

def gerar_insights_financeiros_gemini(user_id, start_date, end_date):
    """
    Busca o resumo financeiro de um período, monta o prompt e chama a API do Gemini.
    """
    try:
        genai.configure(api_key=st.secrets["google_ai"]["api_key"])
    except Exception:
        return "Erro: A chave de API do Google AI não foi configurada corretamente."

    # Passa as datas para a função do banco de dados
    summary_data = database.get_financial_summary_for_ai(user_id, start_date, end_date)
    
    if not summary_data.get('gastos_recentes') and not summary_data.get('receitas_recentes'):
        return f"Não há dados financeiros suficientes entre {start_date.strftime('%d/%m/%Y')} e {end_date.strftime('%d/%m/%Y')} para gerar uma análise."

    dados_json = json.dumps(summary_data, indent=2, ensure_ascii=False)

    # Adicionamos o período de análise ao prompt para dar contexto à IA
    periodo_analise = f"de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
    
    prompt = f"""
    Você é um assistente financeiro pessoal, amigável e perspicaz. Seu objetivo é analisar os dados financeiros de um usuário e fornecer um parágrafo curto com insights úteis, em português do Brasil.

    Regras:
    - Seja conciso e direto.
    - Dê uma sugestão prática ou um elogio, se apropriado.
    - NÃO invente dados. Baseie-se APENAS no resumo JSON fornecido.
    - Formate sua resposta de forma que o texto fique claro, quebre linhas para melhor formatação.
    - IGNORE a categoria de transferências.


    Aqui está o resumo dos dados financeiros do usuário para o período {periodo_analise}:
    ```json
    {dados_json}
    ```

    Por favor, gere o parágrafo de insight para o usuário sobre este período:
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Ocorreu um erro ao comunicar com a IA: {e}"
    
def gerar_insights_financeiros(user_id, start_date, end_date):
    """
    Busca o resumo financeiro, monta o prompt e chama a API do Groq.
    """
    # 1. Configura o "cliente" da API, apontando para os servidores do Groq
    try:
        client = OpenAI(
            api_key=st.secrets["groq"]["api_key"],
            base_url="https://api.groq.com/openai/v1", # URL específica para a API do Groq
        )
    except Exception:
        return "Erro: A chave de API do Groq (groq) não foi configurada corretamente nos segredos do Streamlit."

    # 2. Busca os dados financeiros (esta parte não muda)
    summary_data = database.get_financial_summary_for_ai(user_id, start_date, end_date)
    
    if not summary_data.get('gastos_recentes') and not summary_data.get('receitas_recentes'):
        return f"Não há dados financeiros suficientes entre {start_date.strftime('%d/%m/%Y')} e {end_date.strftime('%d/%m/%Y')} para gerar uma análise."

    dados_json = json.dumps(summary_data, indent=2, ensure_ascii=False)
    periodo_analise = f"de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
    
    # 3. Monta o Prompt para a IA (o prompt pode ser o mesmo, ele é agnóstico ao modelo)
    messages = [
        {
            "role": "system",
            "content": """Você é um assistente financeiro pessoal, amigável e perspicaz. Seu objetivo é analisar os dados financeiros de um usuário e fornecer um parágrafo curto com insights úteis, em português do Brasil.
            Regras:
            - Revise os cálculos para nao apresentar somas erradas.
            - NÃO CONSIDERE A categoria 'Transferências' na sua analise.
            - De uma analise detalhada da vida financeira.
            - Foque nos insights mais importantes.
            - Dê uma sugestão prática ou um elogio, se apropriado.
            - NÃO invente dados. Baseie-se APENAS no resumo JSON fornecido.
            - Formate sua resposta de forma a ficar mais clara as informacoes, e lembre que estamos utilizando o streamlit para apresentar a resposta.
            """
        },
        {
            "role": "user",
            "content": f"""Aqui está o resumo dos dados financeiros do usuário para o período {periodo_analise}:
            ```json
            {dados_json}
            ```
            Por favor, gere uma análise para o usuário sobre este período:"""
        }
    ]

    # 4. Chama a API do Groq
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192", # Modelo popular e rápido disponível no Groq. Outra opção é "mixtral-8x7b-32768".
            temperature=1.0,
            max_tokens=1024,
        )
        # A resposta vem na mesma estrutura da API da OpenAI
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Ocorreu um erro ao comunicar com a IA do Groq: {e}"
    
def gerar_query_sql_com_ia(user_id, pergunta, schema):
    """
    Usa a LLM para traduzir uma pergunta em linguagem natural para uma query SQL.
    """
    prompt_gerador_sql = f"""
    Sua tarefa é agir como um especialista em SQL. Baseado no schema do banco de dados e na pergunta do usuário, gere uma ÚNICA query SQL que responda à pergunta.

    REGRAS IMPORTANTES:
    1.  Use APENAS as tabelas e colunas descritas no schema. Não invente colunas.
    2.  A query DEVE ser apenas de leitura (começar com SELECT).
    3.  SEMPRE filtre os resultados pelo 'user_id' fornecido para garantir a privacidade do usuário. O user_id é: {user_id}.
    4.  Use o dialeto PostgreSQL.

    SCHEMA DO BANCO DE DADOS:
    ---
    {schema}
    ---

    Pergunta do usuário: "{pergunta}"

    Sua query SQL:
    """
    try:
        client = OpenAI(api_key=st.secrets["groq"]["api_key"], base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_gerador_sql}],
            model="llama3-70b-8192", # Usamos um modelo maior e mais capaz para gerar SQL
            temperature=0.0,
        )
        # Extrai a query SQL da resposta da IA
        query_gerada = response.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
        return query_gerada
    except Exception as e:
        print(f"Erro ao gerar SQL: {e}")
        return None

def responder_pergunta_do_usuario(user_id, pergunta):
    """
    Orquestra o processo Text-to-SQL:
    1. Obtém o schema do banco.
    2. Usa a IA para gerar a query SQL.
    3. Executa a query de forma segura.
    4. Usa a IA para gerar a resposta final em linguagem natural.
    """
    # 1. Obter o schema do banco
    schema = database.get_full_database_schema()
    
    # 2. Gerar a query SQL
    query_sql = gerar_query_sql_com_ia(user_id, pergunta, schema)
    
    if not query_sql:
        return "Desculpe, não consegui traduzir sua pergunta em uma consulta ao banco de dados."

    # 3. Executar a query de forma segura
    try:
        resultados = database.execute_generated_sql(query_sql)
    except ValueError as ve: # Erro de segurança (ex: não é um SELECT)
        return f"Erro de segurança: {ve}"
    except Exception as e:
        print(f"Erro ao executar SQL: {e}\nQuery: {query_sql}")
        return "Ocorreu um erro ao buscar os dados para responder sua pergunta."

    # 4. Gerar a resposta final com base nos resultados
    prompt_final = f"""
    Contexto: A pergunta do usuário foi '{pergunta}'. A consulta ao banco de dados retornou os seguintes dados em formato JSON:
    {json.dumps(resultados, indent=2, default=str)}

    Sua tarefa é analisar os dados do contexto e responder à pergunta do usuário de forma clara, amigável e em português.
    Se os dados estiverem vazios, informe ao usuário que não foram encontrados resultados para a pergunta dele.
    """
    
    try:
        client = OpenAI(api_key=st.secrets["groq"]["api_key"], base_url="https://api.groq.com/openai/v1")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_final}],
            model="llama3-8b-8192", # Um modelo mais rápido é suficiente para formatar a resposta
            temperature=0.7
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Ocorreu um erro ao gerar a resposta final: {e}"