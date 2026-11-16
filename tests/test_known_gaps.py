"""Assert real-AWS expectations; XFAIL records emulator divergence, XPASS a fix."""
import pytest
from botocore.exceptions import ClientError


@pytest.mark.xfail(strict=False, reason="Emulator accepts asymmetric SSE-KMS key")
def test_sse_kms_rejects_sign_verify(resources):
    r = resources
    key = r.create_key(KeyUsage="SIGN_VERIFY", KeySpec="RSA_2048")
    with pytest.raises(ClientError) as error:
        r.s3.put_object(Bucket=r.bucket, Key="message", Body=b"hello",
                       ServerSideEncryption="aws:kms", SSEKMSKeyId=key)
    assert error.value.response["Error"]["Code"] == "KMS.InvalidKeyUsageException"


@pytest.mark.xfail(strict=False, reason="Emulator GET ignores PendingDeletion KMS state")
def test_sse_kms_get_pending_deletion(resources):
    r = resources
    r.s3.put_object(Bucket=r.bucket, Key="message", Body=b"hello",
                   ServerSideEncryption="aws:kms", SSEKMSKeyId=r.key)
    r.kms.schedule_key_deletion(KeyId=r.key, PendingWindowInDays=7)
    with pytest.raises(ClientError) as error:
        response = r.s3.get_object(Bucket=r.bucket, Key="message")
        assert response["Body"].read() == b"hello"
        response["Body"].close()
    assert error.value.response["Error"]["Code"] == "KMS.KMSInvalidStateException"

