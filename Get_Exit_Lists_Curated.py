import logging
import os
import io
import json
import pandas as pd
import azure.functions as func
from azure.storage.filedatalake import DataLakeServiceClient

# Connection string to your ADLS Gen2 account
ADLS_CONN = os.getenv("ADLS_GEN2_CONNECTION_STRING")

# Target curated container
CURATED_CONTAINER = "get-exit-lists-curated"

# STRICT: Only process events from these source containers
ALLOWED_SOURCE_CONTAINERS = {"get_exit_lists"}  # or {"get-exit-lists"} if that's correct

CollecTor_Get_Exit_Lists_Curated = func.Blueprint()

@CollecTor_Get_Exit_Lists_Curated.event_grid_trigger(arg_name="event")
def Get_Exit_Lists_Curated(event: func.EventGridEvent):
    """
    Triggered when an Event Grid notification (BlobCreated) is received.
    Reads a Parquet file from the allowed source container and writes
    a curated Parquet file into get-exit-lists-curated.
    """

    try:
        logging.info(f"Event Grid trigger received: {event.id}")
        logging.info(f"Event type: {event.event_type}")
        logging.info(f"Subject: {event.subject}")

        # Guard: Connection string must exist
        if not ADLS_CONN:
            logging.error("ADLS connection string is missing. Skipping event.")
            return

        # Parse container and blob path from subject (authoritative)
        subject = event.subject
        try:
            container = subject.split("/containers/")[1].split("/")[0]
            blob_path = subject.split("/blobs/")[1]
        except Exception as e:
            logging.error(f"Failed to parse subject: {subject}")
            logging.error(f"Error: {e}")
            return

        logging.info(f"Resolved container: {container}")
        logging.info(f"Resolved blob path: {blob_path}")

        # Guard: Enforce container allowlist
        if container not in ALLOWED_SOURCE_CONTAINERS:
            logging.warning(json.dumps({
                "action": "skip",
                "reason": "container_not_allowed",
                "container": container,
                "allowed": sorted(list(ALLOWED_SOURCE_CONTAINERS)),
                "blob_path": blob_path
            }))
            return

        # Guard: Only process .parquet files
        if not blob_path.endswith(".parquet"):
            logging.warning(json.dumps({
                "action": "skip",
                "reason": "non_parquet_file",
                "container": container,
                "blob_path": blob_path
            }))
            return

        # Connect to ADLS Gen2
        try:
            service_client = DataLakeServiceClient.from_connection_string(ADLS_CONN)
        except Exception as e:
            logging.error(f"Failed to connect to ADLS: {e}")
            return

        fs_client = service_client.get_file_system_client(container)
        file_client = fs_client.get_file_client(blob_path)

        # Guard: Check blob size before reading
        props = file_client.get_file_properties()
        if props.size == 0:
            logging.warning(json.dumps({
                "action": "skip",
                "reason": "empty_blob",
                "container": container,
                "blob_path": blob_path
            }))
            return

        # Read parquet
        download = file_client.download_file()
        parquet_bytes = download.readall()
        df = pd.read_parquet(io.BytesIO(parquet_bytes), engine="pyarrow")

        # Build curated path from last 2 segments (e.g., date/hour)
        path_parts = blob_path.split("/")
        if len(path_parts) >= 3:
            curated_path = "/".join(path_parts[-3:-1])  # e.g., 2025-11-27/00
        else:
            curated_path = "unknown"

        # Preserve original filename and append event.id for uniqueness
        base_filename = os.path.basename(blob_path)
        name, ext = os.path.splitext(base_filename)
        filename = f"{name}_{event.id}{ext}"

        # Write curated parquet
        curated_fs = service_client.get_file_system_client(CURATED_CONTAINER)
        dir_client = curated_fs.get_directory_client(curated_path)
        try:
            dir_client.create_directory()
        except Exception:
            pass  # Directory may already exist

        out_file = dir_client.create_file(filename)
        curated_bytes = df.to_parquet(index=False, engine="pyarrow", compression="snappy")
        out_file.append_data(curated_bytes, offset=0, length=len(curated_bytes))
        out_file.flush_data(len(curated_bytes))

        logging.info(json.dumps({
            "action": "write_curated",
            "rows": len(df),
            "source_container": container,
            "source_path": blob_path,
            "target": f"{CURATED_CONTAINER}/{curated_path}/{filename}"
        }))

    except Exception as e:
        import traceback
        logging.error(f"Error processing Event Grid event: {e}")
        logging.error(traceback.format_exc())