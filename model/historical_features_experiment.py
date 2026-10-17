"""
Research experiment using historical occupancy features.

Compares:
1. Random Forest with time/context features
2. Random Forest with time/context + historical occupancy features

Uses a chronological 80/10/10 split.
"""

import json
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
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
RESULTS_OUT = "historical_features_results.json"

BASE_FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "is_exam_period",
    "is_semester_break",
]

LAG_FEATURES = [
    "occupancy_lag_1",
    "occupancy_lag_2",
    "occupancy_lag_3",
    "occupancy_lag_24",
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

    # Sort by time
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Create historical occupancy features
    for lag in [1, 2, 3, 24]:
        df[f"occupancy_lag_{lag}"] = (
            df[TARGET].shift(lag)
        )

    # Remove rows that do not have enough history
    df = df.dropna().reset_index(drop=True)

    # --------------------------------------------------
    # Chronological 80/10/10 split
    # --------------------------------------------------

    n = len(df)

    train_end = int(n * 0.80)
    validation_end = int(n * 0.90)

    train = df.iloc[:train_end]
    validation = df.iloc[train_end:validation_end]
    test = df.iloc[validation_end:]

    y_train = train[TARGET]
    y_validation = validation[TARGET]
    y_test = test[TARGET]

    # --------------------------------------------------
    # Model 1: Base Random Forest
    # --------------------------------------------------

    base_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )

    base_model.fit(
        train[BASE_FEATURES],
        y_train,
    )

    base_results = calculate_metrics(
        base_model,
        test[BASE_FEATURES],
        y_test,
    )

    # --------------------------------------------------
    # Model 2: Random Forest + historical occupancy
    # --------------------------------------------------

    historical_features = BASE_FEATURES + LAG_FEATURES

    historical_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )

    historical_model.fit(
        train[historical_features],
        y_train,
    )

    historical_results = calculate_metrics(
        historical_model,
        test[historical_features],
        y_test,
    )

    # --------------------------------------------------
    # Calculate improvement
    # --------------------------------------------------

    mae_improvement = (
        (base_results["mae"] - historical_results["mae"])
        / base_results["mae"]
    ) * 100

    rmse_improvement = (
        (base_results["rmse"] - historical_results["rmse"])
        / base_results["rmse"]
    ) * 100

    r2_improvement = (
        historical_results["r2"]
        - base_results["r2"]
    )

    results = {
        "dataset": {
            "samples_after_lag_creation": n,
            "train_samples": len(train),
            "validation_samples": len(validation),
            "test_samples": len(test),
            "split": "Chronological 80/10/10",
        },
        "base_features": BASE_FEATURES,
        "historical_features": LAG_FEATURES,
        "target": TARGET,
        "high_occupancy_threshold": HIGH_OCCUPANCY_THRESHOLD,
        "models": {
            "Random Forest - Base": base_results,
            "Random Forest - Historical Features": historical_results,
        },
        "improvement": {
            "mae_improvement_percent": round(
                float(mae_improvement),
                2,
            ),
            "rmse_improvement_percent": round(
                float(rmse_improvement),
                2,
            ),
            "r2_difference": round(
                float(r2_improvement),
                3,
            ),
        },
    }

    with open(RESULTS_OUT, "w") as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print("\nHISTORICAL FEATURE EXPERIMENT")
    print("=" * 70)

    print("\nRandom Forest - Base Features")
    print("-" * 40)

    for key, value in base_results.items():
        print(f"{key}: {value}")

    print("\nRandom Forest - Historical Features")
    print("-" * 40)

    for key, value in historical_results.items():
        print(f"{key}: {value}")

    print("\nImprovement")
    print("-" * 40)
    print(
        f"MAE improvement: "
        f"{mae_improvement:.2f}%"
    )
    print(
        f"RMSE improvement: "
        f"{rmse_improvement:.2f}%"
    )
    print(
        f"R² difference: "
        f"{r2_improvement:.3f}"
    )

    print("\nResults saved to:")
    print(RESULTS_OUT)


if __name__ == "__main__":
    main()