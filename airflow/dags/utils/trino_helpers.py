"""
Utility functions for Trino operations
Các hàm tiện ích cho thao tác với Trino
"""
import trino
from trino.auth import BasicAuthentication
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def get_trino_connection(config: Dict[str, Any]):
    """
    Tạo Trino connection từ config
    
    Args:
        config: Dict chứa trino configuration
    
    Returns:
        Trino connection object
    """
    return trino.dbapi.connect(
        host=config.get('host', 'localhost'),
        port=config.get('port', 8080),
        user=config.get('user', 'trino'),
        catalog=config.get('catalog', 'sme_lake'),
        schema=config.get('schema', 'default'),
        http_scheme='http'
    )


def check_trino_health(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kiểm tra sức khỏe Trino service
    
    Returns:
        Dict với status và message
    """
    try:
        conn = get_trino_connection(config)
        cursor = conn.cursor()
        
        # Simple query để test connection
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result and result[0] == 1:
            return {
                'status': 'healthy',
                'message': 'Trino connection OK'
            }
        else:
            return {
                'status': 'unhealthy',
                'message': 'Unexpected query result'
            }
    
    except Exception as e:
        logger.error(f"Trino connection error: {e}")
        return {
            'status': 'unhealthy',
            'message': f"Connection error: {str(e)}"
        }


def execute_trino_query(
    config: Dict[str, Any],
    query: str,
    catalog: str = None,
    schema: str = None
) -> Dict[str, Any]:
    """
    Thực thi Trino query và trả về kết quả
    
    Args:
        config: Trino config
        query: SQL query string
        catalog: Override catalog (optional)
        schema: Override schema (optional)
    
    Returns:
        Dict với status, rows, columns
    """
    try:
        # Override config if needed
        conn_config = config.copy()
        if catalog:
            conn_config['catalog'] = catalog
        if schema:
            conn_config['schema'] = schema
        
        conn = get_trino_connection(conn_config)
        cursor = conn.cursor()
        
        logger.info(f"Executing query: {query[:100]}...")
        cursor.execute(query)
        
        # Fetch results
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        result_rows = []
        for row in rows:
            result_rows.append(dict(zip(columns, row)))
        
        return {
            'status': 'success',
            'rows': result_rows,
            'columns': columns,
            'row_count': len(result_rows)
        }
    
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def get_table_stats(
    config: Dict[str, Any],
    schema: str,
    table: str
) -> Dict[str, Any]:
    """
    Lấy thống kê về table (row count, size, etc.)
    
    Returns:
        Dict với table statistics
    """
    try:
        # Get row count
        count_query = f"SELECT COUNT(*) as cnt FROM {schema}.{table}"
        count_result = execute_trino_query(config, count_query, schema=schema)
        
        if count_result['status'] != 'success':
            return count_result
        
        row_count = count_result['rows'][0]['cnt'] if count_result['rows'] else 0
        
        # Try to get table properties (Iceberg specific)
        try:
            properties_query = f"SHOW STATS FOR {schema}.{table}"
            properties_result = execute_trino_query(config, properties_query, schema=schema)
            
            stats = {
                'schema': schema,
                'table': table,
                'row_count': row_count,
                'stats': properties_result.get('rows', [])
            }
        except:
            # Fallback if SHOW STATS doesn't work
            stats = {
                'schema': schema,
                'table': table,
                'row_count': row_count
            }
        
        return {
            'status': 'success',
            'stats': stats
        }
    
    except Exception as e:
        logger.error(f"Error getting table stats: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def validate_schema_exists(config: Dict[str, Any], schema: str) -> bool:
    """
    Kiểm tra schema có tồn tại không
    
    Returns:
        True nếu tồn tại, False nếu không
    """
    try:
        query = f"SHOW SCHEMAS LIKE '{schema}'"
        result = execute_trino_query(config, query)
        
        if result['status'] == 'success':
            return len(result['rows']) > 0
        return False
    
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        return False


def validate_table_exists(
    config: Dict[str, Any],
    schema: str,
    table: str
) -> bool:
    """
    Kiểm tra table có tồn tại không
    
    Returns:
        True nếu tồn tại, False nếu không
    """
    try:
        query = f"SHOW TABLES IN {schema} LIKE '{table}'"
        result = execute_trino_query(config, query, schema=schema)
        
        if result['status'] == 'success':
            return len(result['rows']) > 0
        return False
    
    except Exception as e:
        logger.error(f"Error checking table: {e}")
        return False
