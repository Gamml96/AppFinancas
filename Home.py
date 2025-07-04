# app.py (versão simplificada)
import streamlit as st
import streamlit_authenticator as stauth
import database
import datetime
import pandas as pd
import plotly.express as px
from dateutil.relativedelta import relativedelta
import utils
import yfinance as yf

# --- Funções da Página Home ---

def render_home_page(user_id):
    st.title("Visão Geral Financeira")
    st.header("Fluxo de Caixa Diário")

    transacoes = database.get_transacoes_consolidadas(user_id)

    if not transacoes:
        st.info("Você ainda não possui transações para exibir o fluxo de caixa.")
        return

    # O restante do código do fluxo de caixa permanece o mesmo...
    df = pd.DataFrame(transacoes, columns=["data", "descricao", "valor"])
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values(by="data")

    df['entradas'] = df['valor'].apply(lambda x: x if x > 0 else 0)
    df['saidas'] = df['valor'].apply(lambda x: abs(x) if x < 0 else 0)

    fluxo_diario = df.groupby('data').agg(
        entradas=('entradas', 'sum'),
        saidas=('saidas', 'sum')
    ).reset_index()
    
    if not fluxo_diario.empty:
        data_inicio = fluxo_diario['data'].min()
        
        data_fim_transacoes = fluxo_diario['data'].max()
        data_fim_hoje = pd.to_datetime(datetime.date.today())
        data_fim = max(data_fim_transacoes, data_fim_hoje)

        todos_os_dias = pd.date_range(start=data_inicio, end=data_fim, freq='D')

        fluxo_diario = fluxo_diario.set_index('data').reindex(todos_os_dias)
        fluxo_diario[['entradas', 'saidas']] = fluxo_diario[['entradas', 'saidas']].fillna(0)
        fluxo_diario['saldo_dia'] = fluxo_diario['entradas'] - fluxo_diario['saidas']
        fluxo_diario['saldo_acumulado'] = fluxo_diario['saldo_dia'].cumsum()
        fluxo_diario = fluxo_diario.reset_index().rename(columns={'index': 'data'})

    saldo_atual = fluxo_diario[fluxo_diario['data'].dt.date <= datetime.date.today()]['saldo_acumulado'].iloc[-1] if not fluxo_diario.empty else 0.0
    saldo_atual = utils.formatar_moeda_brl(saldo_atual)
    st.metric("Saldo Atual Consolidado (Hoje)", f"R$ {saldo_atual}")

    st.markdown("---")

    st.markdown("### Evolução do Saldo")
    st.line_chart(fluxo_diario.rename(columns={'data':'index'}).set_index('index')['saldo_acumulado'])

    st.markdown("---")

    st.markdown("### Detalhamento do Fluxo de Caixa")

    def highlight_today(row):
        if row.data.date() == datetime.date.today():
            return ['background-color: #3D5320'] * len(row)
        return [''] * len(row)

    df_display = fluxo_diario.sort_values(by="data", ascending=True)[["data", "entradas", "saidas", "saldo_acumulado"]]
    
    styled_df = df_display.style.apply(highlight_today, axis=1).format({
        "entradas": utils.formatar_moeda_brl,
        "saidas": utils.formatar_moeda_brl,
        "saldo_acumulado": utils.formatar_moeda_brl
    }).hide(axis="index")
    
    st.dataframe(
        styled_df,
        column_config={
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "entradas": st.column_config.NumberColumn("Entradas"),
            "saidas": st.column_config.NumberColumn("Saídas"),
            "saldo_acumulado": st.column_config.NumberColumn("Saldo do Dia")
        },
        use_container_width=True,
        hide_index=True
    )
    st.markdown("---")

    # --- INÍCIO DA NOVA SEÇÃO: PRÓXIMOS LANÇAMENTOS ---
    
    st.markdown("### Lançamentos Próximos")
    # Busca os lançamentos para os próximos 3 dias
    proximos_lancamentos = database.get_proximos_lancamentos(user_id, dias_futuros=3)

    if not proximos_lancamentos:
        st.info("Nenhum lançamento previsto para os próximos 3 dias.")
    else:
        st.write("Fique de olho nas suas próximas movimentações:")
        for data, descricao, valor, tipo in proximos_lancamentos:
            data_obj = datetime.datetime.strptime(data, '%Y-%m-%d').date()
            hoje = datetime.date.today()
            
            # Formata a data de forma amigável
            if data_obj == hoje:
                dia_str = "Hoje"
            elif data_obj == hoje + datetime.timedelta(days=1):
                dia_str = "Amanhã"
            else:
                dia_str = data_obj.strftime('%d/%m/%Y')
            valor = utils.formatar_moeda_brl(valor)
            # Exibe um alerta colorido e com ícone para cada lançamento
            if tipo == 'receita':
                st.success(f"**{dia_str}:** {descricao.upper()} | **+ R$ {valor}**", icon="💰")
            else: # tipo == 'despesa'
                st.error(f"**{dia_str}:** {descricao.upper()} | **- R$ {valor}**", icon="💸")

    st.markdown("---")
    
    # --- FIM DA NOVA SEÇÃO ---

# --- LÓGICA PRINCIPAL DE AUTENTICAÇÃO ---
def main():
    st.set_page_config("App Finanças", layout="wide", initial_sidebar_state="auto")
    database.init_db()
    credentials = database.get_authenticator_credentials()
    
    authenticator = stauth.Authenticate(
        credentials, 
        cookie_name="app_fin_cookie",
        key="app_fin_key", 
        cookie_expiry_days=30
    )

    # Verifica se o usuário já está logado
    if st.session_state.get("authentication_status"):
        # Se logado, mostra o nome, botão de logout e a página Home
        with st.sidebar:
            st.subheader(f"Bem-vindo, {st.session_state['name']}!")
            authenticator.logout("Logout", "sidebar", key="logout_button")
        
        # Renderiza a página Home
        user_id = database.get_user_profile(st.session_state['username'])['user_id']
        render_home_page(user_id)
    else:
        # Se não está logado, mostra o formulário de login
        authenticator.login(fields={'Form name': 'Login'})
        if st.session_state["authentication_status"] is False:
            st.error("Usuário ou senha incorretos.")
        elif st.session_state["authentication_status"] is None:
            st.warning("Por favor, insira seu usuário e senha.")

if __name__ == "__main__":
    main()