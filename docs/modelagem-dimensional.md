# Modelagem Dimensional - Superstore Sales

## 1. Requisitos de Negócio

| Requisito | Atendimento no modelo |
|-----------|----------------------|
| Valor de vendas, quantidade, lucro e margem | `fato_vendas`: vendas, quantidade, lucro, margem_lucro_pct |
| Análise por categoria, subcategoria e produto | `dim_produto` |
| Análise por tipo de cliente, região, estado e cidade | `dim_cliente` (segmento) + `dim_localizacao` |
| Análise mensal e por mercado-alvo | `dim_tempo` (ano_mes) + `dim_cliente` (segmento) |

## 2. Modelo Lógico (Star Schema)

```
                    ┌─────────────┐
                    │  dim_tempo  │◄─── sk_tempo_pedido
                    │  (pedido)   │◄─── sk_tempo_envio (role-playing)
                    └──────┬──────┘
                           │
┌─────────────┐    ┌───────┴───────┐    ┌──────────────┐
│ dim_produto │◄───│  fato_vendas  │───►│ dim_cliente  │
└─────────────┘    └───────┬───────┘    └──────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌──────────────┐   ┌──────────────┐   ┌─────────────┐
│dim_localizacao│  │  dim_envio   │   │ order_id    │
└──────────────┘   └──────────────┘   │ (degenerada)│
                                       └─────────────┘
```

## 3. Dimensões

### dim_tempo
Granularidade diária. Permite agregações mensais, trimestrais e anuais.

| Atributo | Descrição |
|----------|-----------|
| sk_tempo | Chave substituta |
| data | Data calendário |
| ano_mes | Formato YYYY-MM para filtros mensais |
| segmento temporal | dia, mês, ano, trimestre, semestre |

### dim_produto
| Atributo | Descrição |
|----------|-----------|
| product_id | Chave natural do produto |
| categoria | Furniture, Office Supplies, Technology |
| subcategoria | Bookcases, Chairs, Labels, etc. |
| nome_produto | Nome completo do item |

### dim_cliente
| Atributo | Descrição |
|----------|-----------|
| customer_id | Chave natural do cliente |
| segmento | Consumer, Corporate, Home Office (tipo de mercado-alvo) |

### dim_localizacao
| Atributo | Descrição |
|----------|-----------|
| regiao | East, West, Central, South |
| estado | Estado dos EUA |
| cidade | Cidade do cliente |
| pais | País (United States) |

### dim_envio
| Atributo | Descrição |
|----------|-----------|
| ship_mode | Standard Class, Second Class, First Class, Same Day |

## 4. Fato - fato_vendas

Granularidade: **uma linha por item vendido** (Row ID do arquivo fonte).

| Medida | Fórmula / Origem |
|--------|------------------|
| vendas | Sales (arquivo fonte) |
| quantidade | Quantity |
| desconto | Discount |
| lucro | Profit |
| margem_lucro_pct | (lucro / vendas) × 100 quando vendas > 0 |

## 5. Mapeamento Fonte → Modelo

| Coluna XLSX | Destino |
|-------------|---------|
| Row ID | fato_vendas.row_id |
| Order ID | fato_vendas.order_id |
| Order Date | dim_tempo (pedido) |
| Ship Date | dim_tempo (envio) |
| Ship Mode | dim_envio |
| Customer ID / Name / Segment | dim_cliente |
| Country / Region / State / City / Postal Code | dim_localizacao |
| Product ID / Category / Sub-Category / Product Name | dim_produto |
| Sales / Quantity / Discount / Profit | fato_vendas |

## 6. Questões de Negócio → Views

| Questão | View |
|---------|------|
| Subcategorias com mais/menos receita e lucro | `vw_receita_lucro_subcategoria` |
| Produtos mais/menos rentáveis | `vw_rentabilidade_produto` |
| Estados com mais vendas e lucro | `vw_vendas_lucro_estado` |
| Hábitos de compra dos clientes | `vw_habitos_compra_segmento` |
| Evolução mensal por mercado-alvo | `vw_vendas_mensais` |
