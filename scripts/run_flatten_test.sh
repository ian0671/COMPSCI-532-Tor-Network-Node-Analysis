#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/run_flatten_test.sh
# Preconditions:
# - az CLI installed and you are logged in (az login)
# - You have access to the storage account/container
# - Run from the repository root (COMPSCI-532)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

ACCOUNT="compsci532mlwo6133466000"
CONTAINER="abuseipdb"
PREFIX="year=2025/month=11/day=23/hour=04/"

echo "Listing blobs under prefix $PREFIX ..."
az storage blob list --account-name "$ACCOUNT" --container-name "$CONTAINER" --prefix "$PREFIX" --auth-mode login --output table

BLOB_NAME=$(az storage blob list --account-name "$ACCOUNT" --container-name "$CONTAINER" --prefix "$PREFIX" --auth-mode login --query "[0].name" -o tsv || true)

if [ -z "$BLOB_NAME" ]; then
  echo "No blob found with that prefix. Edit PREFIX in the script or pick another file."; exit 1
fi

echo "Selected blob: $BLOB_NAME"

echo "Downloading blob to ./input.parquet ..."
az storage blob download --account-name "$ACCOUNT" --container-name "$CONTAINER" --name "$BLOB_NAME" --file ./input.parquet --auth-mode login

echo "Installing Python deps (requirements.txt) ..."
python3 -m pip install --upgrade pip || true
python3 -m pip install -r requirements.txt

DEST_BLOB="flattened/${BLOB_NAME##*/}"

echo "Flattening ./input.parquet -> ./flat.parquet and uploading to container $CONTAINER as $DEST_BLOB"
python3 flatten_parquet.py --input ./input.parquet --output ./flat.parquet --upload --container "$CONTAINER" --storage-account "$ACCOUNT" --dest-path "$DEST_BLOB"

echo "Verifying uploaded blob exists: $DEST_BLOB"
az storage blob exists --account-name "$ACCOUNT" --container-name "$CONTAINER" --name "$DEST_BLOB" --auth-mode login -o table

echo "Listing blobs under flattened/ ..."
az storage blob list --account-name "$ACCOUNT" --container-name "$CONTAINER" --prefix "flattened/" --auth-mode login --output table

echo "Done. If successful, the flattened file is uploaded as: $DEST_BLOB"
