# ETL com Pentaho Data Integration (Kettle)

Este diretório documenta o processo ETL equivalente ao script Python, para uso com **Pentaho Data Integration (PDI)**.

## Arquitetura do Job

```
[Superstore_e-commerce.xlsx]
        │
        ▼
┌───────────────────┐
│ Excel Input       │  Lê planilha "Orders" ou primeira aba
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Select Values     │  Renomeia colunas para padrão do DW
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Calculator        │  margem_lucro_pct = (Profit/Sales)*100
└─────────┬─────────┘
          ├──────────────────────────────────────┐
          ▼                                      ▼
┌───────────────────┐                 ┌───────────────────┐
│ Dimension Lookup  │                 │ Dimension Lookup  │
│ dim_tempo (pedido)│                 │ dim_produto       │
└─────────┬─────────┘                 └─────────┬─────────┘
          │                                      │
          ▼                                      ▼
┌───────────────────┐                 ┌───────────────────┐
│ Dimension Lookup  │                 │ Table Output      │
│ dim_cliente       │                 │ fato_vendas       │
└───────────────────┘                 └───────────────────┘
```

## Transformações (`.ktr`) sugeridas

| Arquivo | Função |
|---------|--------|
| `01_stg_superstore.ktr` | Extração do XLSX e limpeza |
| `02_load_dimensoes.ktr` | Carga de dim_tempo, dim_produto, dim_cliente, dim_localizacao, dim_envio |
| `03_load_fato.ktr` | Carga de fato_vendas com lookups dimensionais |
| `job_superstore.kjb` | Orquestra as transformações em sequência |

## Mapeamento de Campos (Excel → DW)

| Excel | Tabela.Coluna |
|-------|---------------|
| Order Date | dim_tempo.data (sk_tempo_pedido) |
| Ship Date | dim_tempo.data (sk_tempo_envio) |
| Product ID | dim_produto.product_id |
| Customer ID | dim_cliente.customer_id |
| Region, State, City, Country, Postal Code | dim_localizacao |
| Ship Mode | dim_envio.ship_mode |
| Sales | fato_vendas.vendas |
| Quantity | fato_vendas.quantidade |
| Discount | fato_vendas.desconto |
| Profit | fato_vendas.lucro |

## Conexão PostgreSQL no Pentaho

- **Host:** localhost
- **Porta:** 5433 (mapeada pelo Docker)
- **Database:** superstore_dw
- **Schema:** dw
- **Usuário:** dw_user
- **Senha:** dw_pass

## Execução

1. Suba o PostgreSQL: `docker compose up postgres -d`
2. Abra o Spoon (PDI) e importe as transformações
3. Configure a conexão PostgreSQL
4. Execute `job_superstore.kjb`

> A implementação Python em `etl/etl.py` é funcionalmente equivalente e já está integrada ao `docker-compose.yml`.
