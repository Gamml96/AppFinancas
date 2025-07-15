# insights_module.py

import streamlit as st
import google.generativeai as genai
import database
import json

def gerar_insights_financeiros(user_id):
    """
    Busca o resumo financeiro, monta o prompt e chama a API do Gemini.
    """
    # 1. Configura a API do Gemini com a chave dos segredos
    try:
        genai.configure(api_key=st.secrets["google_ai"]["api_key"])
    except Exception:
        return "Erro: A chave de API do Google AI não foi configurada corretamente nos segredos do Streamlit."

    # 2. Busca os dados financeiros do usuário
    summary_data = database.get_financial_summary_for_ai(user_id)
    
    # Verifica se há dados suficientes para uma análise
    if not summary_data.get('gastos_recentes') and not summary_data.get('receitas_recentes'):
        return "Não há dados financeiros suficientes nos últimos 30 dias para gerar uma análise."

    # Converte os dados para uma string JSON para incluir no prompt
    dados_json = json.dumps(summary_data, indent=2, ensure_ascii=False)

    # 3. Monta o Prompt para a IA
    # Este é o coração da funcionalidade. Um bom prompt gera boas respostas.
    prompt = f"""
    Você é um assistente financeiro pessoal, amigável e perspicaz. Seu objetivo é analisar os dados financeiros de um usuário e fornecer um parágrafo curto com insights úteis, em português do Brasil.

    Regras:
    - Seja conciso e direto.
    - Foque no insight mais importante (maior gasto, comparação com orçamento, etc.).
    - Dê uma sugestão prática ou um elogio, se apropriado.
    - NÃO invente dados. Baseie-se APENAS no resumo JSON fornecido.
    - NÃO use markdown na sua resposta, apenas texto simples.

    Aqui está o resumo dos dados financeiros do usuário nos últimos 30 dias:
    ```json
    {dados_json}
    ```

    Por favor, gere o parágrafo de insight para o usuário:
    """

    # 4. Chama a API do Gemini
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Ocorreu um erro ao comunicar com a IA: {e}"