from pathlib import Path
import shutil
import json

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = ROOT / "dataset" / "library_occupancy.csv"

MODEL_OUTPUT = ROOT / "backend" / "library_crowd_model.pkl"
METRICS_OUTPUT = ROOT / "backend" / "metrics.json"

FINAL_RESULTS_PATH = ROOT / "model" / "final_results.json"


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "is_exam_period",
    "is_semester_break",
]

TARGET = "occupancy_percent"


# ---------------------------------------------------------
# Research evaluation information
#
# These values come from the final experiment that was
# already completed and verified.
# ---------------------------------------------------------

TRAIN_ROWS = 2688
VALIDATION_ROWS = 336
TEST_ROWS = 336

TEST_START = "2025-09-15 08:00"
TEST_END = "2025-10-12 19:00"

HIGH_OCCUPANCY_THRESHOLD = 80


# ---------------------------------------------------------
# Load dataset
# ---------------------------------------------------------

print("Loading dataset...")

df = pd.read_csv(DATASET_PATH)

X = df[FEATURES]
y = df[TARGET]

print(f"Dataset loaded: {len(df)} rows")


# ---------------------------------------------------------
# Train final Random Forest
#
# Random Forest was selected during the research
# model comparison.
#
# For deployment, the selected model is retrained
# using the complete available synthetic dataset.
# ---------------------------------------------------------

print()
print("Training final Random Forest model...")

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    random_state=42,
    n_jobs=-1,
)

model.fit(X, y)

print("Model training completed.")


# ---------------------------------------------------------
# Backup existing backend model and metrics
# ---------------------------------------------------------

backup_model = ROOT / "backend" / "library_crowd_model_original.pkl"
backup_metrics = ROOT / "backend" / "metrics_original.json"

if MODEL_OUTPUT.exists() and not backup_model.exists():
    shutil.copy2(MODEL_OUTPUT, backup_model)
    print("Original backend model backed up.")

if METRICS_OUTPUT.exists() and not backup_metrics.exists():
    shutil.copy2(METRICS_OUTPUT, backup_metrics)
    print("Original backend metrics backed up.")


# ---------------------------------------------------------
# Save deployment model
# ---------------------------------------------------------

print()
print("Saving deployment model...")

model_bundle = {
    "model": model,
    "features": FEATURES,
}

joblib.dump(model_bundle, MODEL_OUTPUT)

print("Model bundle saved to:")
print(MODEL_OUTPUT)


# ---------------------------------------------------------
# Load official research results
# ---------------------------------------------------------

print()
print("Loading final research results...")

with open(FINAL_RESULTS_PATH, "r", encoding="utf-8") as f:
    final_results = json.load(f)

rf_results = final_results["models"]["Random Forest"]


# ---------------------------------------------------------
# Prepare backend metrics
#
# These are the official held-out research results.
#
# The deployed model is retrained using the complete
# available dataset after model selection.
# ---------------------------------------------------------

metrics = {
    # Regression metrics
    "mae": rf_results["mae"],
    "rmse": rf_results["rmse"],
    "r2_score": rf_results["r2"],
    "mape": rf_results["mape_percent_zero_safe"],

    # High occupancy classification metrics
    "accuracy": rf_results["high_occupancy_accuracy"],
    "precision": rf_results["high_occupancy_precision"],
    "recall": rf_results["high_occupancy_recall"],
    "f1_score": rf_results["high_occupancy_f1"],

    # Model information
    "features": FEATURES,
    "target": TARGET,

    # Research evaluation
    "evaluation": {
        "method": "chronological 80/10/10 split",

        "train_rows": TRAIN_ROWS,
        "validation_rows": VALIDATION_ROWS,
        "test_rows": TEST_ROWS,

        "test_period": {
            "start": TEST_START,
            "end": TEST_END,
        },

        "high_occupancy_threshold": HIGH_OCCUPANCY_THRESHOLD,
    },

    # Deployment information
    "deployment": {
        "model": "RandomForestRegressor",
        "n_estimators": 200,
        "max_depth": 10,
        "random_state": 42,
        "trained_on": "complete available synthetic dataset",
    },
}


# ---------------------------------------------------------
# Save backend metrics
# ---------------------------------------------------------

print()
print("Saving backend metrics...")

with open(METRICS_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

print("Metrics saved to:")
print(METRICS_OUTPUT)


# ---------------------------------------------------------
# Display final information
# ---------------------------------------------------------

print()
print("=" * 60)
print("FINAL DEPLOYMENT MODEL CREATED")
print("=" * 60)

print()
print(f"Dataset rows:       {len(df)}")
print(f"Features:           {', '.join(FEATURES)}")
print(f"Target:             {TARGET}")

print()
print("Model:")
print("  Random Forest")
print("  Trees:             200")
print("  Max depth:         10")
print("  Random state:      42")

print()
print("Official research test results:")

print(f"  MAE:               {rf_results['mae']}")
print(f"  RMSE:              {rf_results['rmse']}")
print(f"  R²:                 {rf_results['r2']}")
print(f"  MAPE:              {rf_results['mape_percent_zero_safe']}%")

print(
    f"  High occupancy accuracy:  "
    f"{rf_results['high_occupancy_accuracy']}"
)

print(
    f"  High occupancy precision: "
    f"{rf_results['high_occupancy_precision']}"
)

print(
    f"  High occupancy recall:    "
    f"{rf_results['high_occupancy_recall']}"
)

print(
    f"  High occupancy F1:        "
    f"{rf_results['high_occupancy_f1']}"
)

print()
print("Research split:")
print(f"  Training:      {TRAIN_ROWS}")
print(f"  Validation:    {VALIDATION_ROWS}")
print(f"  Test:          {TEST_ROWS}")

print()
print("Test period:")
print(f"  Start:         {TEST_START}")
print(f"  End:           {TEST_END}")

print()
print("Deployment model:")
print(f"  {MODEL_OUTPUT}")

print()
print("Backend metrics:")
print(f"  {METRICS_OUTPUT}")

print()
print("Original backend files:")
print(f"  {backup_model}")
print(f"  {backup_metrics}")

print()
print("=" * 60)
print("DONE")
print("=" * 60)