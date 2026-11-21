import io

from app import db
from app.models import Product, StockMovement


def get_product(name):
    db.session.expire_all()
    query = db.select(Product).filter_by(name=name)
    return db.session.execute(query).scalar_one_or_none()


def upload(client, content, filename="products.csv"):
    return client.post(
        "/products/import",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_export_csv(staff_client):
    response = staff_client.get("/products/export.csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"name,quantity,price,reorder_level")
    assert b"Rice 25kg,40,1200.00,10" in response.data


def test_export_blocks_formula_injection(staff_client):
    db.session.add(Product(name="=SUM(1,2)", quantity=1, price=1, reorder_level=0))
    db.session.commit()

    response = staff_client.get("/products/export.csv")

    assert b"'=SUM(1,2)" in response.data


def test_import_creates_and_updates(admin_client):
    content = (
        b"name,quantity,price,reorder_level\n"
        b"Salt 1kg,30,25,10\n"
        b"Rice 25kg,100,1250,15\n"
    )

    response = upload(admin_client, content)

    assert response.status_code == 200
    assert b"1 created, 1 updated" in response.data
    assert get_product("Salt 1kg").quantity == 30
    rice = get_product("Rice 25kg")
    assert rice.quantity == 100
    assert rice.price == 1250

    query = db.select(StockMovement).filter_by(product_id=rice.id)
    movement = db.session.execute(query).scalar_one()
    assert movement.change == 60
    assert movement.reason == "csv import"


def test_import_is_all_or_nothing(admin_client):
    content = (
        b"name,quantity,price,reorder_level\n"
        b"Salt 1kg,30,25,10\n"
        b"Pepper 100g,-1,90,5\n"
    )

    response = upload(admin_client, content)

    assert response.status_code == 400
    assert b"Row 3: Quantity cannot be negative" in response.data
    assert get_product("Salt 1kg") is None


def test_import_handles_excel_bom(admin_client):
    content = b"\xef\xbb\xbfname,quantity,price,reorder_level\nSalt 1kg,30,25,10\n"

    response = upload(admin_client, content)

    assert response.status_code == 200
    assert get_product("Salt 1kg") is not None


def test_import_rejects_missing_columns(admin_client):
    response = upload(admin_client, b"name,quantity\nSalt 1kg,30\n")

    assert response.status_code == 400
    assert b"Missing required column" in response.data


def test_import_rejects_duplicate_names_in_file(admin_client):
    content = (
        b"name,quantity,price,reorder_level\n"
        b"Salt 1kg,30,25,10\n"
        b"salt 1kg,10,25,10\n"
    )

    response = upload(admin_client, content)

    assert response.status_code == 400
    assert b"Duplicate product name" in response.data


def test_import_rejects_non_csv_file(admin_client):
    response = upload(admin_client, b"hello", filename="products.txt")

    assert response.status_code == 400
    assert b"Only .csv files" in response.data


def test_staff_cannot_import(staff_client):
    response = staff_client.get("/products/import")

    assert response.status_code == 403