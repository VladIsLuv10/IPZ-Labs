
from collections import defaultdict
from statistics import median


def calculate_volume(training):
    """Обчислення обсягу силового навантаження."""
    return (
        training["sets"]
        * training["reps"]
        * training["weight"]
    )


def total_volume_by_exercise(trainings):
    """Загальне навантаження за видами вправ."""
    result = defaultdict(float)

    for training in trainings:
        result[training["exercise"]] += calculate_volume(training)

    return dict(result)


def total_calories(trainings):
    """Загальна кількість витрачених калорій."""
    return sum(t["calories"] for t in trainings)


def most_intense_day(trainings):
    """День із найбільшим силовим навантаженням."""
    daily_volume = defaultdict(float)

    for training in trainings:
        daily_volume[training["date"]] += calculate_volume(training)

    if not daily_volume:
        return None

    return max(daily_volume, key=daily_volume.get)


def exercise_progress(trainings, exercise):
    """Прогрес силової вправи у відсотках."""
    records = sorted(
        [
            t for t in trainings
            if t["exercise"].lower() == exercise.lower()
        ],
        key=lambda t: t["date"]
    )

    if len(records) < 2:
        return None

    first = calculate_volume(records[0])
    last = calculate_volume(records[-1])

    if first == 0:
        return None

    return round((last - first) / first * 100, 2)


def categorize_training(training):
    """Визначення категорії тренування."""
    if training["exercise"].lower() == "біг":
        return "Кардіо"

    volume = calculate_volume(training)

    if volume >= 2500:
        return "Високе навантаження"
    elif volume >= 1000:
        return "Середнє навантаження"
    else:
        return "Низьке навантаження"


def median_calories(trainings):
    """Медіана витрачених калорій."""
    if not trainings:
        return 0

    return median(t["calories"] for t in trainings)


def running_statistics(trainings):
    """Загальна статистика бігу."""
    runs = [
        t for t in trainings
        if t["exercise"].lower() == "біг"
    ]

    if not runs:
        return None

    total_distance = sum(t["distance"] for t in runs)
    total_duration = sum(t["duration"] for t in runs)
    burned_calories = sum(t["calories"] for t in runs)

    average_pace = (
        total_duration / total_distance
        if total_distance > 0 else 0
    )

    average_speed = (
        total_distance / (total_duration / 60)
        if total_duration > 0 else 0
    )

    return {
        "count": len(runs),
        "distance": round(total_distance, 2),
        "duration": round(total_duration, 2),
        "calories": round(burned_calories, 2),
        "pace": average_pace,
        "speed": round(average_speed, 2)
    }


def format_pace(pace):
    """Перетворення темпу в формат хв:сек/км."""
    total_seconds = round(pace * 60)

    minutes, seconds = divmod(total_seconds, 60)

    return f"{minutes}:{seconds:02d}"
