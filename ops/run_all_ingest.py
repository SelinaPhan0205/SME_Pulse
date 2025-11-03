#!/usr/bin/env python3
"""
Master Ingest Script: Chạy cả 2 ingest workflows
- ingest_bank_transactions.py
- ingest_shipments_payments.py

Sử dụng:
  python ops/run_all_ingest.py [--skip-bank] [--skip-shipments]
"""

import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def run_script(script_name: str, description: str) -> bool:
    """Chạy Python script con"""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"▶️  {description}")
    logger.info("=" * 70)
    
    script_path = PROJECT_ROOT / "ops" / script_name
    
    if not script_path.exists():
        logger.error(f"❌ Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=False
        )
        logger.info(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"❌ Error running {description}: {e}")
        return False


def main():
    """Main orchestrator"""
    
    import argparse
    parser = argparse.ArgumentParser(description="Master Ingest Orchestrator")
    parser.add_argument("--skip-bank", action="store_true", help="Skip bank transactions ingest")
    parser.add_argument("--skip-shipments", action="store_true", help="Skip shipments/payments ingest")
    args = parser.parse_args()
    
    logger.info("")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║ 🚀 SME PULSE – DATA INGEST ORCHESTRATOR (Bronze Layer)            ║")
    logger.info("║" + " " * 68 + "║")
    logger.info(f"║ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(69) + "║")
    logger.info("╚" + "=" * 68 + "╝")
    logger.info("")
    
    results = {}
    
    # 1. Bank Transactions
    if not args.skip_bank:
        results["bank_transactions"] = run_script(
            "ingest_bank_transactions.py",
            "📊 INGEST: Bank Transactions"
        )
    else:
        logger.info("⏭️  Skipping bank transactions (--skip-bank)")
        results["bank_transactions"] = None
    
    # 2. Shipments & Payments
    if not args.skip_shipments:
        results["shipments_payments"] = run_script(
            "ingest_shipments_payments.py",
            "📦 INGEST: Shipments & Payments"
        )
    else:
        logger.info("⏭️  Skipping shipments & payments (--skip-shipments)")
        results["shipments_payments"] = None
    
    # Summary
    logger.info("")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║ 📋 SUMMARY                                                       ║")
    logger.info("╚" + "=" * 68 + "╝")
    
    success_count = sum(1 for v in results.values() if v is True)
    total_count = sum(1 for v in results.values() if v is not None)
    
    for task, status in results.items():
        if status is None:
            status_str = "⏭️  SKIPPED"
        elif status:
            status_str = "✅ SUCCESS"
        else:
            status_str = "❌ FAILED"
        
        logger.info(f"  {task.upper().ljust(30)}: {status_str}")
    
    logger.info("")
    logger.info(f"Total: {success_count}/{total_count} succeeded")
    logger.info(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Exit code
    if success_count == total_count and total_count > 0:
        logger.info("✅ All ingest jobs completed successfully!")
        return 0
    else:
        logger.error("❌ Some ingest jobs failed. Please check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
