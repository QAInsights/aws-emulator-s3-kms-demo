# AWS Emulator: S3 + KMS, locally

Tested with aws-emulator 1.0.322, CLI v2 and Python 3.12 on Ubuntu amd64.
This is an emulator demo, not proof of AWS security or service parity.
Never use real credentials. All tests require the localhost endpoint.

## Run

From this directory:

```bash
bash install.sh # optional on a machine already provisioned; requires sudo
source env.sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
curl --cacert "$AWS_CA_BUNDLE" "$AWS_ENDPOINT_URL/__admin/health"
bash s3_kms_cli_demo.sh
pytest -v
pytest -v -rx tests/test_known_gaps.py
```

Always put /usr/local/bin first: the Ubuntu CLI v1 ignores AWS_ENDPOINT_URL
and can contact real AWS. env.sh also supplies AWS_CA_BUNDLE for boto3.
Do not display emulator_credentials or plaintext generated data keys.

The CLI covers identity, KMS context binding, expected error codes, and S3
server-side SSE-KMS. app/envelope.py instead implements client-side encryption:
GenerateDataKey, local AES-256-GCM, and a versioned JSON envelope in S3.
The context is supplied externally for decryption and bound both by KMS and
AES-GCM authenticated data. S3 never receives the plaintext key or data.
Python cannot guarantee zeroization of immutable bytes; this is a small teaching
helper, not hardened production key management.

Tests create unique buckets and keys, remove all objects and buckets, and schedule
KMS keys for deletion (KMS does not offer immediate key deletion).
The CLI uses unique resources and performs the same cleanup.

## Known gaps

The two non-strict xfails assert AWS expectations rather than accepting the
emulator behavior: asymmetric SIGN_VERIFY keys should not work for SSE-KMS,
and GET should fail when its SSE-KMS key is PendingDeletion.
An XPASS means the expectation now succeeds; investigate
before removing the marker. Xfail is not evidence of security enforcement.
Run with -rx to inspect the actual failure, including unexpected API errors.

Observed on 1.0.322: SIGN_VERIFY SSE-KMS PutObject returned HTTP 200;
GetObject after scheduling the symmetric key for deletion returned HTTP 200
and the original body. These two expectations XFAIL. The normal policy test passes:
Decrypt was rejected with AccessDeniedException and an explicit-deny message.
Thus the requested policy gap is not present in this tested build; do not claim
that IAM/key policies are universally ignored based on this demo.

The workflow assumes this demo is the repository root. If embedded in another
repository, set its run working-directory to the demo path. The workflow has
not been run here. The latest emulator package is intentionally used by the
installer and CI, so behavior can change; record aws-emulator -v when publishing.

To share without environments/caches:

```bash
zip -r ../demo.zip . -x '.venv/*' '*/__pycache__/*' '.pytest_cache/*' '*.log'
```
