import os
from uuid import uuid4
from decimal import Decimal
from ..tables.products import products_table
from flask import Blueprint, request, Response, jsonify
from ..utilities import build_and_run_update, get_items_with_filters, validate_item

bp = Blueprint("products_bp", __name__, url_prefix="/products")
KEY_NAME = os.environ.get("KEY_NAME")


@bp.post("/")
def create_product():
    product_info = request.get_json()
    product_info[KEY_NAME] = str(uuid4())

    if product_info.get("price"):
        product_info["price"] = Decimal(str(product_info["price"]))

    products_table.put_item(Item=product_info)

    return product_info


@bp.get("/")
def get_all_products():
    try:
        items = get_items_with_filters(products_table, request.args)
        return jsonify(items), 200
    except ValueError as e:
        return {"error": str(e)}, 400
    except RuntimeError as e:
        return {"error": str(e)}, 500


@bp.get("/<product_id>")
def get_single_product(product_id):
    try:
        product = validate_item(products_table, product_id)
        return product
    except LookupError as e:
        return {"message": e.args[0]}, 404
    except RuntimeError as e:
        return {"error": str(e)}, 500


@bp.patch("/<product_id>")
def update_product(product_id):
    body = request.get_json()
    try:
        build_and_run_update(products_table, product_id, body)
        return Response(status=204, mimetype="application/json")
    except LookupError as e:
        return {"message": e.args[0]}, 404
    except ValueError as e:
        return {"message": str(e)}, 400
    except RuntimeError as e:
        return {"error": str(e)}, 500


@bp.delete("/<product_id>")
def delete_product(product_id):
    products_table.delete_item(Key={KEY_NAME: product_id})

    return Response(status=204, mimetype="application/json")


@bp.get('/health')
def health():
    return {
        "status": "healthy",
        'version': '1.0.1'
    }, 200
