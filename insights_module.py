# insights_module.py

import streamlit as st
import google.generativeai as genai
import database
import json
from openai import OpenAI # Importamos a biblioteca da OpenAI
import re

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
    --- VERSÃO FINAL COM ILIKE PARA CASE-INSENSITIVE ---
    """
    prompt_gerador_sql = f"""
    Sua tarefa é agir como um especialista em SQL do dialeto PostgreSQL. Baseado no schema do banco de dados e na pergunta do usuário, gere uma ÚNICA query SQL que responda à pergunta.

    REGRAS CRÍTICAS:
    1.  A sua resposta deve conter APENAS o código SQL. Não adicione NENHUMA palavra de explicação.
    2.  A query DEVE começar com a palavra SELECT.
    3.  SEMPRE inclua a cláusula "WHERE user_id = {user_id}" em qualquer consulta para garantir a privacidade.
    4.  Para comparações de texto em cláusulas WHERE (como nome de categoria ou descrição), SEMPRE use o operador "ILIKE" em vez de "=" para garantir que a busca não seja sensível a maiúsculas/minúsculas. Por exemplo, use "categoria ILIKE '%gasolina%'" em vez de "categoria = 'gasolina'".

    SCHEMA DO BANCO DE DADOS:
    ---
    {schema}
    ---

    Pergunta do usuário: "{pergunta}"

    Query SQL:
    """
    try:
        client = OpenAI(api_key=st.secrets["groq"]["api_key"], base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_gerador_sql}],
            model="llama3-70b-8192",
            temperature=0.0,
        )
        
        resposta_completa = response.choices[0].message.content.strip()
        
        query_limpa = re.sub(r"```sql|```", "", resposta_completa).strip()

        if query_limpa.upper().startswith("SELECT"):
            print(f"Query SQL gerada e limpa: {query_limpa}")
            return query_limpa
        else:
            print(f"Resposta da IA não continha uma query SQL válida: {resposta_completa}")
            return None

    except Exception as e:
        print(f"Erro na API ao gerar SQL: {e}")
        return None
    
def responder_pergunta_do_usuario(user_id, pergunta):
    """
    Orquestra o processo Text-to-SQL com depuração adicionada.
    """
    # 1. Obter o schema do banco
    schema = database.get_full_database_schema()
    
    # 2. Gerar a query SQL
    st.session_state.last_sql_query = "Nenhuma query foi gerada ainda." # Inicializa no estado da sessão
    query_sql = gerar_query_sql_com_ia(user_id, pergunta, schema)
    
    if not query_sql:
        return "Desculpe, não consegui traduzir sua pergunta em uma consulta ao banco de dados."

    # Armazena a última query gerada no estado da sessão para depuração
    st.session_state.last_sql_query = query_sql
    
    # 3. Executar a query de forma segura
    try:
        resultados = database.execute_generated_sql(query_sql)
    except ValueError as ve:
        return f"Erro de segurança: {ve}"
    except Exception as e:
        # Retorna a query que causou o erro para facilitar a depuração
        return f"Ocorreu um erro ao executar a consulta no banco de dados.\n\n**Query Tentada:**\n```sql\n{query_sql}\n```\n**Erro:**\n`{e}`"

    # 4. Gerar a resposta final com base nos resultados
    prompt_final = f"""
    Contexto: A pergunta do usuário foi '{pergunta}'. A consulta ao banco de dados retornou os seguintes dados:
    {json.dumps(resultados, indent=2, default=str)}

    Sua tarefa é analisar os dados do contexto e responder à pergunta do usuário de forma clara e amigável em português.
    Se a lista de dados estiver vazia, informe ao usuário que você não encontrou resultados para a busca dele. Seja específico se possível.
    """
    
    try:
        client = OpenAI(api_key=st.secrets["groq"]["api_key"], base_url="https://api.groq.com/openai/v1")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_final}],
            model="llama3-8b-8192",
            temperature=0.7
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Ocorreu um erro ao gerar a resposta final: {e}"