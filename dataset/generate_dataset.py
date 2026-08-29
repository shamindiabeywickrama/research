"""
Library Crowd Dataset Generator
--------------------------------
Generates a realistic synthetic dataset of library occupancy readings,
since no IoT sensors are used in this project. Patterns are modeled on
typical university library behaviour:

- Library open hours: 08:00 - 20:00 (closed outside these hours)
- Weekday vs weekend differences
- Lunch-time (12:00-13:00) and evening (16:00-18:00) peaks on weekdays
- Exam period weeks show much higher occupancy across all hours
- Semester break weeks show very low occupancy
- Random noise added to mimic real-world variance

Output: dataset/library_occupancy.csv
Columns:
    timestamp, date, hour, day_of_week, is_weekend,
    is_exam_period, is_semester_break, capacity,
    occupancy_count, occupancy_percent
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

CAPACITY = 200            # max seats in the library
START_DATE = datetime(2025, 1, 6)   # a Monday
NUM_WEEKS = 40             # ~ 9-10 months of data
OPEN_HOUR = 8
CLOSE_HOUR = 20            # exclusive (library closes at 20:00)

# Exam weeks (week index, 0-based) - roughly mid-term and finals
EXAM_WEEKS = {6, 7, 19, 20, 33, 34, 35}
# Semester break weeks (very low occupancy)
BREAK_WEEKS = {12, 13, 26, 27, 28}


def base_hour_factor(hour: int, is_weekend: bool) -> float:
    """Returns a 0-1 factor representing how 'busy' an hour typically is."""
    if is_weekend:
        # Weekend: gentle single midday bump
        weekend_curve = {
            8: 0.10, 9: 0.20, 10: 0.35, 11: 0.45, 12: 0.50,
            13: 0.50, 14: 0.45, 15: 0.40, 16: 0.35, 17: 0.30,
            18: 0.20, 19: 0.10
        }
        return weekend_curve.get(hour, 0.05)
    else:
        # Weekday: morning ramp-up, lunch peak, dip, evening peak, wind-down
        weekday_curve = {
            8: 0.15, 9: 0.35, 10: 0.55, 11: 0.70, 12: 0.85,
            13: 0.90, 14: 0.65, 15: 0.60, 16: 0.75, 17: 0.85,
            18: 0.70, 19: 0.40
        }
        return weekday_curve.get(hour, 0.10)


def generate_row(current_dt: datetime, week_index: int):
    hour = current_dt.hour
    day_of_week = current_dt.weekday()  # 0 = Monday ... 6 = Sunday
    is_weekend = day_of_week >= 5
    is_exam = week_index in EXAM_WEEKS
    is_break = week_index in BREAK_WEEKS

    factor = base_hour_factor(hour, is_weekend)

    if is_break:
        factor *= 0.15          # library almost empty during breaks
    elif is_exam:
        factor = min(1.0, factor * 1.6 + 0.15)   # much busier during exams

    # add random noise (+/- 12%)
    noise = random.uniform(-0.12, 0.12)
    factor = max(0.0, min(1.0, factor + noise))

    occupancy_count = int(round(factor * CAPACITY))
    occupancy_percent = round((occupancy_count / CAPACITY) * 100, 1)

    return {
        "timestamp": current_dt.isoformat(),
        "date": current_dt.strftime("%Y-%m-%d"),
        "hour": hour,
        "day_of_week": day_of_week,   # 0=Mon ... 6=Sun
        "is_weekend": int(is_weekend),
        "is_exam_period": int(is_exam),
        "is_semester_break": int(is_break),
        "capacity": CAPACITY,
        "occupancy_count": occupancy_count,
        "occupancy_percent": occupancy_percent,
    }


def main():
    rows = []
    for week in range(NUM_WEEKS):
        week_start = START_DATE + timedelta(weeks=week)
        for day_offset in range(7):
            day_dt = week_start + timedelta(days=day_offset)
            for hour in range(OPEN_HOUR, CLOSE_HOUR):
                current_dt = day_dt.replace(hour=hour, minute=0, second=0, microsecond=0)
                rows.append(generate_row(current_dt, week))

    out_path = "library_occupancy.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {out_path}")


if __name__ == "__main__":
    main()
