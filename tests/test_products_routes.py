import os

# ─── Helpers ──────────────────────────────────────────────────────────────────

def seed(table, *items):
    for item in items:
        table.put_item(Item=item)
        
# ---------------------------------------------------------------------------
# POST /products/
# ---------------------------------------------------------------------------

def test_create_product_returns_product_with_generated_key(client):
    response = client.post(
        "/products/", json={"name": "Widget", "description": "A test widget"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Widget"
    assert data["description"] == "A test widget"
    assert os.environ["KEY_NAME"] in data


def test_create_product_persists_to_dynamodb(client, dynamodb_table):
    client.post("/products/", json={"name": "Widget"})

    result = dynamodb_table.scan()
    assert len(result["Items"]) == 1
    assert result["Items"][0]["name"] == "Widget"


# ---------------------------------------------------------------------------
# GET /products/
# ---------------------------------------------------------------------------

def test_get_all_products_returns_all_items(client, dynamodb_table):
    seed(dynamodb_table,
         {os.environ["KEY_NAME"]: "1", "name": "Apple", "s3_key": "apple.jpg"},
         {os.environ["KEY_NAME"]: "2", "name": "Banana", "s3_key": "banana.jpg"})

    response = client.get("/products/")

    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_get_all_products_returns_empty_list(client):
    response = client.get("/products/")

    assert response.status_code == 200
    assert response.get_json() == []


def test_get_all_products_filters_by_name(client, dynamodb_table):
    seed(dynamodb_table,
         {os.environ["KEY_NAME"]: "1", "name": "Apple Juice",
             "s3_key": "apple-juice.jpg"},
         {os.environ["KEY_NAME"]: "2", "name": "Banana", "s3_key": "banana.jpg"})

    response = client.get("/products/?name=Apple")

    data = response.get_json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["name"] == "Apple Juice"


def test_get_all_products_sorts_by_name_ascending(client, dynamodb_table):
    seed(dynamodb_table,
         {os.environ["KEY_NAME"]: "1",
             "name": "Banana", "s3_key": "banana.jpg"},
         {os.environ["KEY_NAME"]: "2", "name": "Apple", "s3_key": "apple.jpg"})

    response = client.get("/products/?sort_by=name")

    data = response.get_json()
    assert response.status_code == 200
    assert data[0]["name"] == "Apple"
    assert data[1]["name"] == "Banana"


def test_get_all_products_sorts_by_name_descending(client, dynamodb_table):
    seed(dynamodb_table,
         {os.environ["KEY_NAME"]: "1", "name": "Apple", "s3_key": "apple.jpg"},
         {os.environ["KEY_NAME"]: "2", "name": "Banana", "s3_key": "banana.jpg"})

    response = client.get("/products/?sort_by=name&order=desc")

    data = response.get_json()
    assert response.status_code == 200
    assert data[0]["name"] == "Banana"
    assert data[1]["name"] == "Apple"


def test_get_all_products_invalid_sort_by_returns_400(client):
    response = client.get("/products/?sort_by=invalid_field")

    assert response.status_code == 400
    assert "sort_by" in response.get_json()["error"]


def test_get_all_products_invalid_order_returns_400(client):
    response = client.get("/products/?order=sideways")

    assert response.status_code == 400
    assert "order" in response.get_json()["error"]


# ---------------------------------------------------------------------------
# GET /products/<product_id>
# ---------------------------------------------------------------------------

def test_get_single_product_returns_product(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123",
                          "name": "Widget", "s3_key": "widget.jpg"})

    response = client.get("/products/abc-123")

    assert response.status_code == 200
    data = response.get_json()
    assert data[os.environ["KEY_NAME"]] == "abc-123"
    assert data["name"] == "Widget"


def test_get_single_product_not_found_returns_404(client):
    response = client.get("/products/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.get_json()["message"]


def test_get_single_product_no_s3_key_image_url_empty_string(client, dynamodb_table, aws_credentials):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123",
                          "name": "Widget"})

    response = client.get("/products/abc-123")

    assert response.status_code == 200
    data = response.get_json()
    assert data["image_url"] == ""


# ---------------------------------------------------------------------------
# PATCH /products/<product_id>
# ---------------------------------------------------------------------------

def test_update_product_returns_204(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123", "name": "Old Name",
                          "description": "Old desc", "s3_key": "widget.jpg"})

    response = client.patch("/products/abc-123", json={"name": "New Name"})

    assert response.status_code == 204


def test_update_product_persists_change(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123", "name": "Old Name",
                          "description": "desc", "s3_key": "widget.jpg"})

    client.patch("/products/abc-123", json={"name": "New Name"})

    item = dynamodb_table.get_item(
        Key={os.environ["KEY_NAME"]: "abc-123"})["Item"]
    assert item["name"] == "New Name"


def test_update_product_not_found_returns_404(client):
    response = client.patch("/products/nonexistent", json={"name": "New Name"})

    assert response.status_code == 404


def test_update_product_no_valid_attributes_returns_400(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123",
                          "name": "Widget", "s3_key": "widget.jpg"})

    response = client.patch("/products/abc-123",
                            json={"nonexistent_field": "value"})

    assert response.status_code == 400
    assert "No valid attributes" in response.get_json()["message"]


def test_update_product_cannot_update_primary_key(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123",
                          "name": "Widget", "s3_key": "widget.jpg"})

    response = client.patch("/products/abc-123",
                            json={os.environ["KEY_NAME"]: "new-id"})

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /products/<product_id>
# ---------------------------------------------------------------------------

def test_delete_product_returns_204(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123",
                          "name": "Widget", "s3_key": "widget.jpg"})

    response = client.delete("/products/abc-123")

    assert response.status_code == 204


def test_delete_product_removes_item_from_dynamodb(client, dynamodb_table):
    seed(dynamodb_table, {os.environ["KEY_NAME"]: "abc-123",
                          "name": "Widget", "s3_key": "widget.jpg"})

    client.delete("/products/abc-123")

    result = dynamodb_table.get_item(Key={os.environ["KEY_NAME"]: "abc-123"})
    assert "Item" not in result
