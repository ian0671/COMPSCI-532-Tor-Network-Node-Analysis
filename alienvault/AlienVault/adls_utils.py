import logging
import json
import datetime
import os
from typing import List, Dict, Optional
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

ADLS_ACCOUNT_URL = os.environ.get("ADLS_ACCOUNT_URL")
ADLS_FILESYSTEM = os.environ.get("ADLS_FILESYSTEM")
ADLS_DIR_BASE = os.environ.get("ADLS_DIR_BASE")

def _adls_client() -> Optional[DataLakeServiceClient]:
    if not ADLS_ACCOUNT_URL:
        logging.error("ADLS_ACCOUNT_URL not set")
        return None
    cred = DefaultAzureCredential()
    return DataLakeServiceClient(account_url=ADLS_ACCOUNT_URL, credential=cred)

def write_records_batch(records: List[Dict], subdir: str = "alienvault") -> Optional[str]:
    svc = _adls_client()
    if not svc:
        return None
    ts = datetime.datetime.utcnow()
    parts = [
        ADLS_DIR_BASE.rstrip("/"),
        subdir.strip("/"),
        f"dt={ts.strftime('%Y-%m-%d')}",
        f"hour={ts.strftime('%H')}"
    ]
    dir_path = "/".join([p for p in parts if p])
    filename = f"part-{ts.strftime('%H%M%S')}.json"
    try:
        fs = svc.get_file_system_client(file_system=ADLS_FILESYSTEM)
        dir_client = fs.get_directory_client(dir_path)
        dir_client.create_directory()
        file_client = dir_client.get_file_client(filename)
        data = ("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in records)).encode("utf-8")
        file_client.create_file()
        file_client.append_data(data=data, offset=0, length=len(data))
        file_client.flush_data(len(data))
        path = f"abfss://{ADLS_FILESYSTEM}@{ADLS_ACCOUNT_URL.split('://')[1]}/{dir_path}/{filename}"
        logging.info("Wrote %d records to ADLS: %s", len(records), path)
        return path
    except Exception:
        logging.exception("Failed to write records to ADLS")
        return None