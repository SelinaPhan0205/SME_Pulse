"""
Utility functions for dbt operations
Các hàm tiện ích cho thao tác với dbt
"""
import subprocess
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


def run_dbt_command(
    command: str,
    dbt_dir: str = "/opt/airflow/dbt",
    profiles_dir: str = "/opt/airflow/dbt"
) -> Dict[str, Any]:
    """
    Chạy dbt command và parse kết quả
    
    Args:
        command: dbt command (vd: "dbt run --models silver")
        dbt_dir: Thư mục chứa dbt project
        profiles_dir: Thư mục chứa profiles.yml
    
    Returns:
        Dict với status, output, và parsed results
    """
    try:
        # Build full command
        full_command = f"cd {dbt_dir} && {command} --profiles-dir {profiles_dir}"
        
        logger.info(f"Running: {full_command}")
        
        # Execute command
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        # Parse dbt results
        parsed_results = parse_dbt_output(result.stdout, result.stderr)
        
        return {
            'status': 'success' if result.returncode == 0 else 'failed',
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'parsed': parsed_results
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"dbt command timeout after 30 minutes: {command}")
        return {
            'status': 'timeout',
            'message': 'Command exceeded 30 minute timeout'
        }
    except Exception as e:
        logger.error(f"Error running dbt command: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def parse_dbt_output(stdout: str, stderr: str) -> Dict[str, Any]:
    """
    Parse dbt command output để extract thông tin quan trọng
    
    Returns:
        Dict với models_run, tests_passed, errors, etc.
    """
    results = {
        'models_run': 0,
        'models_success': 0,
        'models_error': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'tests_warned': 0,
        'errors': []
    }
    
    # Parse stdout lines
    for line in stdout.split('\n'):
        # Count model runs
        if 'OK created' in line or 'OK found' in line:
            results['models_run'] += 1
            results['models_success'] += 1
        elif 'ERROR creating' in line or 'ERROR running' in line:
            results['models_run'] += 1
            results['models_error'] += 1
            results['errors'].append(line.strip())
        
        # Count test results
        elif 'PASS' in line and 'test' in line.lower():
            results['tests_passed'] += 1
        elif 'FAIL' in line and 'test' in line.lower():
            results['tests_failed'] += 1
        elif 'WARN' in line and 'test' in line.lower():
            results['tests_warned'] += 1
    
    # Parse stderr for critical errors
    if stderr:
        for line in stderr.split('\n'):
            if 'ERROR' in line or 'CRITICAL' in line:
                results['errors'].append(line.strip())
    
    return results


def check_run_results(dbt_dir: str = "/opt/airflow/dbt") -> Dict[str, Any]:
    """
    Đọc run_results.json từ dbt để lấy chi tiết execution
    
    Returns:
        Dict với detailed run results
    """
    run_results_path = Path(dbt_dir) / "target" / "run_results.json"
    
    try:
        if not run_results_path.exists():
            return {
                'status': 'not_found',
                'message': 'run_results.json not found'
            }
        
        with open(run_results_path, 'r') as f:
            results = json.load(f)
        
        # Extract summary
        summary = {
            'status': 'success' if results.get('success') else 'failed',
            'elapsed_time': results.get('elapsed_time', 0),
            'results': []
        }
        
        for result in results.get('results', []):
            summary['results'].append({
                'unique_id': result.get('unique_id'),
                'status': result.get('status'),
                'execution_time': result.get('execution_time'),
                'rows_affected': result.get('adapter_response', {}).get('rows_affected')
            })
        
        return summary
    
    except Exception as e:
        logger.error(f"Error reading run_results.json: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def check_seed_changes(dbt_dir: str = "/opt/airflow/dbt") -> bool:
    """
    Kiểm tra xem seed files có thay đổi không
    So sánh checksums hoặc timestamps
    
    Returns:
        True nếu có thay đổi, False nếu không
    """
    # Simple implementation: kiểm tra manifest.json
    manifest_path = Path(dbt_dir) / "target" / "manifest.json"
    
    try:
        if not manifest_path.exists():
            # Lần đầu chạy, coi như có thay đổi
            return True
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check seed nodes for changes
        seeds = manifest.get('nodes', {})
        seed_nodes = {k: v for k, v in seeds.items() if k.startswith('seed.')}
        
        if not seed_nodes:
            return True
        
        # Logic đơn giản: nếu có seed nodes, return True để chạy
        # Production nên implement checksum comparison
        return True
    
    except Exception as e:
        logger.warning(f"Error checking seed changes: {e}")
        # Default to True để chạy seed khi có lỗi
        return True


def validate_dbt_models(
    config: Dict[str, Any],
    layer: str,
    expected_counts: Dict[str, int]
) -> Dict[str, Any]:
    """
    Validate số rows của các models sau khi chạy
    
    Args:
        config: Pipeline config
        layer: 'silver', 'gold_dims', 'gold_facts', etc.
        expected_counts: Dict mapping model_name -> expected_row_count
    
    Returns:
        Dict với validation results
    """
    from .trino_helpers import execute_trino_query
    
    results = {
        'layer': layer,
        'models_validated': 0,
        'models_passed': 0,
        'models_warned': 0,
        'models_failed': 0,
        'details': []
    }
    
    # Get thresholds từ config
    warning_threshold = config.get('data_quality', {}).get('row_count_variance_warning', 0.05)
    critical_threshold = config.get('data_quality', {}).get('row_count_variance_critical', 0.10)
    
    for model_name, expected_count in expected_counts.items():
        try:
            # Query actual count
            query = f"SELECT COUNT(*) as cnt FROM {layer}.{model_name}"
            result = execute_trino_query(config, query)
            
            if result['status'] == 'success' and result['rows']:
                actual_count = result['rows'][0]['cnt']
                
                # Calculate variance
                variance = abs(actual_count - expected_count) / expected_count if expected_count > 0 else 1.0
                
                # Determine status
                if variance <= warning_threshold:
                    status = 'passed'
                    results['models_passed'] += 1
                elif variance <= critical_threshold:
                    status = 'warned'
                    results['models_warned'] += 1
                else:
                    status = 'failed'
                    results['models_failed'] += 1
                
                results['details'].append({
                    'model': model_name,
                    'expected': expected_count,
                    'actual': actual_count,
                    'variance': round(variance * 100, 2),
                    'status': status
                })
                
                results['models_validated'] += 1
        
        except Exception as e:
            logger.error(f"Error validating {model_name}: {e}")
            results['details'].append({
                'model': model_name,
                'status': 'error',
                'error': str(e)
            })
    
    return results
