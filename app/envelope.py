"""Client-side envelope encryption; S3 receives only an encrypted JSON envelope."""
import base64
import json
import os

import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_object(
    bucket: str, key: str, data: bytes, kms_key_id: str, context: dict[str, str]
) -> None:
    kms = boto3.client("kms")
    material = kms.generate_data_key(
        KeyId=kms_key_id, KeySpec="AES_256", EncryptionContext=context
    )
    nonce = os.urandom(12)
    aad = json.dumps(context, sort_keys=True, separators=(",", ":")).encode()
    ciphertext = AESGCM(material["Plaintext"]).encrypt(nonce, data, aad)
    envelope = {
        "version": 1,
        "nonce": base64.b64encode(nonce).decode(),
        "encrypted_key": base64.b64encode(material["CiphertextBlob"]).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }
    boto3.client("s3").put_object(
        Bucket=bucket, Key=key, Body=json.dumps(envelope).encode(),
        ContentType="application/json",
    )


def decrypt_object(bucket: str, key: str, context: dict[str, str]) -> bytes:
    body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"]
    try:
        envelope = json.loads(body.read())
    finally:
        body.close()
    if envelope["version"] != 1:
        raise ValueError("Unsupported envelope version")
    material = boto3.client("kms").decrypt(
        CiphertextBlob=base64.b64decode(envelope["encrypted_key"]),
        EncryptionContext=context,
    )
    aad = json.dumps(context, sort_keys=True, separators=(",", ":")).encode()
    return AESGCM(material["Plaintext"]).decrypt(
        base64.b64decode(envelope["nonce"]),
        base64.b64decode(envelope["ciphertext"]), aad,
    )
