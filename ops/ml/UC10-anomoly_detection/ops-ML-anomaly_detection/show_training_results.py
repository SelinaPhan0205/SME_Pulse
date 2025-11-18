"""
Script để hiển thị training results từ MLflow
"""
import mlflow
import os
import json

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/airflow_mlflow")
MLFLOW_EXPERIMENT_NAME = "sme_pulse_anomaly_detection"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

try:
    client = mlflow.tracking.MlflowClient()
    
    # Get experiment
    exp = client.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
    if not exp:
        print(f"❌ Experiment '{MLFLOW_EXPERIMENT_NAME}' not found!")
        print("\nAvailable experiments:")
        for e in client.search_experiments():
            print(f"  - {e.name}")
        exit(1)
    
    # Get latest runs
    runs = client.search_runs(experiment_ids=[exp.experiment_id], order_by=["start_time DESC"], max_results=1)
    
    if not runs:
        print("❌ No runs found!")
        exit(1)
    
    run = runs[0]
    
    print("\n" + "="*80)
    print("✅ TRAINING RESULTS FROM MLFLOW")
    print("="*80)
    print(f"\nRun ID: {run.info.run_id}")
    print(f"Start time: {run.info.start_time}")
    print(f"Status: {run.info.status}")
    
    # Parameters
    print("\n📋 PARAMETERS:")
    for param, value in run.data.params.items():
        print(f"  {param}: {value}")
    
    # Metrics
    print("\n📊 METRICS:")
    for metric, value in sorted(run.data.metrics.items()):
        if isinstance(value, (int, float)):
            print(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")
    
    # Artifacts
    print("\n📁 ARTIFACTS:")
    artifacts = client.list_artifacts(run.info.run_id)
    for artifact in artifacts:
        print(f"  - {artifact.path}")
    
    print("\n" + "="*80)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
