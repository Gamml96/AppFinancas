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
            - De uma analise detalhada da vida financeira.
            - Foque nos insights mais importantes.
            - Dê uma sugestão prática ou um elogio, se apropriado.
            - NÃO invente dados. Baseie-se APENAS no resumo JSON fornecido.
            - Formate sua resposta de forma a ficar mais clara as informacoes, e lembre que estamos utilizando o streamlit para apresentar a resposta.
            - NÃO CONSIDERE A categoria 'Transferências' na sua analise."""
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
            temperature=0.7,
            max_tokens=1024,
        )
        # A resposta vem na mesma estrutura da API da OpenAI
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Ocorreu um erro ao comunicar com a IA do Groq: {e}"