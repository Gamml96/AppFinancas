import streamlit as st
import database
import yfinance as yf

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
        return 0.0