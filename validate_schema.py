import argparse
import csv
import sys
from pathlib import Path


def load_expected_schema(dictionary_path: Path) -> dict[str, list[str]]:
    expected: dict[str, list[tuple[int, str]]] = {}

    with dictionary_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"table_name", "column_name", "ordinal_position"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Missing required dictionary columns: {missing_list}")

        for row in reader:
            table = (row.get("table_name") or "").strip()
            column = (row.get("column_name") or "").strip()
            ordinal_raw = (row.get("ordinal_position") or "").strip()

            if not table or not column or not ordinal_raw:
                continue

            try:
                ordinal = int(ordinal_raw)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid ordinal_position '{ordinal_raw}' for {table}.{column}"
                ) from exc

            expected.setdefault(table, []).append((ordinal, column))

    ordered: dict[str, list[str]] = {}
    for table, pairs in expected.items():
        sorted_pairs = sorted(pairs, key=lambda p: p[0])
        ordered[table] = [column for _, column in sorted_pairs]

    return ordered


def read_csv_header(csv_path: Path) -> list[str]:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            return next(reader)
        except StopIteration:
            return []


def compare_schema(expected: dict[str, list[str]], data_dir: Path) -> list[str]:
    errors: list[str] = []

    for table, expected_columns in sorted(expected.items()):
        csv_path = data_dir / f"{table}.csv"
        if not csv_path.exists():
            errors.append(f"Missing data file for table '{table}': {csv_path}")
            continue

        actual_columns = read_csv_header(csv_path)

        if actual_columns == expected_columns:
            continue

        expected_set = set(expected_columns)
        actual_set = set(actual_columns)
        missing = [c for c in expected_columns if c not in actual_set]
        extra = [c for c in actual_columns if c not in expected_set]

        errors.append(f"Schema mismatch for {csv_path}:")
        if missing:
            errors.append(f"  Missing columns: {', '.join(missing)}")
        if extra:
            errors.append(f"  Extra columns: {', '.join(extra)}")

        common = [c for c in expected_columns if c in actual_set]
        actual_common = [c for c in actual_columns if c in expected_set]
        if common != actual_common and not missing and not extra:
            errors.append("  Column order mismatch.")
            errors.append(f"  Expected order: {', '.join(expected_columns)}")
            errors.append(f"  Actual order:   {', '.join(actual_columns)}")

    known_tables = set(expected.keys())
    for csv_path in sorted(data_dir.glob("*.csv")):
        table_name = csv_path.stem
        if table_name not in known_tables:
            errors.append(
                f"Data file has no table definition in dictionary: {csv_path}"
            )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate generated CSV schemas against DATA_DICTIONARY.csv"
    )
    parser.add_argument(
        "--dictionary",
        default="DATA_DICTIONARY.csv",
        help="Path to machine-readable data dictionary CSV",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing generated table CSV files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dictionary_path = Path(args.dictionary)
    data_dir = Path(args.data_dir)

    if not dictionary_path.exists():
        print(f"ERROR: Dictionary file not found: {dictionary_path}")
        return 2
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"ERROR: Data directory not found: {data_dir}")
        return 2

    try:
        expected = load_expected_schema(dictionary_path)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not expected:
        print("ERROR: No schema rows found in dictionary file.")
        return 2

    errors = compare_schema(expected, data_dir)
    if errors:
        print("Schema validation failed:")
        for error in errors:
            print(error)
        return 1

    print(
        f"Schema validation passed: {len(expected)} tables matched between "
        f"{dictionary_path} and {data_dir}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
