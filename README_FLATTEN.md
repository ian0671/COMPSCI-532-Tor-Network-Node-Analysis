# Parquet Flattener and Uploader

This script `flatten_parquet.py` flattens nested Parquet files (expands dict/struct fields) and optionally uploads the flattened Parquet to Azure Blob Storage.

## Requirements

- Python 3.8+
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Flatten locally

```bash
python flatten_parquet.py --input path/to/input.parquet --output path/to/flat.parquet
```

This writes `flat.parquet` and `flat.csv` (sibling CSV for quick preview).

### Flatten and upload

Two authentication methods are supported:

1. Connection string (explicit)

```bash
python flatten_parquet.py --input input.parquet --output flat.parquet --upload --container abuseipdb --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

2. Azure AD (DefaultAzureCredential)

- Ensure `az login` or appropriate environment/service principal is configured for `DefaultAzureCredential`.

```bash
python flatten_parquet.py --input input.parquet --output flat.parquet --upload --container abuseipdb --storage-account compsci532mlwo6133466000
```

If `--dest-path` is provided, the blob will be uploaded at that path inside the container; otherwise the output filename is used.

## Notes

- Dict/object columns are expanded into dotted columns (e.g., `col.key`).
- List columns are serialized to JSON strings to avoid exploding rows; if you need to explode lists into multiple rows, modify the script accordingly.
- The script prefers `AZURE_STORAGE_CONNECTION_STRING` environment variable if no `--connection-string` is provided explicitly.

## Troubleshooting

- If upload fails due to missing packages, install `azure-storage-blob` and `azure-identity` (see `requirements.txt`).
- For Azure AD auth, ensure your principal has `Blob Data Contributor` rights to the target container.
