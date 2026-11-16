import pytest
from botocore.exceptions import ClientError

from app.envelope import decrypt_object, encrypt_object

CONTEXT = {"project": "blog"}


@pytest.mark.parametrize("data", [b"hello envelope encryption", b""])
def test_round_trip(resources, data):
    r = resources
    encrypt_object(r.bucket, "message", data, r.key, CONTEXT)
    assert decrypt_object(r.bucket, "message", CONTEXT) == data


def test_wrong_context(resources):
    r = resources
    encrypt_object(r.bucket, "message", b"secret", r.key, CONTEXT)
    with pytest.raises(ClientError) as error:
        decrypt_object(r.bucket, "message", {"project": "wrong"})
    assert error.value.response["Error"]["Code"] == "InvalidCiphertextException"


def test_disabled_key(resources):
    r = resources
    r.kms.disable_key(KeyId=r.key)
    with pytest.raises(ClientError) as error:
        encrypt_object(r.bucket, "message", b"secret", r.key, CONTEXT)
    assert error.value.response["Error"]["Code"] == "DisabledException"


def test_pending_deletion(resources):
    r = resources
    encrypt_object(r.bucket, "message", b"secret", r.key, CONTEXT)
    r.kms.schedule_key_deletion(KeyId=r.key, PendingWindowInDays=7)
    with pytest.raises(ClientError) as error:
        decrypt_object(r.bucket, "message", CONTEXT)
    assert error.value.response["Error"]["Code"] == "KMSInvalidStateException"


def test_sign_verify_key(resources):
    r = resources
    key = r.create_key(KeyUsage="SIGN_VERIFY", KeySpec="RSA_2048")
    with pytest.raises(ClientError) as error:
        encrypt_object(r.bucket, "message", b"secret", key, CONTEXT)
    assert error.value.response["Error"]["Code"] == "InvalidKeyUsageException"


def test_sse_kms_missing_key(resources):
    r = resources
    with pytest.raises(ClientError) as error:
        r.s3.put_object(Bucket=r.bucket, Key="message", Body=b"hello",
                       ServerSideEncryption="aws:kms",
                       SSEKMSKeyId="arn:aws:kms:us-east-1:000000000000:key/00000000-0000-0000-0000-000000000000")
    assert error.value.response["Error"]["Code"] == "KMS.NotFoundException"
