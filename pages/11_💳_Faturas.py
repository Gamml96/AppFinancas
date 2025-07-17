import streamlit as st
import database
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import utils

# --- Guarda de Autenticação ---
profile, user_id, username, credentials, authenticator = utils.check_authentication()

# --- Busca de Dados Iniciais ---
contas = database.get_contas(user_id)
# Filtra apenas as contas que têm dias de fechamento, assumindo que são cartões de crédito.
contas_cartao = [conta for conta in contas if conta[5] is not None and conta[5] > 0]

# --- Conteúdo da Página ---
st.title("Fatura do Cartão de Crédito")

if not contas_cartao:
    st.info("Você não possui contas configuradas como cartão de crédito (com dia de fechamento).")
    st.write("Vá para a aba 'Contas' e edite uma conta, adicionando um valor para 'Dias antes do vencimento para fechar a fatura'.")
    st.stop() # Interrompe a execução se não houver cartões

contas_dict = {conta[1]: conta[0] for conta in contas_cartao}

# --- FILTROS ---
col1, col2 = st.columns([2, 1]) # Dando mais espaço para o seletor de cartão
with col1:
    conta_selecionada_nome = st.selectbox("Selecione o Cartão de Crédito", options=list(contas_dict.keys()))
    conta_selecionada_id = contas_dict[conta_selecionada_nome]

# --- NOVA SEÇÃO: GRÁFICO DE EVOLUÇÃO ---
st.markdown("---")
st.markdown("### Evolução do Valor das Faturas")

historico_data = database.get_historico_faturas(user_id, conta_selecionada_id)

if not historico_data:
    st.info("Não há dados suficientes para gerar um gráfico de evolução para este cartão.")
else:
    df_historico = pd.DataFrame(historico_data, columns=['Mês', 'Valor da Fatura'])
    df_historico = df_historico.set_index('Mês')
    
    # Exibe o gráfico de barras
    st.bar_chart(df_historico, y="Valor da Fatura")

# --- SEÇÃO EXISTENTE: DETALHES DA FATURA SELECIONADA ---
st.markdown("---")
st.markdown("### Detalhes da Fatura Selecionada")

# Gera uma lista de meses e anos para o selectbox de detalhe
with col2:
    # Movemos o seletor de mês para a segunda coluna ao lado do nome do cartão
    meses_anos = sorted(list(set([(utils.get_local_today() + relativedelta(months=i)).strftime("%Y-%m") for i in range(-12, 12)])), reverse=True)
    mes_ano_selecionado = st.selectbox("Ver Fatura de:", options=meses_anos)

ano, mes = map(int, mes_ano_selecionado.split('-'))

# --- EXIBIÇÃO DOS ITENS DA FATURA ---
fatura_itens = database.get_fatura_cartao(user_id, conta_selecionada_id, mes, ano)

if not fatura_itens:
    st.warning(f"Nenhuma despesa encontrada para a fatura de {mes:02d}/{ano} neste cartão.")
else:
    df_fatura = pd.DataFrame(fatura_itens, columns=['Data da Compra', 'Descrição', 'Valor'])
    df_fatura['Data da Compra'] = pd.to_datetime(df_fatura['Data da Compra']).dt.strftime('%d/%m/%Y')
    
    valor_total_fatura = df_fatura['Valor'].sum()

    st.metric(f"Valor Total da Fatura de {mes:02d}/{ano}", f" {utils.formatar_moeda_brl(valor_total_fatura)}")
    
    st.dataframe(
        df_fatura,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn(format="R$ %.2f")
        }
    )
