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
tab_investimentos, tab_despesas, tab_orcamento = st.tabs(
    ["Investimentos", "Despesas", "Orçamento"]
)

with tab_despesas:
    # Sub-abas dentro de Despesas
    subtab_cat, subtab_subcat = st.tabs(
        ["Por Categoria (atual)", "Por Subcategoria"]
    )

    # ==========================
    # SUBABA: POR CATEGORIA (CÓDIGO EXISTENTE)
    # ==========================
    with subtab_cat:
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
        st.markdown("### Para onde foi meu dinheiro? (por categoria)")

        despesas_cat = database.get_despesas_por_categoria(
            user_id, start_date.isoformat(), end_date.isoformat()
        )

        if not despesas_cat:
            st.info("Nenhuma despesa encontrada no período selecionado.")
        else:
            df_despesas_cat = pd.DataFrame(despesas_cat, columns=["Categoria", "Total"])
            fig = px.pie(
                df_despesas_cat,
                names="Categoria",
                values="Total",
                title="Distribuição de Despesas por Categoria",
                hole=0.3,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # --- HISTÓRICO MENSAL (RECEITA VS DESPESA) ---
        st.markdown("### Histórico mensal")

        receitas_mensal = database.get_total_receitas_mensal(user_id)
        despesas_mensal = database.get_total_despesas_mensal(user_id)

        if not receitas_mensal and not despesas_mensal:
            st.info("Nenhuma movimentação mensal encontrada para gerar o histórico.")
        else:
            df_receitas = pd.DataFrame(receitas_mensal, columns=["Mês", "Receitas"])
            df_despesas = pd.DataFrame(despesas_mensal, columns=["Mês", "Despesas"])

            # Junta os dois DataFrames para ter uma única fonte para o gráfico
            df_historico = pd.merge(
                df_receitas, df_despesas, on="Mês", how="outer"
            ).fillna(0)
            df_historico = df_historico.sort_values(by="Mês").set_index("Mês")

            st.bar_chart(df_historico)

    # ==========================
    # SUBABA: POR SUBCATEGORIA (NOVA)
    # ==========================
    with subtab_subcat:
        st.markdown("### Filtros (Subcategorias)")

        # Mesmo padrão de datas
        today = utils.get_local_today()
        start_of_month = today.replace(day=1)
        end_of_month = (start_of_month + relativedelta(months=1)) - datetime.timedelta(
            days=1
        )

        col1, col2 = st.columns(2)
        with col1:
            start_date_sub = st.date_input(
                "Data de Início", value=start_of_month, key="inicio_sub"
            )
        with col2:
            end_date_sub = st.date_input(
                "Data de Fim", value=end_of_month, key="fim_sub"
            )

        st.markdown("---")
        st.markdown("### Despesas por Subcategoria")

        # Aqui você precisa de uma função que traga despesas já associadas à subcategoria.
        # Supondo que tenha criado algo como:
        # get_despesas_por_subcategoria(user_id, data_inicio, data_fim)
        # que retorne: [(subcategoria_nome, total), ...]
        try:
            despesas_sub = database.get_despesas_por_subcategoria(
                user_id, start_date_sub.isoformat(), end_date_sub.isoformat()
            )
        except AttributeError:
            despesas_sub = []

        if not despesas_sub:
            st.info(
                "Nenhuma despesa por subcategoria encontrada no período selecionado "
                "ou função get_despesas_por_subcategoria ainda não implementada."
            )
        else:
            df_despesas_sub = pd.DataFrame(
                despesas_sub, columns=["Subcategoria", "Total"]
            )

            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("#### Gráfico de Pizza")
                fig_sub_pie = px.pie(
                    df_despesas_sub,
                    names="Subcategoria",
                    values="Total",
                    title="Distribuição de Despesas por Subcategoria",
                    hole=0.3,
                )
                st.plotly_chart(fig_sub_pie, use_container_width=True)

            with col_g2:
                st.markdown("#### Gráfico de Barras")
                fig_sub_bar = px.bar(
                    df_despesas_sub,
                    x="Subcategoria",
                    y="Total",
                    title="Total de Despesas por Subcategoria",
                )
                fig_sub_bar.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_sub_bar, use_container_width=True)

            st.markdown("#### Detalhes em tabela")
            st.dataframe(
                df_despesas_sub.sort_values("Total", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

with tab_orcamento:
    st.markdown("---")
    st.markdown("### Acompanhamento do orçamento no período")

    # Reaproveita despesas_cat calculado na aba de categoria; se não existir, calcula de novo
    today = utils.get_local_today()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + relativedelta(months=1)) - datetime.timedelta(
        days=1
    )
    despesas_cat = database.get_despesas_por_categoria(
        user_id, start_of_month.isoformat(), end_of_month.isoformat()
    )

    df_despesas_cat = (
        pd.DataFrame(despesas_cat, columns=["Categoria", "Total"])
        if despesas_cat
        else pd.DataFrame(columns=["Categoria", "Total"])
    )

    orcamentos = database.get_orcamentos(user_id)
    df_orcamentos = pd.DataFrame(orcamentos, columns=["Categoria", "Orçamento"])

    if df_orcamentos.empty:
        st.info(
            "Você ainda não definiu nenhum orçamento. Vá para a página 'Orçamento' para começar."
        )
    else:
        # Junta gastos e orçamentos
        df_comparativo = pd.merge(
            df_orcamentos, df_despesas_cat, on="Categoria", how="outer"
        ).fillna(0)

        # Filtra apenas categorias com orçamento > 0
        df_comparativo = df_comparativo[df_comparativo["Orçamento"] > 0].reset_index(
            drop=True
        )

        if df_comparativo.empty:
            st.info("Nenhum gasto nas categorias com orçamento definido para este período.")
        else:
            # Calcula progresso e restante
            df_comparativo["Progresso"] = (
                df_comparativo["Total"] / df_comparativo["Orçamento"]
            ).where(df_comparativo["Orçamento"] > 0, 0)
            df_comparativo["Restante"] = (
                df_comparativo["Orçamento"] - df_comparativo["Total"]
            )

            for _, row in df_comparativo.iterrows():
                st.markdown(f"#### {row['Categoria']}")

                progresso = row["Progresso"]

                if progresso > 1:
                    status_color_method = st.error
                    status_text = (
                        f"Orçamento estourado em "
                        f"{utils.formatar_moeda_brl(abs(row['Restante']))}"
                    )
                elif progresso >= 0.8:
                    status_color_method = st.warning
                    status_text = (
                        f"Atenção: próximo do limite. Restam "
                        f"{utils.formatar_moeda_brl(row['Restante'])}"
                    )
                else:
                    status_color_method = st.success
                    status_text = (
                        f"Dentro do orçamento. Restam "
                        f"{utils.formatar_moeda_brl(row['Restante'])}"
                    )

                col1, col2 = st.columns(2)
                col1.metric("Gasto Atual", f"{utils.formatar_moeda_brl(row['Total'])}")
                col2.metric(
                    "Orçamento Total", f"{utils.formatar_moeda_brl(row['Orçamento'])}"
                )

                st.progress(min(progresso, 1.0))
                status_color_method(status_text)
                st.markdown("---")

with tab_investimentos:
    st.markdown("### Resultados de Investimentos")

    # --- OPERAÇÕES NORMAIS (COMPRA E VENDA) ---
    st.header("Resultados com Operações Compra e Venda")

    resultados_normais = database.get_resultados_operacoes_normais_por_ativo(user_id)

    if not resultados_normais:
        st.info(
            "Você ainda não possui resultados de operações de compra e venda finalizadas (trades)."
        )
    else:
        df_resultados_normais = pd.DataFrame(
            resultados_normais,
            columns=["Ativo", "Resultado Total (R$)", "Nº de Vendas"],
        )

        resultado_geral_normais = df_resultados_normais["Resultado Total (R$)"].sum()

        st.metric(
            label="Resultado Geral com Trades",
            value=f"{utils.formatar_moeda_brl(resultado_geral_normais)}",
        )

        st.subheader("Detalhes por Ativo")

        df_resultados_normais["Resultado Total (R$)"] = df_resultados_normais[
            "Resultado Total (R$)"
        ].apply(utils.formatar_moeda_brl)

        st.dataframe(
            df_resultados_normais, use_container_width=True, hide_index=True
        )

        st.markdown("---")

    # --- OPERAÇÕES ESTRUTURADAS ---
    st.header("Resultados com Operações Estruturadas")

    resultados_ops = database.get_resultados_operacoes_estruturadas_por_ativo(user_id)

    if not resultados_ops:
        st.info("Você ainda não possui resultados de operações estruturadas finalizadas.")
    else:
        df_resultados = pd.DataFrame(
            resultados_ops,
            columns=["Ativo Subjacente", "Resultado Total (R$)", "Nº de Operações"],
        )

        resultado_geral = df_resultados["Resultado Total (R$)"].sum()

        st.metric(
            label="Resultado Geral com Operações Estruturadas",
            value=f"{utils.formatar_moeda_brl(resultado_geral)}",
        )

        st.subheader("Detalhes por Ativo")

        df_resultados["Resultado Total (R$)"] = df_resultados["Resultado Total (R$)"].apply(
            utils.formatar_moeda_brl
        )

        st.dataframe(df_resultados, use_container_width=True, hide_index=True)
