-- Views analíticas para o front-end e relatórios de negócio
SET search_path TO dw, public;

-- Visão consolidada para exploração geral
CREATE OR REPLACE VIEW vw_vendas_detalhadas AS
SELECT
    f.row_id,
    f.order_id,
    tp.data AS data_pedido,
    tp.ano_mes,
    tp.ano,
    tp.mes,
    tp.nome_mes,
    te.data AS data_envio,
    e.ship_mode AS modo_envio,
    c.customer_id,
    c.nome_cliente,
    c.segmento AS tipo_cliente,
    l.regiao,
    l.estado,
    l.cidade,
    l.pais,
    p.product_id,
    p.nome_produto,
    p.categoria,
    p.subcategoria,
    f.vendas,
    f.quantidade,
    f.desconto,
    f.lucro,
    f.margem_lucro_pct
FROM fato_vendas f
JOIN dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
JOIN dim_tempo te ON f.sk_tempo_envio = te.sk_tempo
JOIN dim_produto p ON f.sk_produto = p.sk_produto
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
JOIN dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
JOIN dim_envio e ON f.sk_envio = e.sk_envio;

-- Receita e lucro por subcategoria
CREATE OR REPLACE VIEW vw_receita_lucro_subcategoria AS
SELECT
    p.categoria,
    p.subcategoria,
    SUM(f.vendas) AS receita_total,
    SUM(f.lucro) AS lucro_total,
    SUM(f.quantidade) AS quantidade_vendida,
    CASE WHEN SUM(f.vendas) > 0
         THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
         ELSE 0 END AS margem_lucro_pct
FROM fato_vendas f
JOIN dim_produto p ON f.sk_produto = p.sk_produto
GROUP BY p.categoria, p.subcategoria;

-- Rentabilidade por produto
CREATE OR REPLACE VIEW vw_rentabilidade_produto AS
SELECT
    p.product_id,
    p.nome_produto,
    p.categoria,
    p.subcategoria,
    SUM(f.vendas) AS receita_total,
    SUM(f.lucro) AS lucro_total,
    SUM(f.quantidade) AS quantidade_vendida,
    CASE WHEN SUM(f.vendas) > 0
         THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
         ELSE 0 END AS margem_lucro_pct
FROM fato_vendas f
JOIN dim_produto p ON f.sk_produto = p.sk_produto
GROUP BY p.product_id, p.nome_produto, p.categoria, p.subcategoria;

-- Vendas e lucro por estado
CREATE OR REPLACE VIEW vw_vendas_lucro_estado AS
SELECT
    l.regiao,
    l.estado,
    SUM(f.vendas) AS receita_total,
    SUM(f.lucro) AS lucro_total,
    COUNT(DISTINCT f.order_id) AS total_pedidos,
    COUNT(DISTINCT c.customer_id) AS clientes_unicos,
    CASE WHEN SUM(f.vendas) > 0
         THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
         ELSE 0 END AS margem_lucro_pct
FROM fato_vendas f
JOIN dim_localizacao l ON f.sk_localizacao = l.sk_localizacao
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
GROUP BY l.regiao, l.estado;

-- Hábitos de compra por segmento (tipo de mercado-alvo)
CREATE OR REPLACE VIEW vw_habitos_compra_segmento AS
SELECT
    c.segmento AS tipo_mercado,
    tp.ano_mes,
    tp.ano,
    tp.mes,
    tp.nome_mes,
    COUNT(DISTINCT f.order_id) AS total_pedidos,
    COUNT(DISTINCT c.customer_id) AS clientes_unicos,
    SUM(f.quantidade) AS itens_comprados,
    ROUND(AVG(f.vendas), 2) AS ticket_medio_item,
    SUM(f.vendas) AS receita_total,
    SUM(f.lucro) AS lucro_total
FROM fato_vendas f
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
JOIN dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
GROUP BY c.segmento, tp.ano_mes, tp.ano, tp.mes, tp.nome_mes;

-- Evolução mensal de vendas
CREATE OR REPLACE VIEW vw_vendas_mensais AS
SELECT
    tp.ano_mes,
    tp.ano,
    tp.mes,
    tp.nome_mes,
    c.segmento AS tipo_mercado,
    SUM(f.vendas) AS receita_total,
    SUM(f.lucro) AS lucro_total,
    SUM(f.quantidade) AS quantidade_vendida,
    CASE WHEN SUM(f.vendas) > 0
         THEN ROUND((SUM(f.lucro) / SUM(f.vendas)) * 100, 2)
         ELSE 0 END AS margem_lucro_pct
FROM fato_vendas f
JOIN dim_tempo tp ON f.sk_tempo_pedido = tp.sk_tempo
JOIN dim_cliente c ON f.sk_cliente = c.sk_cliente
GROUP BY tp.ano_mes, tp.ano, tp.mes, tp.nome_mes, c.segmento;
