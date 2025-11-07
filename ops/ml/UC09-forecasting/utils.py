import trino
import os

def get_trino_connector():
    """
    Tạo kết nối Trino/Iceberg.
    """
    conn = trino.dbapi.connect(
        host=os.getenv("TRINO_HOST", "trino"),
        port=int(os.getenv("TRINO_PORT", 8080)),
        user="python_script",
        catalog="sme_lake",
        schema="silver",
    )
    return conn