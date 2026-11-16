import os
from types import SimpleNamespace
from uuid import uuid4

import boto3
import pytest


@pytest.fixture
def resources():
    if os.environ.get("AWS_ENDPOINT_URL") != "https://127.0.0.1:9297":
        pytest.fail("Source env.sh: tests must only target the local emulator")
    s3, kms = boto3.client("s3"), boto3.client("kms")
    bucket = f"blog-{uuid4().hex}"
    keys = []

    def create_key(**kwargs):
        key = kms.create_key(**kwargs)["KeyMetadata"]["KeyId"]
        keys.append(key)
        return key

    s3.create_bucket(Bucket=bucket)
    try:
        yield SimpleNamespace(s3=s3, kms=kms, bucket=bucket,
                              key=create_key(), create_key=create_key)
    finally:
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                s3.delete_object(Bucket=bucket, Key=obj["Key"])
        s3.delete_bucket(Bucket=bucket)
        for key in keys:
            state = kms.describe_key(KeyId=key)["KeyMetadata"]["KeyState"]
            if state != "PendingDeletion":
                kms.schedule_key_deletion(KeyId=key, PendingWindowInDays=7)
