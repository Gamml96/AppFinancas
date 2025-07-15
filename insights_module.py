# insights_module.py

import streamlit as st
import google.generativeai as genai
import database
import json

def gerar_insights_financeiros(user_id, start_date, end_date):
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
    - Formate sua resposta para um markdown do streamlit, quebre linhas para melhor formatação.
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