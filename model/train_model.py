"""
Trains a RandomForestRegressor to predict library occupancy_percent
based on time-context features (no IoT sensor input required).

Features used:
    hour, day_of_week, is_weekend, is_exam_period, is_semester_break

Target:
    occupancy_percent

Output:
    model/library_crowd_model.pkl   (trained sklearn pipeline)
    model/metrics.json              (evaluation metrics)
"""

import json
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

DATA_PATH = "../dataset/library_occupancy.csv"
MODEL_OUT = "library_crowd_model.pkl"
METRICS_OUT = "metrics.json"

FEATURES = ["hour", "day_of_week", "is_weekend", "is_exam_period", "is_semester_break"]
TARGET = "occupancy_percent"


def main():
    df = pd.read_csv(DATA_PATH)

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    metrics = {
        "mae": round(float(mae), 3),
        "r2_score": round(float(r2), 3),
        "features": FEATURES,
        "target": TARGET,
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    joblib.dump({"model": model, "features": FEATURES}, MODEL_OUT)
    with open(METRICS_OUT, "w") as f:
        json.dump(metrics, f, indent=2)

    print("Training complete.")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
