import streamlit as st
import database
import yfinance as yf
import datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo 


def formatar_moeda_brl(valor):
    """Formata um número para o padrão de moeda brasileiro (R$ 1.234,56)."""
    try:
        # Garante que o valor é numérico antes de formatar
        valor_float = float(valor)
        # Usa a formatação padrão com vírgula e ponto, e depois inverte os separadores.
        valor_formatado = f'{valor_float:,.2f}'
        # Troca temporária para não haver conflito
        valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
        return valor_formatado
    except (ValueError, TypeError):
        # Retorna o valor original se não for um número
        return valor
    
def check_authentication():
    """
    Verifica se o usuário está logado. Se não, para a execução.
    Se sim, retorna o perfil e o user_id.
    """
    if not st.session_state.get("authentication_status"):
        st.info("Por favor, faça o login para acessar esta página.")
        st.stop()
    
    username = st.session_state['username']
    profile = database.get_user_profile(username)
    user_id = profile['user_id']
    
    return profile, user_id, username

@st.cache_data(ttl=3600) # Cache de 1 hora para não sobrecarregar a API
def get_current_price(ticker, tipo_ativo):
    """
    Busca o preço atual de um ativo usando a biblioteca yfinance.
    Adiciona o sufixo .SA para ações brasileiras e FIIs.
    """
    try:
        # Adiciona o sufixo .SA para ativos da B3 para a API do Yahoo Finance
        if tipo_ativo in ['Ação BR', 'FII']:
            ticker_yf = f"{ticker}.SA"
        else:
            ticker_yf = ticker
            
        stock = yf.Ticker(ticker_yf)
        # 'regularMarketPrice' é mais em tempo real, 'previousClose' é mais estável
        price = stock.info.get('regularMarketPrice', stock.info.get('previousClose'))
        
        if price is None:
            # Fallback para o histórico se a info não estiver disponível
            price = stock.history(period="1d")['Close'].iloc[0]

        return price
    except Exception as e:
        # st.warning(f"Não foi possível buscar a cotação para {ticker}: {e}")
        return 1


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

def get_local_today():
    """
    Retorna a data atual baseada no fuso horário de São Paulo (UTC-3).
    Esta função deve substituir todas as chamadas a datetime.date.today().
    """
    sao_paulo_tz = ZoneInfo("America/Sao_Paulo")
    return datetime.datetime.now(sao_paulo_tz).date()
