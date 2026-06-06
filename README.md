# Superstore Sales — Plataforma Analítica

Solução completa de Business Intelligence para a empresa **Superstore Sales**, contemplando modelagem dimensional, ETL e front-end analítico.

## Arquitetura

```
┌─────────────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Superstore_e-       │     │   Processo   │     │   PostgreSQL    │
│ commerce.xlsx       │────►│     ETL      │────►│  (Star Schema)  │
└─────────────────────┘     └──────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Dashboard     │
                                                 │   (Streamlit)   │
                                                 └─────────────────┘
```

## Componentes

| Componente | Tecnologia | Descrição |
|------------|------------|-----------|
| Modelo dimensional | PostgreSQL | Star schema com 5 dimensões e 1 fato |
| ETL | Python (pandas) | Extração XLSX/CSV → transformação → carga |
| ETL alternativo | Pentaho PDI | Documentado em `pentaho/README.md` |
| Front-end | Streamlit + Plotly | Dashboard interativo com filtros |
| Infraestrutura | Docker Compose | Orquestração de todos os serviços |

## Questões de Negócio Atendidas

- **Subcategorias** com mais e menos receita/lucro → aba *Subcategorias*
- **Produtos** mais e menos rentáveis → aba *Produtos*
- **Estados** com mais vendas e lucro → aba *Estados*
- **Hábitos de compra** dos clientes → aba *Hábitos de Compra*
- **Análise mensal** por tipo de mercado-alvo → aba *Análise Mensal*

## Pré-requisitos

- [Docker](https://www.docker.com/) e Docker Compose instalados

## Como Executar

### 1. Dados fonte

Coloque o arquivo `Superstore_e-commerce.xlsx` na pasta `data/`.

> O projeto já inclui `data/Sample-Superstore.csv` (dataset equivalente ao Sample Superstore da Tableau) para execução imediata. O ETL aceita tanto `.xlsx` quanto `.csv`.

### 2. Subir a plataforma

```bash
cd superstore-analytics
docker compose up --build
```

O Docker irá:
1. Criar o banco PostgreSQL e aplicar o schema (`sql/01_schema.sql`)
2. Executar o ETL para carregar os dados
3. Iniciar o dashboard em `http://localhost:8501`

### 3. Acessar o dashboard

Abra no navegador: **http://localhost:8501**

### Comandos úteis

```bash
# Reexecutar apenas o ETL (após trocar o arquivo fonte)
docker compose up etl --build

# Parar todos os serviços
docker compose down

# Parar e remover volumes (limpar banco)
docker compose down -v
```

## Estrutura do Projeto

```
superstore-analytics/
├── data/                          # Arquivo fonte (XLSX/CSV)
├── docs/
│   └── modelagem-dimensional.md   # Modelo lógico e físico
├── sql/
│   ├── 01_schema.sql              # DDL do data warehouse
│   └── 02_views_analiticas.sql    # Views para análises
├── etl/
│   ├── etl.py                     # Script ETL Python
│   └── Dockerfile
├── dashboard/
│   ├── app.py                     # Front-end Streamlit
│   └── Dockerfile
├── pentaho/
│   └── README.md                  # Documentação ETL Pentaho
├── docker-compose.yml
└── README.md
```

## Modelo Dimensional

| Tabela | Tipo | Descrição |
|--------|------|-----------|
| `dim_tempo` | Dimensão | Datas de pedido e envio (role-playing) |
| `dim_produto` | Dimensão | Categoria, subcategoria, produto |
| `dim_cliente` | Dimensão | Cliente e segmento (mercado-alvo) |
| `dim_localizacao` | Dimensão | País, região, estado, cidade |
| `dim_envio` | Dimensão | Modo de envio |
| `fato_vendas` | Fato | Vendas, quantidade, desconto, lucro, margem |

Documentação completa: [docs/modelagem-dimensional.md](docs/modelagem-dimensional.md)

## Conexão ao Banco (desenvolvimento)

| Parâmetro | Valor |
|-----------|-------|
| Host | localhost |
| Porta | 5433 |
| Database | superstore_dw |
| Schema | dw |
| Usuário | dw_user |
| Senha | dw_pass |

## Licença

Projeto acadêmico — Superstore Sales Analytics.
