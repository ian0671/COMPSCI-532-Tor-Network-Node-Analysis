import logging
import os
import tempfile
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pandas as pd
import pyarrow  # noqa: F401 ensure pyarrow parquet engine is available
import json
from typing import Any

def flatten_df(df):
    while True:
        nested_cols = []
        for col in df.columns:
            if df[col].dtype == 'O':
                if df[col].apply(lambda x: isinstance(x, dict)).any():
                    nested_cols.append((col, 'dict'))
                elif df[col].apply(lambda x: isinstance(x, list)).any():
                    nested_cols.append((col, 'list'))
        if not nested_cols:
            break
        for col, coltype in nested_cols:
            if coltype == 'dict':
                try:
                    normalized = pd.json_normalize(df[col]).add_prefix(f'{col}.')
                except Exception:
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
                    continue
                df = df.drop(columns=[col]).join(normalized)
            elif coltype == 'list':
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
    return df


def _serialize_complex(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return json.dumps(value)
        except Exception:
            return str(value)
    return value


def sanitize_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Convert complex objects to JSON strings to avoid unsupported Parquet logical types."""
    for col in df.columns:
        if df[col].dtype == 'O':
            series = df[col].apply(_serialize_complex)
            if not all(isinstance(v, (str, int, float, bool, type(None))) for v in series):
                series = series.apply(lambda v: str(v) if v is not None else None)
            df[col] = series.astype('string')
    return df

def main(blob: func.InputStream):
    logging.info(f"Processing blob: {blob.name}, Size: {blob.length} bytes")
    # Derive container directly from blob URI for consistency with abuseipdb trigger
    # format: https://<account>.blob.core.windows.net/<container>/<blob path>
    container = blob.uri.split('/')[3]
    conn_str = os.environ.get('AzureWebJobsStorage')
    blob_service_client = BlobServiceClient.from_connection_string(conn_str)
    container_client = blob_service_client.get_container_client(container)
    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, 'input.parquet')
        out_path = os.path.join(tmpdir, 'flat.parquet')
        with open(in_path, 'wb') as f:
            f.write(blob.read())
        df = pd.read_parquet(in_path)
        flat_df = flatten_df(df)
        flat_df = sanitize_for_parquet(flat_df)
        flat_df.to_parquet(out_path, index=False, engine='pyarrow')
        dest_blob = f"flattened/{os.path.basename(blob.name)}"
        with open(out_path, 'rb') as f:
            container_client.upload_blob(dest_blob, f, overwrite=True)
        logging.info(f"Flattened file uploaded to {dest_blob}")
