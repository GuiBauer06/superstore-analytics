"""
Dashboard analítico Superstore Sales
Front-end para exploração do data warehouse e resposta às questões de negócio.
"""

import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="Superstore Sales Analytics",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "superstore_dw"),
        user=os.environ.get("DB_USER", "dw_user"),
        password=os.environ.get("DB_PASSWORD", "dw_pass"),
    )


@st.cache_data(ttl=300)
def run_query(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def sidebar_filters() -> dict:
    st.sidebar.header("Filtros")
    segmentos = run_query(
        "SELECT DISTINCT segmento FROM dw.dim_cliente ORDER BY segmento"
    )["segmento"].tolist()
    regioes = run_query(
        "SELECT DISTINCT regiao FROM dw.dim_localizacao ORDER BY regiao"
    )["regiao"].tolist()
    categorias = run_query(
        "SELECT DISTINCT categoria FROM dw.dim_produto ORDER BY categoria"
    )["categoria"].tolist()
    anos = run_query(
        "SELECT DISTINCT ano FROM dw.dim_tempo ORDER BY ano"
    )["ano"].tolist()

    return {
        "segmentos": st.sidebar.multiselect("Tipo de cliente", segmentos, default=segmentos),
        "regioes": st.sidebar.multiselect("Região", regioes, default=regioes),
        "categorias": st.sidebar.multiselect("Categoria", categorias, default=categorias),
        "anos": st.sidebar.multiselect("Ano", anos, default=anos),
    }


def build_where(filters: dict) -> tuple[str, list]:
    clauses = []
    params = []
    if filters["segmentos"]:
        clauses.append("c.segmento = ANY(%s)")
        params.append(filters["segmentos"])
    if filters["regioes"]:
        clauses.append("l.regiao = ANY(%s)")
        params.append(filters["regioes"])
    if filters["categorias"]:
        clauses.append("p.categoria = ANY(%s)")
        params.append(filters["categorias"])
    if filters["anos"]:
        clauses.append("tp.ano = ANY(%s)")
        params.append(filters["anos"])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def kpi_cards(filters: dict):
    where, params = build_where(filters)
    sql = f"""
        SELECT
            COALESCE(SUM(f.vendas), 0) AS receita,
            COALESCE(SUM(f.lucro), 0) AS lucro,
            COALESCE(SUM(f.quantidade), 0) AS itens,
            CASE WHEN SUM(f.vendas) > 0
                 THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
                 ELSE 0 END AS margem
        FROM dw.fato_vendas f
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        {where}
    """
    row = run_query(sql, params).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Total", format_currency(row["receita"]))
    c2.metric("Lucro Total", format_currency(row["lucro"]))
    c3.metric("Itens Vendidos", f"{int(row['itens']):,}")
    c4.metric("Margem de Lucro", f"{row['margem']:.2f}%")


def tab_subcategorias(filters: dict):
    st.subheader("Receita e Lucro por Subcategoria")
    where, params = build_where(filters)
    sql = f"""
        SELECT p.categoria, p.subcategoria,
               SUM(f.vendas) AS receita, SUM(f.lucro) AS lucro
        FROM dw.fato_vendas f
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        {where}
        GROUP BY p.categoria, p.subcategoria
        ORDER BY receita DESC
    """
    df = run_query(sql, params)
    if df.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    top = df.nlargest(10, "receita")
    bottom = df.nsmallest(10, "receita")
    fig_top = px.bar(
        top, x="subcategoria", y="receita", color="categoria",
        title="Top 10 Subcategorias por Receita", text_auto=".2s",
    )
    fig_bottom = px.bar(
        bottom, x="subcategoria", y="lucro", color="categoria",
        title="10 Subcategorias com Menor Receita (Lucro)", text_auto=".2s",
    )
    col1.plotly_chart(fig_top, use_container_width=True)
    col2.plotly_chart(fig_bottom, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def tab_produtos(filters: dict):
    st.subheader("Rentabilidade por Produto")
    where, params = build_where(filters)
    sql = f"""
        SELECT p.nome_produto, p.categoria, p.subcategoria,
               SUM(f.vendas) AS receita, SUM(f.lucro) AS lucro,
               CASE WHEN SUM(f.vendas) > 0
                    THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
                    ELSE 0 END AS margem
        FROM dw.fato_vendas f
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        {where}
        GROUP BY p.nome_produto, p.categoria, p.subcategoria
        ORDER BY lucro DESC
    """
    df = run_query(sql, params)
    if df.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    fig_mais = px.bar(
        df.nlargest(15, "lucro"), x="lucro", y="nome_produto",
        orientation="h", title="15 Produtos Mais Rentáveis", color="categoria",
    )
    fig_menos = px.bar(
        df.nsmallest(15, "lucro"), x="lucro", y="nome_produto",
        orientation="h", title="15 Produtos Menos Rentáveis", color="categoria",
    )
    col1.plotly_chart(fig_mais, use_container_width=True)
    col2.plotly_chart(fig_menos, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def tab_estados(filters: dict):
    st.subheader("Vendas e Lucro por Estado")
    where, params = build_where(filters)
    sql = f"""
        SELECT l.regiao, l.estado,
               SUM(f.vendas) AS receita, SUM(f.lucro) AS lucro,
               COUNT(DISTINCT f.order_id) AS pedidos
        FROM dw.fato_vendas f
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        {where}
        GROUP BY l.regiao, l.estado
        ORDER BY receita DESC
    """
    df = run_query(sql, params)
    if df.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    fig = px.treemap(
        df, path=["regiao", "estado"], values="receita",
        color="lucro", color_continuous_scale="RdYlGn",
        title="Mapa de Receita por Região e Estado",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def tab_habitos(filters: dict):
    st.subheader("Hábitos de Compra dos Clientes")
    where, params = build_where(filters)
    sql = f"""
        SELECT c.segmento AS tipo_cliente, tp.ano_mes,
               COUNT(DISTINCT f.order_id) AS pedidos,
               COUNT(DISTINCT c.customer_id) AS clientes,
               SUM(f.quantidade) AS itens,
               ROUND(AVG(f.vendas), 2) AS ticket_medio,
               SUM(f.vendas) AS receita
        FROM dw.fato_vendas f
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        {where}
        GROUP BY c.segmento, tp.ano_mes
        ORDER BY tp.ano_mes, c.segmento
    """
    df = run_query(sql, params)
    if df.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    col1, col2 = st.columns(2)
    fig_pedidos = px.line(
        df, x="ano_mes", y="pedidos", color="tipo_cliente",
        markers=True, title="Pedidos Mensais por Segmento",
    )
    fig_ticket = px.bar(
        df.groupby("tipo_cliente", as_index=False)["ticket_medio"].mean(),
        x="tipo_cliente", y="ticket_medio",
        title="Ticket Médio por Tipo de Cliente", text_auto=".2f",
    )
    col1.plotly_chart(fig_pedidos, use_container_width=True)
    col2.plotly_chart(fig_ticket, use_container_width=True)

    modo_sql = f"""
        SELECT c.segmento, e.ship_mode, COUNT(*) AS qtd
        FROM dw.fato_vendas f
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_envio e ON f.sk_envio = e.sk_envio
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        {where}
        GROUP BY c.segmento, e.ship_mode
    """
    modo_df = run_query(modo_sql, params)
    fig_modo = px.sunburst(
        modo_df, path=["segmento", "ship_mode"], values="qtd",
        title="Preferência de Modo de Envio por Segmento",
    )
    st.plotly_chart(fig_modo, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def tab_mensal(filters: dict):
    st.subheader("Evolução Mensal por Mercado-Alvo")
    where, params = build_where(filters)
    sql = f"""
        SELECT tp.ano_mes, c.segmento AS tipo_mercado,
               SUM(f.vendas) AS receita, SUM(f.lucro) AS lucro,
               CASE WHEN SUM(f.vendas) > 0
                    THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
                    ELSE 0 END AS margem
        FROM dw.fato_vendas f
        JOIN dw.dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
        JOIN dw.dim_cliente c ON f.sk_cliente = c.sk_cliente
        JOIN dw.dim_produto p ON f.sk_produto = p.sk_produto
        JOIN dw.dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
        {where}
        GROUP BY tp.ano_mes, c.segmento
        ORDER BY tp.ano_mes, c.segmento
    """
    df = run_query(sql, params)
    if df.empty:
        st.warning("Sem dados para os filtros selecionados.")
        return

    fig = px.area(
        df, x="ano_mes", y="receita", color="tipo_mercado",
        title="Receita Mensal por Tipo de Mercado-Alvo",
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_margem = px.line(
        df, x="ano_mes", y="margem", color="tipo_mercado",
        markers=True, title="Margem de Lucro Mensal (%)",
    )
    st.plotly_chart(fig_margem, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    st.title("Superstore Sales — Plataforma Analítica")
    st.caption(
        "Análise de vendas, lucratividade e hábitos de compra "
        "a partir do data warehouse dimensional."
    )

    try:
        total = run_query("SELECT COUNT(*) AS n FROM dw.fato_vendas").iloc[0]["n"]
        if total == 0:
            st.error("O data warehouse ainda não foi carregado. Execute o ETL primeiro.")
            return
    except Exception as exc:
        st.error(f"Não foi possível conectar ao banco de dados: {exc}")
        return

    filters = sidebar_filters()
    kpi_cards(filters)

    tabs = st.tabs([
        "Subcategorias",
        "Produtos",
        "Estados",
        "Hábitos de Compra",
        "Análise Mensal",
    ])
    with tabs[0]:
        tab_subcategorias(filters)
    with tabs[1]:
        tab_produtos(filters)
    with tabs[2]:
        tab_estados(filters)
    with tabs[3]:
        tab_habitos(filters)
    with tabs[4]:
        tab_mensal(filters)


if __name__ == "__main__":
    main()
