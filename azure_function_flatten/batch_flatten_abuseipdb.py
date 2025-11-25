#!/usr/bin/env python3
"""Batch flatten existing abuseipdb parquet files and upload to flattened/ prefix."""
import os
import sys
import tempfile
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from azure.storage.blob import BlobServiceClient
import pandas as pd
from azure_function_flatten.flatten_blob_trigger.__init__ import flatten_df, sanitize_for_parquet

CONN_STR = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
if not CONN_STR:
    print("Error: Set AZURE_STORAGE_CONNECTION_STRING environment variable")
    sys.exit(1)

CONTAINER = 'abuseipdb'
blob_service = BlobServiceClient.from_connection_string(CONN_STR)
container_client = blob_service.get_container_client(CONTAINER)

# List all parquet files (exclude already flattened ones)
blobs = [
    b for b in container_client.list_blobs()
    if b.name.endswith('.parquet') and not b.name.startswith('flattened/')
]

print(f"Found {len(blobs)} parquet files in {CONTAINER} container")

for i, blob in enumerate(blobs, 1):
    print(f"\n[{i}/{len(blobs)}] Processing {blob.name}")
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, 'input.parquet')
            out_path = os.path.join(tmpdir, 'output.parquet')
            
            # Download
            blob_client = container_client.get_blob_client(blob.name)
            with open(in_path, 'wb') as f:
                f.write(blob_client.download_blob().readall())
            
            # Flatten
            df = pd.read_parquet(in_path)
            flat = flatten_df(df)
            flat = sanitize_for_parquet(flat)
            flat.to_parquet(out_path, index=False, engine='pyarrow')
            
            # Upload to flattened/
            dest = f"flattened/{os.path.basename(blob.name)}"
            with open(out_path, 'rb') as f:
                container_client.upload_blob(dest, f, overwrite=True)
            
            print(f"   Uploaded to {dest}")
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        continue

print(f"\nDone! Check {CONTAINER}/flattened/ for results")
