import csv
import io

from .routes import validate_product_form

CSV_FIELDS = ["name", "quantity", "price", "reorder_level"]
FORMULA_PREFIXES = ("=", "+", "-", "@")


def safe_csv_text(value):
    text = str(value)
    if text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text


def products_to_csv(products):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_FIELDS)
    for product in products:
        writer.writerow([
            safe_csv_text(product.name),
            product.quantity,
            f"{product.price:.2f}",
            product.reorder_level,
        ])
    return output.getvalue()


def parse_products_csv(text):
    """Return (rows, errors). Rows are validated product dictionaries."""
    reader = csv.DictReader(io.StringIO(text))
    headers = [header.strip().lower() for header in (reader.fieldnames or [])]
    missing = [field for field in CSV_FIELDS if field not in headers]
    if missing:
        return [], [f"Missing required column(s): {', '.join(missing)}."]

    rows = []
    errors = []
    seen_names = set()

    for line_number, raw_row in enumerate(reader, start=2):
        row = {
            key.strip().lower(): (value or "").strip()
            for key, value in raw_row.items()
            if isinstance(key, str)
        }
        if not any(row.values()):
            continue

        data, row_errors = validate_product_form(row)
        name_key = data["name"].lower()
        if name_key and name_key in seen_names:
            row_errors.append("Duplicate product name in this file.")
        seen_names.add(name_key)

        errors.extend(f"Row {line_number}: {error}" for error in row_errors)
        rows.append(data)

    if not rows and not errors:
        errors.append("The file has no product rows.")

    return rows, errors