# utils.py (versão final, completa e estável)

import streamlit as st
import database
import yfinance as yf
import datetime
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo 
import requests
import streamlit_authenticator as stauth

def formatar_moeda_brl(valor):
    """
    Formata um número para o padrão de moeda brasileiro (R$ 1.234,56).
    """
    try:
        valor_float = float(valor)
        # Usa a formatação padrão com vírgula e ponto, e depois inverte os separadores.
        valor_formatado = f'{valor_float:,.2f}'
        # Troca temporária para não haver conflito
        valor_formatado = valor_formatado.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {valor_formatado}"
    except (ValueError, TypeError):
        # Retorna o valor original se não for um número ou se for None
        return valor

def get_local_today():
    """
    Retorna a data atual baseada no fuso horário de São Paulo (UTC-3).
    Esta função deve substituir todas as chamadas a datetime.date.today().
    """
    try:
        sao_paulo_tz = ZoneInfo("America/Sao_Paulo")
        return datetime.datetime.now(sao_paulo_tz).date()
    except Exception:
        # Fallback para o fuso horário padrão do sistema em caso de erro
        return datetime.date.today()

def check_authentication():
    """
    Função central de autenticação. Verifica se o usuário está logado.
    Se não estiver, exibe a tela de login.
    Se estiver, configura a sidebar e retorna os dados essenciais do usuário.
    Levanta um st.stop() para interromper a execução da página se o login não for bem-sucedido.
    """
    # 1. Busca as credenciais de forma segura
    credentials = database.get_authenticator_credentials()
    
    # 2. Inicializa o objeto de autenticação
    authenticator = stauth.Authenticate(
        credentials,
        cookie_name="app_fin_cookie",
        key="app_fin_key",
        cookie_expiry_days=30
    )

    # 3. Renderiza o formulário de login
    authenticator.login()

    # --- Lógica para Usuário LOGADO ---
    if st.session_state.get("authentication_status"):
        username = st.session_state['username']
        with st.sidebar:
            st.subheader(f"Bem-vindo, {st.session_state['name']}!")
            st.markdown("---")
            authenticator.logout("Logout", "sidebar", key="logout_button")
        
        profile = database.get_user_profile(username)
        if profile:
            user_id = profile['user_id']
            return profile, user_id, username, credentials, authenticator
        else:
            st.error("Erro crítico: Não foi possível carregar o perfil do usuário logado.")
            st.stop()

    # --- Lógica para Tentativa de Login FALHA ---
    elif st.session_state.get("authentication_status") is False:
        st.error('Usuário ou senha incorretos.')
        st.stop()

    # --- Lógica para Estado INICIAL (nenhuma tentativa de login) ---
    elif st.session_state.get("authentication_status") is None:
        st.warning('Por favor, insira seu usuário e senha para continuar.')
        st.stop()

    # Fallback para garantir que a aplicação pare se nenhuma condição for atendida
    st.stop()


@st.cache_data(ttl=900) # Cache de 15 minutos
def get_current_price(ticker, tipo_ativo):
    """
    Busca o preço atual de um ativo usando a biblioteca yfinance.
    Adiciona o sufixo .SA para ações brasileiras e FIIs.
    """
    try:
        if tipo_ativo in ['Ação BR', 'FII']:
            ticker_yf = f"{ticker.upper()}.SA"
        else:
            ticker_yf = ticker.upper()
            
        stock = yf.Ticker(ticker_yf)
        price = stock.info.get('regularMarketPrice', stock.info.get('previousClose'))
        
        if price is None:
            price = stock.history(period="1d")['Close'].iloc[0]

        return price if price else 0.0
    except Exception:
        # st.warning(f"Não foi possível buscar a cotação para {ticker}")
        return 0.0

@st.cache_data(ttl=43200) # Cache de 12 horas
def get_cdi_acumulado(data_inicio, data_fim):
    """
    Busca os dados da taxa DI do Banco Central e calcula o fator de rendimento acumulado.
    """
    try:
        data_inicio_str = data_inicio.strftime('%d/%m/%Y')
        data_fim_str = data_fim.strftime('%d/%m/%Y')
        
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json&dataInicial={data_inicio_str}&dataFinal={data_fim_str}"
        
        response = requests.get(url)
        response.raise_for_status()
        dados_cdi = response.json()
        
        if not dados_cdi: return 1.0

        fator_acumulado = 1.0
        for registro_diario in dados_cdi:
            taxa_diaria = float(registro_diario['valor']) / 100
            fator_acumulado *= (1 + taxa_diaria)
            
        return fator_acumulado
    except Exception:
        # st.error(f"Não foi possível buscar os dados do CDI.")
        return 1.0

@st.cache_data(ttl=900) # Cache de 15 minutos
def get_opcoes_disponiveis(ticker):
    """
    Busca todas as opções disponíveis (Calls e Puts) para um ativo usando a API da Brapi.
    """
    if "brapi" not in st.secrets or "token" not in st.secrets["brapi"]:
        st.error("Token da API Brapi não configurado nos segredos do Streamlit.")
        return []
        
    token = st.secrets["brapi"]["token"]
    ticker_limpo = ticker.upper().replace(".SA", "")
    url = f"https://brapi.dev/api/quote/{ticker_limpo}?range=1d&interval=1d&fundamental=false&dividends=false"

    try:
        response = requests.get(url, params={'token': token})
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        if not results or 'options' not in results[0]:
            st.warning(f"Nenhuma opção encontrada para o ativo '{ticker_limpo}'. Verifique o código do ativo.")
            return []
            
        return results[0]['options']
    except requests.exceptions.HTTPError:
        st.error(f"Erro ao buscar dados para '{ticker_limpo}': Ativo não encontrado ou API indisponível.")
        return []
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao buscar opções: {e}")
        return []

# --- Funções de Cálculo ---
def _ajustar_data_para_sexta_anterior(data_obj):
    if data_obj.weekday() == 5: return data_obj - datetime.timedelta(days=1)
    if data_obj.weekday() == 6: return data_obj - datetime.timedelta(days=2)
    return data_obj

def _calcular_vencimento_credito(data_compra_obj, dia_vencimento, dias_fechamento):
    try:
        # Garante que os dias são inteiros
        dia_vencimento = int(dia_vencimento)
        dias_fechamento = int(dias_fechamento)

        vencimento_base = (data_compra_obj + relativedelta(months=1)).replace(day=dia_vencimento)
    except ValueError:
        proximo_mes = data_compra_obj + relativedelta(months=1)
        ultimo_dia_mes = (proximo_mes.replace(day=1) + relativedelta(months=1)) - datetime.timedelta(days=1)
        vencimento_base = ultimo_dia_mes
    except (TypeError, AttributeError):
        # Fallback se os dias de vencimento/fechamento não forem válidos
        return data_compra_obj + relativedelta(months=1)

    fechamento_preliminar = vencimento_base - datetime.timedelta(days=dias_fechamento)
    fechamento_real = _ajustar_data_para_sexta_anterior(fechamento_preliminar)
    if data_compra_obj <= fechamento_real: return vencimento_base
    else: return vencimento_base + relativedelta(months=1)

