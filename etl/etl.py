"""
ETL Superstore Sales
Extrai dados de Superstore_e-commerce.xlsx (ou CSV), transforma e carrega no DW PostgreSQL.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def normalize_cep(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text.replace(".0", "") if text.endswith(".0") else text


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "superstore_dw"),
        user=os.environ.get("DB_USER", "dw_user"),
        password=os.environ.get("DB_PASSWORD", "dw_pass"),
    )


def wait_for_db(max_retries=30, delay=2):
    for attempt in range(max_retries):
        try:
            conn = get_connection()
            conn.close()
            print("Conexão com PostgreSQL estabelecida.")
            return
        except psycopg2.OperationalError:
            print(f"Aguardando banco... tentativa {attempt + 1}/{max_retries}")
            time.sleep(delay)
    raise RuntimeError("Não foi possível conectar ao PostgreSQL.")


def find_source_file(data_dir: Path) -> Path:
    candidates = [
        data_dir / "Superstore_e-commerce.xlsx",
        data_dir / "Superstore_e-commerce.xls",
        data_dir / "Superstore_e-commerce.csv",
        data_dir / "Sample-Superstore.csv",
        data_dir / "Sample-Superstore.xlsx",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Arquivo fonte não encontrado em {data_dir}. "
        "Coloque Superstore_e-commerce.xlsx na pasta data/."
    )


def load_raw_data(path: Path) -> pd.DataFrame:
    print(f"Lendo arquivo: {path}")
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=0)
    else:
        df = pd.read_csv(path)

    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    rename_map = {
        # Formato em inglês (Sample Superstore)
        "Row ID": "row_id",
        "Order ID": "order_id",
        "Order Date": "order_date",
        "Ship Date": "ship_date",
        "Ship Mode": "ship_mode",
        "Customer ID": "customer_id",
        "Customer Name": "customer_name",
        "Segment": "segment",
        "Country": "country",
        "City": "city",
        "State": "state",
        "Postal Code": "postal_code",
        "Region": "region",
        "Product ID": "product_id",
        "Category": "category",
        "Sub-Category": "sub_category",
        "Product Name": "product_name",
        "Sales": "sales",
        "Quantity": "quantity",
        "Discount": "discount",
        "Profit": "profit",
        # Formato em português (Superstore_e-commerce.xlsx oficial)
        "ID_Linha": "row_id",
        "ID_Pedido": "order_id",
        "Dta_Pedido": "order_date",
        "Dta_Envio": "ship_date",
        "Envio_Forma": "ship_mode",
        "ID_Cliente": "customer_id",
        "Nme_Cliente": "customer_name",
        "Segmento": "segment",
        "Pais": "country",
        "Cidade": "city",
        "Estado": "state",
        "Codigo_Postal": "postal_code",
        "Regiao": "region",
        "ID_Produto": "product_id",
        "Categoria_Produto": "category",
        "Sub-categoria_Produto": "sub_category",
        "Nme_Produto": "product_name",
        "Vendas": "sales",
        "Quantidade_Itens": "quantity",
        "Desconto": "discount",
        "Lucro": "profit",
    }
    df = df.rename(columns=rename_map)
    required = [
        "row_id", "order_id", "order_date", "ship_date", "ship_mode",
        "customer_id", "customer_name", "segment", "country", "city",
        "state", "postal_code", "region", "product_id", "category",
        "sub_category", "product_name", "sales", "quantity", "profit",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no arquivo fonte: {missing}")

    if "discount" not in df.columns:
        df["discount"] = 0.0

    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ship_date"] = pd.to_datetime(df["ship_date"])
    df["postal_code"] = df["postal_code"].apply(normalize_cep)
    return df


def build_tempo_rows(dates: pd.Series) -> list:
    unique_dates = sorted(dates.dropna().dt.date.unique())
    rows = []
    for d in unique_dates:
        dt = datetime.combine(d, datetime.min.time())
        rows.append((
            d,
            d.day,
            d.month,
            d.year,
            (d.month - 1) // 3 + 1,
            1 if d.month <= 6 else 2,
            MESES[d.month],
            f"Q{(d.month - 1) // 3 + 1}",
            f"{d.year}-{d.month:02d}",
            d.weekday(),
            DIAS[d.weekday()],
        ))
    return rows


def dedupe_rows(rows: list, key_index: int = 0) -> list:
    """Remove duplicatas no mesmo lote (exigido pelo ON CONFLICT do PostgreSQL)."""
    seen = set()
    unique = []
    for row in rows:
        key = row[key_index]
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def upsert_dimension(conn, table: str, columns: list, rows: list, conflict_col: str,
                     select_sql: str, key_index: int = 0) -> dict:
    if not rows:
        return {}
    rows = dedupe_rows(rows, key_index)
    placeholders = ", ".join(columns)
    update_cols = [c for c in columns if c != conflict_col]
    if update_cols:
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
        on_conflict = f"ON CONFLICT ({conflict_col}) DO UPDATE SET {updates}"
    else:
        on_conflict = f"ON CONFLICT ({conflict_col}) DO NOTHING"
    sql = f"INSERT INTO dw.{table} ({placeholders}) VALUES %s {on_conflict}"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
        cur.execute(select_sql)
        return {row[0]: row[1] for row in cur.fetchall()}


def load_dimensions(conn, df: pd.DataFrame) -> dict:
    tempo_rows = build_tempo_rows(pd.concat([df["order_date"], df["ship_date"]]))
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO dw.dim_tempo
                (data, dia, mes, ano, trimestre, semestre, nome_mes, nome_trimestre,
                 ano_mes, dia_semana, nome_dia_semana)
            VALUES %s
            ON CONFLICT (data) DO NOTHING
            """,
            tempo_rows,
        )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT data, sk_tempo FROM dw.dim_tempo")
        tempo_map = {row[0]: row[1] for row in cur.fetchall()}

    produto_rows = (
        df[["product_id", "product_name", "category", "sub_category"]]
        .drop_duplicates(subset=["product_id"], keep="first")
    )
    produto_rows = [
        (r.product_id, r.product_name, r.category, r.sub_category)
        for r in produto_rows.itertuples(index=False)
    ]
    produto_map = upsert_dimension(
        conn, "dim_produto",
        ["product_id", "nome_produto", "categoria", "subcategoria"],
        produto_rows, "product_id",
        "SELECT product_id, sk_produto FROM dw.dim_produto",
    )

    cliente_rows = (
        df[["customer_id", "customer_name", "segment"]]
        .drop_duplicates(subset=["customer_id"], keep="first")
    )
    cliente_rows = [
        (r.customer_id, r.customer_name, r.segment)
        for r in cliente_rows.itertuples(index=False)
    ]
    cliente_map = upsert_dimension(
        conn, "dim_cliente",
        ["customer_id", "nome_cliente", "segmento"],
        cliente_rows, "customer_id",
        "SELECT customer_id, sk_cliente FROM dw.dim_cliente",
    )

    loc_df = df[["country", "region", "state", "city", "postal_code"]].copy()
    loc_df["postal_code"] = loc_df["postal_code"].apply(normalize_cep)
    loc_df = loc_df.drop_duplicates(
        subset=["country", "region", "state", "city", "postal_code"], keep="first"
    )
    loc_rows = [
        (r.country, r.region, r.state, r.city, r.postal_code)
        for r in loc_df.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO dw.dim_localizacao (pais, regiao, estado, cidade, cep)
            VALUES %s
            ON CONFLICT (pais, regiao, estado, cidade, cep) DO NOTHING
            """,
            list(dict.fromkeys(loc_rows)),
        )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT pais, regiao, estado, cidade, cep, sk_localizacao "
            "FROM dw.dim_localizacao"
        )
        loc_map = {(r[0], r[1], r[2], r[3], normalize_cep(r[4])): r[5] for r in cur.fetchall()}

    envio_rows = [(m,) for m in df["ship_mode"].drop_duplicates().tolist()]
    envio_map = upsert_dimension(
        conn, "dim_envio", ["ship_mode"], envio_rows, "ship_mode",
        "SELECT ship_mode, sk_envio FROM dw.dim_envio",
    )

    return {
        "tempo": tempo_map,
        "produto": produto_map,
        "cliente": cliente_map,
        "localizacao": loc_map,
        "envio": envio_map,
    }


def load_fact(conn, df: pd.DataFrame, maps: dict):
    with conn.cursor() as cur:
        cur.execute("TRUNCATE dw.fato_vendas RESTART IDENTITY")
    conn.commit()

    fact_rows = []
    for row in df.itertuples(index=False):
        vendas = float(row.sales)
        lucro = float(row.profit)
        margem = round((lucro / vendas) * 100, 4) if vendas else 0.0
        loc_key = (row.country, row.region, row.state, row.city, normalize_cep(row.postal_code))
        fact_rows.append((
            int(row.row_id),
            row.order_id,
            maps["tempo"][row.order_date.date()],
            maps["tempo"][row.ship_date.date()],
            maps["produto"][row.product_id],
            maps["cliente"][row.customer_id],
            maps["localizacao"][loc_key],
            maps["envio"][row.ship_mode],
            vendas,
            int(row.quantity),
            float(row.discount),
            lucro,
            margem,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO dw.fato_vendas
                (row_id, order_id, sk_tempo_pedido, sk_tempo_envio, sk_produto,
                 sk_cliente, sk_localizacao, sk_envio, vendas, quantidade,
                 desconto, lucro, margem_lucro_pct)
            VALUES %s
            """,
            fact_rows,
        )
    conn.commit()
    print(f"Carga concluída: {len(fact_rows)} registros em fato_vendas.")


def apply_views(conn):
    views_path = Path("/sql/02_views_analiticas.sql")
    if not views_path.exists():
        views_path = Path(__file__).resolve().parent.parent / "sql" / "02_views_analiticas.sql"
    sql = views_path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("Views analíticas criadas/atualizadas.")


def run_etl():
    wait_for_db()
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    source = find_source_file(data_dir)
    df = load_raw_data(source)
    print(f"Registros extraídos: {len(df)}")

    conn = get_connection()
    try:
        maps = load_dimensions(conn, df)
        load_fact(conn, df, maps)
        apply_views(conn)
    finally:
        conn.close()

    print("ETL finalizado com sucesso.")


if __name__ == "__main__":
    try:
        run_etl()
    except Exception as exc:
        print(f"ERRO no ETL: {exc}", file=sys.stderr)
        sys.exit(1)
