import json

import boto3
import pytest
from botocore.exceptions import ClientError


def test_key_policy_denies_decrypt(resources):
    r = resources
    ciphertext = r.kms.encrypt(KeyId=r.key, Plaintext=b"secret")["CiphertextBlob"]
    account = boto3.client("sts").get_caller_identity()["Account"]
    policy = {"Version": "2012-10-17", "Statement": [
        {"Sid": "Admin", "Effect": "Allow",
         "Principal": {"AWS": f"arn:aws:iam::{account}:root"},
         "Action": "kms:*", "Resource": "*"},
        {"Sid": "DenyDecrypt", "Effect": "Deny", "Principal": "*",
         "Action": "kms:Decrypt", "Resource": "*"},
    ]}
    r.kms.put_key_policy(KeyId=r.key, PolicyName="default", Policy=json.dumps(policy))
    with pytest.raises(ClientError) as error:
        r.kms.decrypt(CiphertextBlob=ciphertext)
    assert error.value.response["Error"]["Code"] == "AccessDeniedException"
