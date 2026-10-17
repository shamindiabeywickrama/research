"""
Research experiment for library occupancy prediction.

Compares:
1. Linear Regression
2. Random Forest Regression

Both models use the same chronological 80/10/10 split.
"""

import json
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)


DATA_PATH = "../dataset/library_occupancy.csv"
RESULTS_OUT = "model_comparison.json"

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "is_exam_period",
    "is_semester_break",
]

TARGET = "occupancy_percent"
HIGH_OCCUPANCY_THRESHOLD = 80.0


def calculate_metrics(model, X_test, y_test):
    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)

    rmse = mean_squared_error(
        y_test,
        predictions,
    ) ** 0.5

    r2 = r2_score(y_test, predictions)

    actual_high = (
        y_test >= HIGH_OCCUPANCY_THRESHOLD
    ).astype(int)

    predicted_high = (
        predictions >= HIGH_OCCUPANCY_THRESHOLD
    ).astype(int)

    accuracy = accuracy_score(
        actual_high,
        predicted_high,
    )

    precision = precision_score(
        actual_high,
        predicted_high,
        zero_division=0,
    )

    recall = recall_score(
        actual_high,
        predicted_high,
        zero_division=0,
    )

    f1 = f1_score(
        actual_high,
        predicted_high,
        zero_division=0,
    )

    return {
        "mae": round(float(mae), 3),
        "rmse": round(float(rmse), 3),
        "r2": round(float(r2), 3),
        "high_occupancy_accuracy": round(float(accuracy), 3),
        "high_occupancy_precision": round(float(precision), 3),
        "high_occupancy_recall": round(float(recall), 3),
        "high_occupancy_f1": round(float(f1), 3),
    }


def main():
    # Load dataset
    df = pd.read_csv(DATA_PATH)

    # Sort chronologically
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    X = df[FEATURES]
    y = df[TARGET]

    # Chronological 80/10/10 split
    n = len(df)

    train_end = int(n * 0.80)
    validation_end = int(n * 0.90)

    X_train = X.iloc[:train_end]
    y_train = y.iloc[:train_end]

    X_validation = X.iloc[train_end:validation_end]
    y_validation = y.iloc[train_end:validation_end]

    X_test = X.iloc[validation_end:]
    y_test = y.iloc[validation_end:]

    # --------------------------------------------------
    # 1. Linear Regression
    # --------------------------------------------------

    linear_model = LinearRegression()

    linear_model.fit(
        X_train,
        y_train,
    )

    linear_results = calculate_metrics(
        linear_model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # 2. Random Forest
    # --------------------------------------------------

    random_forest_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )

    random_forest_model.fit(
        X_train,
        y_train,
    )

    random_forest_results = calculate_metrics(
        random_forest_model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Save results
    # --------------------------------------------------

    results = {
        "dataset": {
            "total_samples": n,
            "train_samples": len(X_train),
            "validation_samples": len(X_validation),
            "test_samples": len(X_test),
            "split": "Chronological 80/10/10",
            "test_start": str(
                df["timestamp"].iloc[validation_end]
            ),
            "test_end": str(
                df["timestamp"].iloc[-1]
            ),
        },
        "features": FEATURES,
        "target": TARGET,
        "high_occupancy_threshold": HIGH_OCCUPANCY_THRESHOLD,
        "models": {
            "Linear Regression": linear_results,
            "Random Forest": random_forest_results,
        },
    }

    with open(RESULTS_OUT, "w") as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    # --------------------------------------------------
    # Display comparison
    # --------------------------------------------------

    print("\nMODEL COMPARISON")
    print("=" * 70)

    print("\nLinear Regression")
    print("-" * 30)

    for key, value in linear_results.items():
        print(f"{key}: {value}")

    print("\nRandom Forest")
    print("-" * 30)

    for key, value in random_forest_results.items():
        print(f"{key}: {value}")

    print("\nResults saved to:")
    print(RESULTS_OUT)


if __name__ == "__main__":
    main()