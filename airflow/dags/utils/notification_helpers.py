"""
Utility functions for notifications (Slack, Email, etc.)
Các hàm tiện ích cho thông báo
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


def send_slack_notification(
    webhook_url: str,
    message: str,
    title: str = None,
    color: str = "good",
    fields: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Gửi notification đến Slack
    
    Args:
        webhook_url: Slack webhook URL
        message: Main message text
        title: Optional title
        color: "good" (green), "warning" (yellow), "danger" (red)
        fields: List of {title, value, short} dicts
    
    Returns:
        Dict với status
    """
    try:
        import requests
        
        # Build Slack message payload
        attachment = {
            "color": color,
            "text": message,
            "ts": int(datetime.now().timestamp())
        }
        
        if title:
            attachment["title"] = title
        
        if fields:
            attachment["fields"] = fields
        
        payload = {
            "attachments": [attachment]
        }
        
        # Send to Slack
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                'status': 'success',
                'message': 'Notification sent to Slack'
            }
        else:
            return {
                'status': 'failed',
                'message': f'Slack API returned {response.status_code}'
            }
    
    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def send_email_notification(
    smtp_config: Dict[str, Any],
    to_emails: List[str],
    subject: str,
    body: str,
    html: bool = False
) -> Dict[str, Any]:
    """
    Gửi email notification
    
    Args:
        smtp_config: Dict với host, port, username, password
        to_emails: List email addresses
        subject: Email subject
        body: Email body
        html: True nếu body là HTML
    
    Returns:
        Dict với status
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_config['from_email']
        msg['To'] = ', '.join(to_emails)
        
        # Attach body
        mime_type = 'html' if html else 'plain'
        msg.attach(MIMEText(body, mime_type))
        
        # Send email
        with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
            if smtp_config.get('use_tls', True):
                server.starttls()
            
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
        
        return {
            'status': 'success',
            'message': f'Email sent to {len(to_emails)} recipient(s)'
        }
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def generate_pipeline_report(
    pipeline_name: str,
    execution_date: str,
    tasks_results: List[Dict[str, Any]],
    overall_status: str
) -> str:
    """
    Tạo báo cáo tổng hợp pipeline execution
    
    Args:
        pipeline_name: Tên pipeline
        execution_date: Ngày thực thi
        tasks_results: List các task results
        overall_status: 'success', 'failed', 'partial'
    
    Returns:
        Formatted report string (plain text or HTML)
    """
    # Build report sections
    report_lines = [
        "=" * 60,
        f"PIPELINE EXECUTION REPORT",
        f"Pipeline: {pipeline_name}",
        f"Execution Date: {execution_date}",
        f"Overall Status: {overall_status.upper()}",
        "=" * 60,
        "",
        "TASK SUMMARY:",
        "-" * 60
    ]
    
    # Count task statuses
    total_tasks = len(tasks_results)
    success_tasks = sum(1 for t in tasks_results if t.get('status') == 'success')
    failed_tasks = sum(1 for t in tasks_results if t.get('status') == 'failed')
    skipped_tasks = sum(1 for t in tasks_results if t.get('status') == 'skipped')
    
    report_lines.extend([
        f"Total Tasks: {total_tasks}",
        f"Success: {success_tasks}",
        f"Failed: {failed_tasks}",
        f"Skipped: {skipped_tasks}",
        "",
        "TASK DETAILS:",
        "-" * 60
    ])
    
    # Add individual task details
    for task in tasks_results:
        task_name = task.get('task_id', 'unknown')
        status = task.get('status', 'unknown')
        duration = task.get('duration_seconds', 0)
        
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'skipped': '⏭️',
            'running': '🔄'
        }.get(status, '❓')
        
        report_lines.append(f"{status_emoji} {task_name}: {status.upper()} ({duration:.1f}s)")
        
        # Add error message if failed
        if status == 'failed' and task.get('error'):
            report_lines.append(f"   Error: {task['error'][:100]}")
    
    report_lines.extend([
        "",
        "=" * 60,
        f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60
    ])
    
    return "\n".join(report_lines)


def generate_data_quality_report(
    layer: str,
    validation_results: Dict[str, Any]
) -> str:
    """
    Tạo báo cáo data quality cho một layer
    
    Args:
        layer: 'silver', 'gold', etc.
        validation_results: Results từ validate_dbt_models
    
    Returns:
        Formatted report string
    """
    report_lines = [
        "=" * 60,
        f"DATA QUALITY REPORT - {layer.upper()} LAYER",
        "=" * 60,
        "",
        "SUMMARY:",
        f"Models Validated: {validation_results.get('models_validated', 0)}",
        f"✅ Passed: {validation_results.get('models_passed', 0)}",
        f"⚠️ Warned: {validation_results.get('models_warned', 0)}",
        f"❌ Failed: {validation_results.get('models_failed', 0)}",
        "",
        "DETAILS:",
        "-" * 60
    ]
    
    # Add model details
    for detail in validation_results.get('details', []):
        model = detail.get('model', 'unknown')
        status = detail.get('status', 'unknown')
        
        if status == 'error':
            report_lines.append(f"❌ {model}: ERROR - {detail.get('error', 'Unknown error')}")
        else:
            expected = detail.get('expected', 0)
            actual = detail.get('actual', 0)
            variance = detail.get('variance', 0)
            
            status_emoji = {
                'passed': '✅',
                'warned': '⚠️',
                'failed': '❌'
            }.get(status, '❓')
            
            report_lines.append(
                f"{status_emoji} {model}: Expected {expected:,}, Got {actual:,} "
                f"(Variance: {variance:.1f}%)"
            )
    
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)


def notify_pipeline_completion(
    config: Dict[str, Any],
    pipeline_name: str,
    execution_date: str,
    status: str,
    tasks_results: List[Dict[str, Any]]
) -> None:
    """
    Gửi notification khi pipeline hoàn thành
    
    Args:
        config: Pipeline config với notification settings
        pipeline_name: Tên pipeline
        execution_date: Ngày thực thi
        status: Overall status
        tasks_results: Task results
    """
    # Generate report
    report = generate_pipeline_report(
        pipeline_name,
        execution_date,
        tasks_results,
        status
    )
    
    # Determine notification color/priority
    color = {
        'success': 'good',
        'failed': 'danger',
        'partial': 'warning'
    }.get(status, 'warning')
    
    # Send Slack notification if enabled
    slack_config = config.get('notifications', {}).get('slack', {})
    if slack_config.get('enabled', False):
        webhook_url = slack_config.get('webhook_url')
        
        if webhook_url:
            send_slack_notification(
                webhook_url=webhook_url,
                title=f"Pipeline {pipeline_name} - {status.upper()}",
                message=report,
                color=color
            )
            logger.info("Sent Slack notification")
    
    # Send Email notification if enabled
    email_config = config.get('notifications', {}).get('email', {})
    if email_config.get('enabled', False):
        smtp_config = email_config.get('smtp', {})
        to_emails = email_config.get('recipients', [])
        
        if smtp_config and to_emails:
            send_email_notification(
                smtp_config=smtp_config,
                to_emails=to_emails,
                subject=f"[{status.upper()}] Pipeline {pipeline_name} - {execution_date}",
                body=report,
                html=False
            )
            logger.info("Sent email notification")


def refresh_metabase_cache(**context):
    """
    Refresh Metabase database schema cache
    """
    import os
    logger.info("Refreshing Metabase cache...")
    
    try:
        # Get config from environment or defaults
        metabase_enabled = os.getenv('METABASE_ENABLED', 'false').lower() == 'true'
        if not metabase_enabled:
            logger.info("Metabase integration disabled, skipping...")
            return
        
        # Check if requests library available
        try:
            import requests
        except ImportError:
            logger.warning("⚠️ requests library not available, skipping Metabase refresh")
            return
        
        # Call Metabase API to refresh specific database
        metabase_url = os.getenv('METABASE_URL', 'http://metabase:3000')
        database_id = os.getenv('METABASE_DATABASE_ID', '1')
        api_key = os.getenv('METABASE_API_KEY', '')
        
        url = f"{metabase_url}/api/database/{database_id}/sync_schema"
        
        response = requests.post(
            url,
            headers={'X-Metabase-Session': api_key},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("✅ Metabase cache refreshed successfully")
        else:
            logger.warning(f"⚠️ Metabase refresh returned status {response.status_code}")
    
    except Exception as e:
        logger.warning(f"⚠️ Error refreshing Metabase cache: {e}")
        # Don't fail pipeline for cache refresh errors
        pass


def invalidate_redis_cache(**context):
    """
    Invalidate Redis cache keys
    """
    import os
    logger.info("Invalidating Redis cache...")
    
    try:
        redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
        if not redis_enabled:
            logger.info("Redis integration disabled, skipping...")
            return
        
        # Check if redis library available
        try:
            import redis
        except ImportError:
            logger.warning("⚠️ redis library not available, skipping cache invalidation")
            return
        
        # Connect to Redis
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))
        
        r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        
        # Delete cache keys matching pattern
        pattern = os.getenv('REDIS_CACHE_PATTERN', 'sme_pulse:*')
        keys = r.keys(pattern)
        
        if keys:
            r.delete(*keys)
            logger.info(f"✅ Invalidated {len(keys)} Redis cache keys")
        else:
            logger.info("No Redis cache keys found to invalidate")
    
    except Exception as e:
        logger.warning(f"⚠️ Error invalidating Redis cache: {e}")
        # Don't fail pipeline for cache invalidation errors
        pass
