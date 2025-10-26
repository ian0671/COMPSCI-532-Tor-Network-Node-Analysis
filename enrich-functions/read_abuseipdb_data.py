from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from fastavro import reader
import io, pandas as pd

ACCOUNT_URL = "https://compsci532mlwo6133466000.blob.core.windows.net"
CONTAINER   = "abuseipdb"
PREFIX      = "compsci532eventhub/abuseipdbdata/"

cred = DefaultAzureCredential()
cc = BlobServiceClient(account_url=ACCOUNT_URL, credential=cred).get_container_client(CONTAINER)

records, files = [], 0
for b in cc.list_blobs(name_starts_with=PREFIX):
    if not b.name.endswith(".avro"): 
        continue
    files += 1
    data = cc.download_blob(b.name).readall()
    for rec in reader(io.BytesIO(data)):
        records.append(rec)

print("AVRO files matched:", files)
df = pd.DataFrame(records)
print("Total rows:", len(df))
print(df.head())
