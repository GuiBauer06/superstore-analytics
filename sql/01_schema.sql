-- Superstore Sales - Modelo Dimensional (Star Schema)
-- SGBD: PostgreSQL

CREATE SCHEMA IF NOT EXISTS dw;
SET search_path TO dw, public;

-- ============================================================
-- DIMENSÃO TEMPO
-- Suporta análises mensais, trimestrais e anuais
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_tempo (
    sk_tempo        SERIAL PRIMARY KEY,
    data            DATE NOT NULL UNIQUE,
    dia             SMALLINT NOT NULL,
    mes             SMALLINT NOT NULL,
    ano             SMALLINT NOT NULL,
    trimestre       SMALLINT NOT NULL,
    semestre        SMALLINT NOT NULL,
    nome_mes        VARCHAR(20) NOT NULL,
    nome_trimestre  VARCHAR(10) NOT NULL,
    ano_mes         VARCHAR(7) NOT NULL,
    dia_semana      SMALLINT NOT NULL,
    nome_dia_semana VARCHAR(15) NOT NULL
);

-- ============================================================
-- DIMENSÃO PRODUTO
-- Categoria, subcategoria e produto
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_produto (
    sk_produto      SERIAL PRIMARY KEY,
    product_id      VARCHAR(50) NOT NULL UNIQUE,
    nome_produto    VARCHAR(255) NOT NULL,
    categoria       VARCHAR(50) NOT NULL,
    subcategoria    VARCHAR(50) NOT NULL
);

-- ============================================================
-- DIMENSÃO CLIENTE
-- Tipo de cliente / mercado-alvo (segmento)
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_cliente (
    sk_cliente      SERIAL PRIMARY KEY,
    customer_id     VARCHAR(50) NOT NULL UNIQUE,
    nome_cliente    VARCHAR(100) NOT NULL,
    segmento        VARCHAR(30) NOT NULL
);

-- ============================================================
-- DIMENSÃO LOCALIZAÇÃO
-- Região, estado e cidade
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_localizacao (
    sk_localizacao  SERIAL PRIMARY KEY,
    pais            VARCHAR(50) NOT NULL,
    regiao          VARCHAR(20) NOT NULL,
    estado          VARCHAR(50) NOT NULL,
    cidade          VARCHAR(100) NOT NULL,
    cep             VARCHAR(20),
    UNIQUE (pais, regiao, estado, cidade, cep)
);

-- ============================================================
-- DIMENSÃO ENVIO
-- Modo de envio do pedido
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_envio (
    sk_envio        SERIAL PRIMARY KEY,
    ship_mode       VARCHAR(30) NOT NULL UNIQUE
);

-- ============================================================
-- TABELA FATO - VENDAS
-- Métricas: vendas, quantidade, desconto, lucro, margem
-- ============================================================
CREATE TABLE IF NOT EXISTS fato_vendas (
    sk_venda            BIGSERIAL PRIMARY KEY,
    row_id              INTEGER NOT NULL UNIQUE,
    order_id            VARCHAR(30) NOT NULL,
    sk_tempo_pedido     INTEGER NOT NULL REFERENCES dim_tempo(sk_tempo),
    sk_tempo_envio      INTEGER NOT NULL REFERENCES dim_tempo(sk_tempo),
    sk_produto          INTEGER NOT NULL REFERENCES dim_produto(sk_produto),
    sk_cliente          INTEGER NOT NULL REFERENCES dim_cliente(sk_cliente),
    sk_localizacao      INTEGER NOT NULL REFERENCES dim_localizacao(sk_localizacao),
    sk_envio            INTEGER NOT NULL REFERENCES dim_envio(sk_envio),
    vendas              NUMERIC(12, 4) NOT NULL,
    quantidade          INTEGER NOT NULL,
    desconto            NUMERIC(6, 4) NOT NULL,
    lucro               NUMERIC(12, 4) NOT NULL,
    margem_lucro_pct    NUMERIC(8, 4) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fato_tempo_pedido ON fato_vendas(sk_tempo_pedido);
CREATE INDEX IF NOT EXISTS idx_fato_produto ON fato_vendas(sk_produto);
CREATE INDEX IF NOT EXISTS idx_fato_cliente ON fato_vendas(sk_cliente);
CREATE INDEX IF NOT EXISTS idx_fato_localizacao ON fato_vendas(sk_localizacao);
CREATE INDEX IF NOT EXISTS idx_fato_order ON fato_vendas(order_id);
