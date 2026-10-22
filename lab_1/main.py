
import csv
import json
from pathlib import Path
from datetime import datetime

import analyzer


BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "trainings.csv"
JSON_FILE = BASE_DIR / "results.json"


def load_trainings(filename):
    """Завантаження та перевірка даних із CSV."""
    trainings = []

    try:
        with open(filename, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            required_fields = {
                "date", "exercise", "sets", "reps",
                "weight", "duration", "distance", "calories"
            }

            if not required_fields.issubset(reader.fieldnames or []):
                print("Помилка: CSV не містить усіх необхідних стовпців.")
                return []

            for line_number, row in enumerate(reader, start=2):
                try:
                    training = {
                        "date": row["date"].strip(),
                        "exercise": row["exercise"].strip(),
                        "sets": int(row["sets"]),
                        "reps": int(row["reps"]),
                        "weight": float(row["weight"]),
                        "duration": float(row["duration"]),
                        "distance": float(row["distance"]),
                        "calories": float(row["calories"])
                    }

                    datetime.strptime(
                        training["date"], "%Y-%m-%d"
                    )

                    if not training["exercise"]:
                        raise ValueError("Не вказано назву вправи")

                    numeric_fields = [
                        "sets", "reps", "weight",
                        "duration", "distance", "calories"
                    ]

                    for field in numeric_fields:
                        value = training[field]

                        if not (0 <= value < float("inf")):
                            raise ValueError(
                                f"Некоректне значення поля {field}"
                            )

                    if training["exercise"].lower() == "біг":
                        if training["duration"] <= 0 or training["distance"] <= 0:
                            raise ValueError(
                                "Для бігу потрібні додатні час і дистанція"
                            )

                    trainings.append(training)

                except (ValueError, TypeError, KeyError, AttributeError) as error:
                    print(
                        f"Помилка у рядку {line_number}: {error}"
                    )

    except (FileNotFoundError, OSError) as error:
        print(f"Не вдалося відкрити CSV: {error}")

    return trainings


def show_all_trainings(trainings):
    """Перегляд усіх тренувань."""
    print("\n=== УСІ ТРЕНУВАННЯ ===")

    for t in sorted(trainings, key=lambda x: x["date"]):
        print(
            f'{t["date"]} | '
            f'{t["exercise"]} | '
            f'{t["calories"]:.0f} ккал'
        )


def show_report(trainings):
    """Загальний звіт про тренування."""
    print("\n=== ЗАГАЛЬНИЙ ЗВІТ ===")

    print(f"Кількість тренувань: {len(trainings)}")

    volumes = analyzer.total_volume_by_exercise(trainings)

    print("\nСилове навантаження:")

    for exercise, volume in volumes.items():
        if volume > 0:
            print(f"  {exercise}: {volume:.1f} кг")

    print(
        f"\nЗагальні витрачені калорії: "
        f"{analyzer.total_calories(trainings):.0f} ккал"
    )

    print(
        f"Медіана калорій: "
        f"{analyzer.median_calories(trainings):.1f} ккал"
    )

    day = analyzer.most_intense_day(trainings)

    print(
        f"Найінтенсивніший силовий день: "
        f"{day if day else 'Немає даних'}"
    )


def show_sorted(trainings):
    """Сортування за витраченими калоріями."""
    print("\n=== СОРТУВАННЯ ЗА КАЛОРІЯМИ ===")

    sorted_trainings = sorted(
        trainings,
        key=lambda t: t["calories"],
        reverse=True
    )

    for t in sorted_trainings:
        print(
            f'{t["date"]} | '
            f'{t["exercise"]} | '
            f'{t["calories"]:.0f} ккал'
        )


def show_categories(trainings):
    """Категоризація тренувань."""
    print("\n=== КАТЕГОРІЇ ТРЕНУВАНЬ ===")

    for t in trainings:
        category = analyzer.categorize_training(t)

        print(
            f'{t["date"]} | '
            f'{t["exercise"]} | '
            f'{category}'
        )


def show_progress(trainings):
    """Аналіз прогресу вибраної вправи."""
    exercise = input("Введіть назву вправи: ").strip()

    progress = analyzer.exercise_progress(
        trainings, exercise
    )

    if progress is None:
        print("Недостатньо даних для аналізу прогресу.")
    else:
        print(
            f"Зміна обсягу навантаження: "
            f"{progress:+.2f}%"
        )


def show_running_statistics(trainings):
    """Виведення статистики бігу."""
    stats = analyzer.running_statistics(trainings)

    if stats is None:
        print("Даних про біг немає.")
        return

    print("\n=== СТАТИСТИКА БІГУ ===")

    print(f'Кількість пробіжок: {stats["count"]}')
    print(f'Загальна дистанція: {stats["distance"]:.2f} км')
    print(f'Загальний час: {stats["duration"]:.0f} хв')
    print(f'Спалено калорій: {stats["calories"]:.0f} ккал')

    print(
        f'Середній темп: '
        f'{analyzer.format_pace(stats["pace"])} хв/км'
    )

    print(
        f'Середня швидкість: {stats["speed"]:.2f} км/год'
    )


def save_results(trainings):
    """Збереження результатів аналізу в JSON."""
    result = {
        "training_count": len(trainings),
        "total_calories": analyzer.total_calories(trainings),
        "median_calories": analyzer.median_calories(trainings),
        "volume_by_exercise": analyzer.total_volume_by_exercise(trainings),
        "most_intense_day": analyzer.most_intense_day(trainings),
        "running_statistics": analyzer.running_statistics(trainings)
    }

    try:
        with open(JSON_FILE, "w", encoding="utf-8") as file:
            json.dump(
                result,
                file,
                ensure_ascii=False,
                indent=4
            )

        print(f"\nРезультати збережено у {JSON_FILE.name}")

    except OSError as error:
        print(f"Помилка збереження JSON: {error}")


def main():
    """Головна функція програми."""
    trainings = load_trainings(CSV_FILE)

    if not trainings:
        print("Немає даних для аналізу.")
        return

    while True:
        print("\n========== ТРЕНУВАЛЬНИЙ ЩОДЕННИК ==========")
        print("1. Переглянути всі тренування")
        print("2. Загальний звіт")
        print("3. Сортування за калоріями")
        print("4. Категорії тренувань")
        print("5. Прогрес силової вправи")
        print("6. Статистика бігу")
        print("7. Зберегти результати у JSON")
        print("0. Вихід")
        print("============================================")

        choice = input("Оберіть пункт меню: ").strip()

        if choice == "1":
            show_all_trainings(trainings)

        elif choice == "2":
            show_report(trainings)

        elif choice == "3":
            show_sorted(trainings)

        elif choice == "4":
            show_categories(trainings)

        elif choice == "5":
            show_progress(trainings)

        elif choice == "6":
            show_running_statistics(trainings)

        elif choice == "7":
            save_results(trainings)

        elif choice == "0":
            print("\nРоботу програми завершено.")
            break

        else:
            print("Невірний пункт меню. Спробуйте ще раз.")


if __name__ == "__main__":
    main()
