import streamlit as st
import streamlit_authenticator as stauth
import database
import datetime
import pandas as pd
import utils
import plotly.express as px
from dateutil.relativedelta import relativedelta
import calendar

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

st.title("Visão Geral Financeira")
st.markdown("---")

# Busca contas para os filtros
contas = database.get_contas(user_id)
if not contas:
    st.warning("Cadastre pelo menos uma conta para começar.")
    st.stop()

contas_dict = {conta[1]: conta[0] for conta in contas}

# Início dos filtros horizontais
st.markdown("### Filtros ")

hoje = datetime.date.today()
meses = {i: calendar.month_name[i] for i in range(1, 13)}
meses_keys = list(meses.keys())
meses_keys.insert(0, "Todos")
hoje = datetime.date.today()
mes_atual = hoje.month
index_mes = meses_keys.index(mes_atual) if mes_atual in meses_keys else 0

filtro_cols = st.columns(3)
with filtro_cols[2]:
    conta_filtro = st.selectbox("Conta", options=["Todas"] + list(contas_dict.keys()))
# Carrega transações para montar anos e aplicar filtros
transacoes = database.get_transacoes_consolidadas(
    user_id, conta_id=contas_dict.get(conta_filtro) if conta_filtro != "Todas" else None
)
df = pd.DataFrame(transacoes, columns=["data", "descricao", "valor"])
df["data"] = pd.to_datetime(df["data"])

# Monta os anos do filtro de acordo com os dados do DataFrame
if not df.empty:
    anos = sorted(df["data"].dt.year.unique())
else:
    anos = [hoje.year]
index_ano = anos.index(hoje.year) if hoje.year in anos else 0

with filtro_cols[0]:
    mes_selecionado = st.selectbox(
        "Mês",
        options=meses_keys,
        format_func=lambda x: "Todos" if x == "Todos" else meses[x],
        index=index_mes
    )
with filtro_cols[1]:
    ano_selecionado = st.selectbox("Ano", options=anos, index=index_ano)

# ==== filtragem para gráfico/tabela ====
df_filtrado = df.copy()
if mes_selecionado != "Todos":
    df_filtrado = df_filtrado[df_filtrado["data"].dt.month == mes_selecionado]
df_filtrado = df_filtrado[df_filtrado["data"].dt.year == ano_selecionado]

# ================= Lançamentos Próximos ==========================
st.markdown("### Lançamentos Próximos")
conta_id_filtro = contas_dict.get(conta_filtro) if conta_filtro != "Todas" else None
proximos_lancamentos = database.get_proximos_lancamentos(user_id, dias_futuros=3, conta_id=conta_id_filtro)
if not proximos_lancamentos:
    st.info("Nenhum lançamento previsto para os próximos 3 dias.")
else:
    st.write("Fique de olho nas suas próximas movimentações:")
    for data_lanc, desc, val, tipo in proximos_lancamentos:
        hoje_dt = utils.get_local_today()
        if data_lanc == hoje_dt:
            dia_str = "Hoje"
        elif data_lanc == hoje_dt + datetime.timedelta(days=1):
            dia_str = "Amanhã"
        else:
            dia_str = data_lanc.strftime('%d/%m/%Y')
        valor_formatado = utils.formatar_moeda_brl(val)
        if tipo == 'receita':
            st.success(f"**{dia_str}:** {desc.upper()} | **+ {valor_formatado}**", icon="💰")
        else:
            st.error(f"**{dia_str}:** {desc.upper()} | **- {valor_formatado}**", icon="💸")

st.markdown("---")

# --- FLUXO DE CAIXA DIÁRIO (CÁLCULO E EXIBIÇÃO) ---

if df.empty:
    st.info("Você ainda não possui transações para exibir o fluxo de caixa.")
else:
    df = df.sort_values(by="data")
    df['entradas'] = df['valor'].apply(lambda x: x if x > 0 else 0)
    df['saidas'] = df['valor'].apply(lambda x: abs(x) if x < 0 else 0)

    # FLUXO CONSOLIDADO (para saldo real até hoje)
    fluxo_tudo = df.groupby('data').agg(
        entradas=('entradas', 'sum'),
        saidas=('saidas', 'sum')
    ).reset_index()
    fluxo_tudo['saldo_dia'] = fluxo_tudo['entradas'] - fluxo_tudo['saidas']
    fluxo_tudo['saldo_acumulado'] = fluxo_tudo['saldo_dia'].cumsum()
    saldo_atual_valor = fluxo_tudo[fluxo_tudo['data'].dt.date <= utils.get_local_today()]['saldo_acumulado'].iloc[-1] if not fluxo_tudo.empty else 0.0

    st.metric("Saldo Atual Consolidado (Hoje)", utils.formatar_moeda_brl(saldo_atual_valor))
    st.markdown("---")

    # --- BLOCO COM A CORREÇÃO ---
    if not df_filtrado.empty:
        df_temp = df_filtrado.copy().sort_values(by="data")
        df_temp['entradas'] = df_temp['valor'].apply(lambda x: x if x > 0 else 0)
        df_temp['saidas'] = df_temp['valor'].apply(lambda x: abs(x) if x < 0 else 0)
        fluxo_diario = df_temp.groupby('data').agg(
            entradas=('entradas', 'sum'),
            saidas=('saidas', 'sum')
        ).reset_index()

        if not fluxo_diario.empty:
            data_inicio = fluxo_diario['data'].min()
            data_fim_transacoes = fluxo_diario['data'].max()
            data_fim_hoje = pd.to_datetime(utils.get_local_today())
            data_fim = max(data_fim_transacoes, data_fim_hoje)
            todos_os_dias = pd.date_range(start=data_inicio, end=data_fim, freq='D')
            fluxo_diario = fluxo_diario.set_index('data').reindex(todos_os_dias, fill_value=0).reset_index().rename(columns={'index': 'data'})
            fluxo_diario['saldo_dia'] = fluxo_diario['entradas'] - fluxo_diario['saidas']

            # CORREÇÃO: calcular saldo até o dia anterior ao início do filtro!
            saldo_ate_dia_anterior = df[df['data'] < data_inicio]['valor'].sum() if not df.empty else 0.0
            fluxo_diario['saldo_acumulado'] = fluxo_diario['saldo_dia'].cumsum() + saldo_ate_dia_anterior

            st.line_chart(
                fluxo_diario.rename(columns={'data': 'index'}).set_index('index')['saldo_acumulado']
            )
            st.markdown("---")

            def highlight_today(row):
                if row.data.date() == utils.get_local_today():
                    return ['background-color: #3D5320'] * len(row)
                return [''] * len(row)

            df_display = fluxo_diario.sort_values(by="data", ascending=True)[
                ["data", "entradas", "saidas", "saldo_acumulado"]]
            vmin = 500
            vmax = df_display["saldo_acumulado"].max()

            styled_df = (
                df_display.style
                .apply(highlight_today, axis=1)
                .format({
                    "entradas": utils.formatar_moeda_brl,
                    "saidas": utils.formatar_moeda_brl,
                    "saldo_acumulado": utils.formatar_moeda_brl
                })
                .background_gradient(subset=["saldo_acumulado"], cmap="RdYlGn", vmin=vmin, vmax=vmax)  # Aplica gradiente na coluna saldo
                .hide(axis="index")
            )
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
        else:
            st.info("Não há dados suficientes para o gráfico/tabela no período/conta filtrado.")
    else:
        st.info("Não há dados para o período/conta filtrado selecionado.")









