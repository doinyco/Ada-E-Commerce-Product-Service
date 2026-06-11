import os
import boto3
import pytest
from moto import mock_aws

QUEUE_NAME = "test-queue.fifo"


@pytest.fixture
def aws_credentials():
    os.environ["TABLE_NAME"] = "test-table"
    os.environ["KEY_NAME"] = "product_key"
    os.environ["BUCKET_NAME"] = "test-bucket"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["S3_DEFAULT_KEY"] = "S3_DEFAULT_KEY"


@pytest.fixture
def app(aws_credentials):
    from app import create_app
    flask_app = create_app()
    return flask_app


@pytest.fixture
def mock_aws_context(aws_credentials):
    with mock_aws():
        yield


@pytest.fixture
def dynamodb_table(mock_aws_context):
    dynamodb = boto3.resource("dynamodb", region_name=os.environ["AWS_DEFAULT_REGION"])
    table = dynamodb.create_table(
        TableName=os.environ["TABLE_NAME"],
        KeySchema=[{"AttributeName": os.environ["KEY_NAME"], "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": os.environ["KEY_NAME"], "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()

    s3 = boto3.client("s3", region_name=os.environ["AWS_DEFAULT_REGION"])
    s3.create_bucket(Bucket=os.environ["BUCKET_NAME"])

    yield table


@pytest.fixture
def sqs_queue(mock_aws_context):
    sqs = boto3.resource("sqs", region_name=os.environ["AWS_DEFAULT_REGION"])
    queue = sqs.create_queue(
        QueueName=QUEUE_NAME,
        Attributes={
            "FifoQueue": "true",
            "ContentBasedDeduplication": "true",
        },
    )
    os.environ["QUEUE_URL"] = queue.url
    yield queue


@pytest.fixture
def client(app, dynamodb_table):
    import app.routes.products_routes as routes_module
    original = routes_module.products_table
    routes_module.products_table = dynamodb_table
    with app.test_client() as c:
        yield c
    routes_module.products_table = original


@pytest.fixture
def consumer_table(dynamodb_table):
    """Patch the products_table used by utilities so consumer logic hits the moto table."""
    import app.utilities as utilities_module
    original = utilities_module.products_table
    utilities_module.products_table = dynamodb_table
    yield dynamodb_table
    utilities_module.products_table = original
