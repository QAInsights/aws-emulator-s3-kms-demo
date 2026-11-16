#!/usr/bin/env bash
# Local-only walkthrough. Expected negative cases are checked, printed, and continued.
set -euo pipefail
cd "$(dirname "$0")"
source ./env.sh
work=$(mktemp -d)
bucket="blog-cli-$(date +%s)-$RANDOM"
alias="alias/blog-$RANDOM"
key="" signing=""
cleanup() {
  aws s3 rm "s3://$bucket" --recursive >/dev/null 2>&1 || true
  aws s3 rb "s3://$bucket" >/dev/null 2>&1 || true
  aws kms delete-alias --alias-name "$alias" >/dev/null 2>&1 || true
  for id in "$key" "$signing"; do
    if [[ -n "$id" ]]; then
      aws kms schedule-key-deletion --key-id "$id" --pending-window-in-days 7 >/dev/null
    fi
  done
  rm -rf "$work"
}
trap cleanup EXIT
expected_error() {
  local code=$1; shift
  echo "\$ $*"
  if "$@" >"$work/error" 2>&1; then
    echo "ERROR: unexpectedly succeeded"; return 1
  fi
  cat "$work/error"
  if ! grep -Fq "$code" "$work/error"; then return 1; fi
}
echo '$ aws sts get-caller-identity'
aws sts get-caller-identity
# A symmetric key and a friendly alias.
echo '$ aws kms create-key; aws kms create-alias'
key=$(aws kms create-key --query KeyMetadata.KeyId --output text)
aws kms create-alias --alias-name "$alias" --target-key-id "$key"
echo "Created $key ($alias)"
printf 'Hello from AWS Emulator!' >"$work/plain"
echo '$ aws kms encrypt --encryption-context project=blog'
aws kms encrypt --key-id "$alias" --plaintext "fileb://$work/plain" \
  --encryption-context project=blog --query CiphertextBlob --output text | base64 -d >"$work/cipher"
echo '$ aws kms decrypt --encryption-context project=blog'
aws kms decrypt --ciphertext-blob "fileb://$work/cipher" \
  --encryption-context project=blog --query Plaintext --output text | base64 -d
echo
expected_error InvalidCiphertextException aws kms decrypt \
  --ciphertext-blob "fileb://$work/cipher" --encryption-context project=wrong
# Do not print the plaintext data key; envelope.py uses it only in memory.
echo '$ aws kms generate-data-key --key-spec AES_256 (plaintext omitted)'
aws kms generate-data-key --key-id "$key" --key-spec AES_256 \
  --encryption-context project=blog --query '{KeyId:KeyId}' --output json
aws kms disable-key --key-id "$key"
expected_error DisabledException aws kms encrypt --key-id "$key" --plaintext "fileb://$work/plain"
aws kms enable-key --key-id "$key"
signing=$(aws kms create-key --key-usage SIGN_VERIFY --key-spec RSA_2048 --query KeyMetadata.KeyId --output text)
expected_error InvalidKeyUsageException aws kms encrypt --key-id "$signing" --plaintext "fileb://$work/plain"
expected_error NotFoundException aws kms describe-key --key-id "$key" --region us-west-2
# Server-side encryption is separate from the client-side envelope helper.
echo '$ aws s3 mb; aws s3 cp --sse aws:kms --sse-kms-key-id KEY'
aws s3 mb "s3://$bucket"
aws s3 cp "$work/plain" "s3://$bucket/hello.txt" --sse aws:kms --sse-kms-key-id "$key"
echo '$ aws s3api head-object'
aws s3api head-object --bucket "$bucket" --key hello.txt
