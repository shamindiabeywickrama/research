"""
Final research experiment for library occupancy prediction.

Models:
1. Linear Regression
2. Random Forest Regression

Evaluation:
- Chronological 80/10/10 split
- MAE
- RMSE
- Zero-safe MAPE
- R²
- High occupancy Accuracy
- Precision
- Recall
- F1-score

The same test set is used for both models.
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
RESULTS_OUT = "final_results.json"

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "is_exam_period",
    "is_semester_break",
]

TARGET = "occupancy_percent"
HIGH_OCCUPANCY_THRESHOLD = 80.0


def calculate_zero_safe_mape(actual, predicted):
    """
    Calculate MAPE while excluding observations
    where the actual occupancy is zero.
    """

    actual = pd.Series(actual).reset_index(drop=True)
    predicted = pd.Series(predicted).reset_index(drop=True)

    non_zero = actual != 0

    if non_zero.sum() == 0:
        return None

    mape = (
        (
            (actual[non_zero] - predicted[non_zero]).abs()
            / actual[non_zero].abs()
        ).mean()
        * 100
    )

    return float(mape)


def evaluate_model(model, X_test, y_test):
    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = mean_squared_error(
        y_test,
        predictions,
    ) ** 0.5

    mape = calculate_zero_safe_mape(
        y_test,
        predictions,
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    # High occupancy classification
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
        "mape_percent_zero_safe": round(float(mape), 3),
        "r2": round(float(r2), 3),
        "high_occupancy_accuracy": round(float(accuracy), 3),
        "high_occupancy_precision": round(float(precision), 3),
        "high_occupancy_recall": round(float(recall), 3),
        "high_occupancy_f1": round(float(f1), 3),
    }


def main():

    # --------------------------------------------------
    # Load and sort dataset
    # --------------------------------------------------

    df = pd.read_csv(DATA_PATH)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    X = df[FEATURES]
    y = df[TARGET]

    # --------------------------------------------------
    # Chronological 80/10/10 split
    # --------------------------------------------------

    n = len(df)

    train_end = int(n * 0.80)
    validation_end = int(n * 0.90)

    X_train = X.iloc[:train_end]
    y_train = y.iloc[:train_end]

    X_validation = X.iloc[
        train_end:validation_end
    ]

    y_validation = y.iloc[
        train_end:validation_end
    ]

    X_test = X.iloc[
        validation_end:
    ]

    y_test = y.iloc[
        validation_end:
    ]

    # --------------------------------------------------
    # Linear Regression
    # --------------------------------------------------

    linear_model = LinearRegression()

    linear_model.fit(
        X_train,
        y_train,
    )

    linear_results = evaluate_model(
        linear_model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Random Forest
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

    random_forest_results = evaluate_model(
        random_forest_model,
        X_test,
        y_test,
    )

    # --------------------------------------------------
    # Determine best model by MAE
    # --------------------------------------------------

    if (
        random_forest_results["mae"]
        < linear_results["mae"]
    ):
        best_model = "Random Forest"
    else:
        best_model = "Linear Regression"

    # --------------------------------------------------
    # Save final results
    # --------------------------------------------------

    results = {
        "dataset": {
            "total_samples": n,
            "train_samples": len(X_train),
            "validation_samples": len(X_validation),
            "test_samples": len(X_test),
            "split": "Chronological 80/10/10",
            "train_start": str(
                df["timestamp"].iloc[0]
            ),
            "train_end": str(
                df["timestamp"].iloc[train_end - 1]
            ),
            "validation_start": str(
                df["timestamp"].iloc[train_end]
            ),
            "validation_end": str(
                df["timestamp"].iloc[validation_end - 1]
            ),
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
        "selected_model": best_model,
    }

    with open(
        RESULTS_OUT,
        "w"
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
        )

    # --------------------------------------------------
    # Display results
    # --------------------------------------------------

    print("\nFINAL RESEARCH EXPERIMENT")
    print("=" * 70)

    print("\nDataset")
    print("-" * 30)
    print(f"Total samples: {n}")
    print(f"Training: {len(X_train)}")
    print(f"Validation: {len(X_validation)}")
    print(f"Testing: {len(X_test)}")

    print(
        f"\nTest period: "
        f"{df['timestamp'].iloc[validation_end]} "
        f"to "
        f"{df['timestamp'].iloc[-1]}"
    )

    print("\nLinear Regression")
    print("-" * 30)

    for key, value in linear_results.items():
        print(f"{key}: {value}")

    print("\nRandom Forest")
    print("-" * 30)

    for key, value in random_forest_results.items():
        print(f"{key}: {value}")

    print("\nSelected model")
    print("-" * 30)
    print(best_model)

    print("\nResults saved to:")
    print(RESULTS_OUT)


if __name__ == "__main__":
    main()