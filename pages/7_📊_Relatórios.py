import streamlit as st
import database
import pandas as pd
import datetime
import plotly.express as px 
from dateutil.relativedelta import relativedelta
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# --- Conteúdo da Página ---

st.title("Relatórios Financeiros")

# --- FILTROS ---
st.markdown("### Filtros")
# Define o primeiro e o último dia do mês atual como padrão
today = utils.get_local_today()
start_of_month = today.replace(day=1)
end_of_month = (start_of_month + relativedelta(months=1)) - datetime.timedelta(days=1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data de Início", value=start_of_month)
with col2:
    end_date = st.date_input("Data de Fim", value=end_of_month)

st.markdown("---")

# --- GRÁFICO DE DESPESAS POR CATEGORIA (PIZZA) ---
st.markdown("### Para onde foi meu dinheiro?")
despesas_cat = database.get_despesas_por_categoria(user_id, start_date.isoformat(), end_date.isoformat())

if not despesas_cat:
    st.info("Nenhuma despesa encontrada no período selecionado.")
else:
    df_despesas_cat = pd.DataFrame(despesas_cat, columns=['Categoria', 'Total'])
    fig = px.pie(df_despesas_cat, names='Categoria', values='Total', 
                    title='Distribuição de Despesas', hole=.3)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")



# --- HISTÓRICO MENSAL (RECEITA VS DESPESA) ---
st.markdown("### Histórico mensal")
receitas_mensal = database.get_total_receitas_mensal(user_id)
despesas_mensal = database.get_total_despesas_mensal(user_id)

if not receitas_mensal and not despesas_mensal:
    st.info("Nenhuma movimentação mensal encontrada para gerar o histórico.")
else:
    df_receitas = pd.DataFrame(receitas_mensal, columns=['Mês', 'Receitas'])
    df_despesas = pd.DataFrame(despesas_mensal, columns=['Mês', 'Despesas'])
    
    # Junta os dois DataFrames para ter uma única fonte para o gráfico
    df_historico = pd.merge(df_receitas, df_despesas, on='Mês', how='outer').fillna(0)
    df_historico = df_historico.sort_values(by='Mês').set_index('Mês')
    
    st.bar_chart(df_historico)

st.markdown("---")
st.markdown("### Acompanhamento do orçamento no período")

# 1. Pega os gastos e os orçamentos (código existente)
# A função get_despesas_por_categoria já foi chamada no início do script.
df_despesas_cat = pd.DataFrame(despesas_cat, columns=['Categoria', 'Total']) if despesas_cat else pd.DataFrame(columns=['Categoria', 'Total'])
orcamentos = database.get_orcamentos(user_id)
df_orcamentos = pd.DataFrame(orcamentos, columns=['Categoria', 'Orçamento'])

if df_orcamentos.empty:
    st.info("Você ainda não definiu nenhum orçamento. Vá para a página 'Orçamento' para começar.")
else:
    # 2. Junta as informações de gastos e orçamentos
    # Usamos um 'outer' join para incluir categorias com orçamento mas sem gastos no período
    df_comparativo = pd.merge(df_orcamentos, df_despesas_cat, on='Categoria', how='outer').fillna(0)
    
    # Filtra apenas as categorias que têm um orçamento definido > 0
    df_comparativo = df_comparativo[df_comparativo['Orçamento'] > 0].reset_index(drop=True)

    if df_comparativo.empty:
        st.info("Nenhum gasto nas categorias com orçamento definido para este período.")
    else:
        # Calcula as colunas de progresso e restante
        # Adicionado um tratamento para evitar divisão por zero se o orçamento for 0
        df_comparativo['Progresso'] = (df_comparativo['Total'] / df_comparativo['Orçamento']).where(df_comparativo['Orçamento'] > 0, 0)
        df_comparativo['Restante'] = df_comparativo['Orçamento'] - df_comparativo['Total']

        # --- INÍCIO DA NOVA VISUALIZAÇÃO APRIMORADA ---

        for _, row in df_comparativo.iterrows():
            st.markdown(f"#### {row['Categoria']}")
            
            progresso = row['Progresso']
            
            # Lógica para definir a cor e o status com base no progresso
            if progresso > 1:
                status_color_method = st.error
                status_text = f"Orçamento estourado em R$ {utils.formatar_moeda_brl(abs(row['Restante']))}"
            elif progresso >= 0.8:
                status_color_method = st.warning
                status_text = f"Atenção: próximo do limite. Restam R$ {utils.formatar_moeda_brl(row['Restante'])}"
            else:
                status_color_method = st.success
                status_text = f"Dentro do orçamento. Restam R$ {utils.formatar_moeda_brl(row['Restante'])}"

            # Exibe as métricas em colunas
            col1, col2 = st.columns(2)
            col1.metric("Gasto Atual", f"R$ {utils.formatar_moeda_brl(row['Total'])}")
            col2.metric("Orçamento Total", f"R$ {utils.formatar_moeda_brl(row['Orçamento'])}")

            # Barra de progresso visual
            st.progress(min(progresso, 1.0))
            
            # Exibe o texto de status com a cor apropriada
            status_color_method(status_text)
            
            st.markdown("---") # Separador para a próxima categoria
