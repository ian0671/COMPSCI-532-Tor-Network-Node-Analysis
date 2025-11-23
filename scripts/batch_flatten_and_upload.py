import os
import tempfile
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import subprocess

# CONFIGURATION
ACCOUNT_NAME = "compsci532mlwo6133466000"
CONTAINER = "abuseipdb"
PREFIX = "year=2025/month=11/"  # Change as needed
FLATTENED_PREFIX = "flattened/"

# Use DefaultAzureCredential (az login)
credential = DefaultAzureCredential()
service_client = BlobServiceClient(account_url=f"https://{ACCOUNT_NAME}.blob.core.windows.net", credential=credential)
container_client = service_client.get_container_client(CONTAINER)

# List all Parquet blobs under the prefix
print(f"Listing blobs under {PREFIX} ...")
blobs = [b for b in container_client.list_blobs(name_starts_with=PREFIX) if b.name.endswith('.parquet')]
print(f"Found {len(blobs)} Parquet files.")

for blob in blobs:
    print(f"\nProcessing: {blob.name}")
    with tempfile.TemporaryDirectory() as tmpdir:
        local_in = os.path.join(tmpdir, "input.parquet")
        local_out = os.path.join(tmpdir, "flat.parquet")
        # Download
        with open(local_in, "wb") as f:
            f.write(container_client.download_blob(blob.name).readall())
        # Flatten
        print("  Flattening ...")
        subprocess.run([
            "python3", "flatten_parquet.py",
            "--input", local_in,
            "--output", local_out
        ], check=True)
        # Upload
        dest_blob = FLATTENED_PREFIX + os.path.basename(blob.name)
        print(f"  Uploading to {dest_blob} ...")
        with open(local_out, "rb") as f:
            container_client.upload_blob(dest_blob, f, overwrite=True)
        print(f"  Done: {dest_blob}")

print("\nAll files processed and uploaded to flattened/ folder.")
