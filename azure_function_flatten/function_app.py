import azure.functions as func
import logging
import os
import tempfile
from azure.storage.blob import BlobServiceClient
import pandas as pd
import pyarrow
import json
from typing import Any

app = func.FunctionApp()


def flatten_df(df):
    """Flatten nested DataFrame structures"""
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
    """Serialize complex Python types to JSON strings"""
    if isinstance(value, (dict, list, tuple, set)):
        try:
            return json.dumps(value)
        except Exception:
            return str(value)
    return value


def sanitize_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all complex types to strings for Parquet compatibility"""
    for col in df.columns:
        if df[col].dtype == 'O':
            series = df[col].apply(_serialize_complex)
            if not all(isinstance(v, (str, int, float, bool, type(None))) for v in series):
                series = series.apply(lambda v: str(v) if v is not None else None)
            df[col] = series.astype('string')
    return df


@app.blob_trigger(arg_name="myblob", path="abuseipdb/{path}.parquet",
                  connection="AzureWebJobsStorage") 
def flatten_blob_trigger(myblob: func.InputStream):
    logging.info(f"Processing blob: {myblob.name}, Size: {myblob.length} bytes")
    
    try:
        container = myblob.uri.split("/")[3]
        conn_str = os.environ.get('AzureWebJobsStorage')
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service_client.get_container_client(container)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, 'input.parquet')
            out_path = os.path.join(tmpdir, 'flat.parquet')
            
            with open(in_path, 'wb') as f:
                f.write(myblob.read())
            
            df = pd.read_parquet(in_path)
            flat_df = flatten_df(df)
            flat_df = sanitize_for_parquet(flat_df)
            flat_df.to_parquet(out_path, index=False, engine='pyarrow')
            
            dest_blob = f"flattened/{os.path.basename(myblob.name)}"
            with open(out_path, 'rb') as f:
                container_client.upload_blob(dest_blob, f, overwrite=True)
            
            logging.info(f"✓ Flattened file uploaded to {dest_blob}")
    except Exception as e:
        logging.error(f"Error processing blob: {e}")
        raise


# This example uses SDK types to directly access the underlying BlobClient object provided by the Blob storage trigger.
# To use, uncomment the section below and add azurefunctions-extensions-bindings-blob to your requirements.txt file
# Ref: aka.ms/functions-sdk-blob-python
#
# import azurefunctions.extensions.bindings.blob as blob
# @app.blob_trigger(arg_name="client", path="abuseipdb/{name}",
#                   connection="DefaultEndpointsProtocol=https;AccountName=compsci532mlwo6133466000;AccountKey=9WpasXAzf4kL32KOwOJQmQj2Ns8sDxljJPs0jSwASCmUVyz4HSVMRQnu7Xxcbr9+oHkU9xmDOICX+AStSyqETg==;EndpointSuffix=core.windows.net")
# def flatten_blob_trigger(client: blob.BlobClient):
#     logging.info(
#         f"Python blob trigger function processed blob \n"
#         f"Properties: {client.get_blob_properties()}\n"
#         f"Blob content head: {client.download_blob().read(size=1)}"
#     )



@app.blob_trigger(arg_name="myblob", path="censys/{path}.parquet",
                  connection="AzureWebJobsStorage") 
def flatten_blob_trigger_censys(myblob: func.InputStream):
    logging.info(f"Processing censys blob: {myblob.name}, Size: {myblob.length} bytes")
    
    try:
        container = myblob.uri.split("/")[3]
        conn_str = os.environ.get('AzureWebJobsStorage')
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
        container_client = blob_service_client.get_container_client(container)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, 'input.parquet')
            out_path = os.path.join(tmpdir, 'flat.parquet')
            
            with open(in_path, 'wb') as f:
                f.write(myblob.read())
            
            df = pd.read_parquet(in_path)
            flat_df = flatten_df(df)
            flat_df = sanitize_for_parquet(flat_df)
            flat_df.to_parquet(out_path, index=False, engine='pyarrow')
            
            dest_blob = f"flattened/{os.path.basename(myblob.name)}"
            with open(out_path, 'rb') as f:
                container_client.upload_blob(dest_blob, f, overwrite=True)
            
            logging.info(f"✓ Censys flattened file uploaded to {dest_blob}")
    except Exception as e:
        logging.error(f"Error processing censys blob: {e}")
        raise


# This example uses SDK types to directly access the underlying BlobClient object provided by the Blob storage trigger.
# To use, uncomment the section below and add azurefunctions-extensions-bindings-blob to your requirements.txt file
# Ref: aka.ms/functions-sdk-blob-python
#
# import azurefunctions.extensions.bindings.blob as blob
# @app.blob_trigger(arg_name="client", path="censys/{name}",
#                   connection="DefaultEndpointsProtocol=https;AccountName=compsci532mlwo6133466000;AccountKey=9WpasXAzf4kL32KOwOJQmQj2Ns8sDxljJPs0jSwASCmUVyz4HSVMRQnu7Xxcbr9+oHkU9xmDOICX+AStSyqETg==;EndpointSuffix=core.windows.net")
# def flatten_blob_trigger_censys(client: blob.BlobClient):
#     logging.info(
#         f"Python blob trigger function processed blob \n"
#         f"Properties: {client.get_blob_properties()}\n"
#         f"Blob content head: {client.download_blob().read(size=1)}"
#     )
