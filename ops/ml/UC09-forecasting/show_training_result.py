"""
Script để hiển thị training results từ MLflow cho Cashflow Forecasting
"""
import mlflow
import os
import json

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/airflow_mlflow")
MLFLOW_EXPERIMENT_NAME = "sme_pulse_cashflow_forecast"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

try:
    client = mlflow.tracking.MlflowClient()
    
    # Get experiment
    exp = client.get_experiment_by_name(MLFLOW_EXPERIMENT_NAME)
    if not exp:
        print(f"❌ Experiment '{MLFLOW_EXPERIMENT_NAME}' not found!")
        print(f"🔎 MLflow URI đang dùng: {MLFLOW_TRACKING_URI}")
        print("\nAvailable experiments:")
        for e in client.search_experiments():
            print(f"  - {e.name}")
        print("\n💡 Hãy kiểm tra lại tên experiment hoặc URI.\n")
        exit(1)
    
    # Get latest runs
    runs = client.search_runs(
        experiment_ids=[exp.experiment_id], 
        order_by=["start_time DESC"], 
        max_results=1
    )
    
    if not runs:
        print("❌ No runs found!")
        exit(1)
    
    run = runs[0]
    
    print("\n" + "="*80)
    print("✅ TRAINING RESULTS FROM MLFLOW")
    print("="*80)
    print(f"MLflow URI: {MLFLOW_TRACKING_URI}")
    print(f"\nRun ID: {run.info.run_id}")
    print(f"Start time: {run.info.start_time}")
    print(f"Status: {run.info.status}")
    
    # Parameters
    print("\n📋 PARAMETERS:")
    for param, value in sorted(run.data.params.items()):
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
    
    # Display feature importance if available
    print("\n🔍 FEATURE INFORMATION:")
    try:
        features_artifact = [a for a in artifacts if a.path == "features.json"]
        if features_artifact:
            features_path = client.download_artifacts(run.info.run_id, "features.json")
            with open(features_path, 'r') as f:
                features = json.load(f)
            print(f"  Total features: {len(features)}")
            print(f"  Features: {', '.join(features)}")
    except Exception as e:
        print(f"  Note: Could not load features.json ({e})")
    
    print("\n" + "="*80)
    print(f"\n💡 To load this model for prediction:")
    print(f"   model_uri = 'runs:/{run.info.run_id}/isolation_forest_model'")
    print(f"   model = mlflow.sklearn.load_model(model_uri)")
    print("="*80)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
