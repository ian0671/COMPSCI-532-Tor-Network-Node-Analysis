import pandas as pd
import os
import json
from pandas import json_normalize

def flatten_df(df):
    """Recursively flatten columns that contain dict values.

    Lists are converted to JSON strings to avoid row explosion; dicts are
    expanded into new columns with dotted prefixes.
    """
    while True:
        # find columns that contain at least one dict value
        nested_cols = []
        for col in df.columns:
            # skip non-object columns quickly
            if df[col].dtype == 'O':
                # check if any value is a dict
                if df[col].apply(lambda x: isinstance(x, dict)).any():
                    nested_cols.append((col, 'dict'))
                elif df[col].apply(lambda x: isinstance(x, list)).any():
                    nested_cols.append((col, 'list'))

        if not nested_cols:
            break

        for col, coltype in nested_cols:
            if coltype == 'dict':
                # Normalize dict column into separate columns
                try:
                    normalized = json_normalize(df[col]).add_prefix(f'{col}.')
                except Exception:
                    # fallback: convert dict to JSON string
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)
                    continue
                # join back to dataframe
                df = df.drop(columns=[col]).join(normalized)
            elif coltype == 'list':
                # Convert lists to JSON strings (avoid exploding rows)
                df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)

    return df


def flatten_parquet(input_path, output_path):
    """Read a Parquet file, flatten nested fields, and write flattened output.

    Also writes a CSV sibling file for convenience.
    """
    df = pd.read_parquet(input_path)
    flat_df = flatten_df(df)
    flat_df.to_parquet(output_path, index=False)
    csv_path = os.path.splitext(output_path)[0] + '.csv'
    flat_df.to_csv(csv_path, index=False)
    print(f'Flattened data saved to {output_path} and {csv_path}')


def upload_blob(file_path, container_name, dest_blob_name, account_name=None, connection_string=None):
    """Upload `file_path` to `container_name` as `dest_blob_name`.

    Authentication options:
    - If `connection_string` is provided, uses it.
    - Else, requires `account_name` and will attempt Azure AD auth via DefaultAzureCredential.
    """
    try:
        from azure.storage.blob import BlobClient, BlobServiceClient
    except Exception as e:
        raise RuntimeError("Missing azure-storage-blob; install via requirements.txt") from e

    if connection_string:
        blob = BlobClient.from_connection_string(conn_str=connection_string,
                                                container_name=container_name,
                                                blob_name=dest_blob_name)
    else:
        if not account_name:
            raise ValueError('account_name required when connection_string is not provided')
        try:
            from azure.identity import DefaultAzureCredential
        except Exception as e:
            raise RuntimeError("Missing azure-identity; install via requirements.txt") from e

        credential = DefaultAzureCredential()
        service_client = BlobServiceClient(account_url=f"https://{account_name}.blob.core.windows.net",
                                           credential=credential)
        blob = service_client.get_blob_client(container=container_name, blob=dest_blob_name)

    with open(file_path, 'rb') as data:
        blob.upload_blob(data, overwrite=True)

    print(f'Uploaded {file_path} to container "{container_name}" at "{dest_blob_name}"')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Flatten nested Parquet and optionally upload to Azure Blob Storage')
    parser.add_argument('--input', required=True, help='Input Parquet file path')
    parser.add_argument('--output', required=True, help='Output Parquet file path (flattened)')
    parser.add_argument('--upload', action='store_true', help='Upload the flattened file to Azure after processing')
    parser.add_argument('--container', help='Blob container name (required if --upload)')
    parser.add_argument('--storage-account', help='Storage account name (use with Azure AD auth)')
    parser.add_argument('--dest-path', default=None, help='Destination blob path/name inside container (defaults to filename)')
    parser.add_argument('--connection-string', default=None, help='Azure Storage connection string (optional)')

    args = parser.parse_args()

    flatten_parquet(args.input, args.output)

    if args.upload:
        if not args.container:
            raise SystemExit('When using --upload you must provide --container')
        dest_name = args.dest_path if args.dest_path else os.path.basename(args.output)
        # Try provided connection string, else fall back to DefaultAzureCredential
        conn_str = args.connection_string or os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        upload_blob(args.output, args.container, dest_name, account_name=args.storage_account, connection_string=conn_str)
