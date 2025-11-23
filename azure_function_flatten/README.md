# Azure Flatten Functions

Two blob-triggered Azure Functions flatten nested Parquet files and write sanitized Parquet back under a `flattened/` prefix:

- `flatten_blob_trigger`: AbuseIPDB (derives container from incoming blob URI)
- `flatten_blob_trigger_censys`: Censys (now unified: also derives container from blob URI)

## What Changed

We added `sanitize_for_parquet` to convert any remaining Python complex objects (dict/list/tuple/set) into JSON strings before writing Parquet. This prevents Azure portal / ML workspace browse errors like:

```
StreamAccess.Validation.ParquetType-NotSupported
```

Both triggers now write via `engine='pyarrow'` for consistent metadata.

## Local Test

1. Install deps:

```bash
pip install -r requirements.txt
```

2. Create a sample nested parquet:

```bash
python - <<'PY'
import pandas as pd
import json
from pathlib import Path
nested = pd.DataFrame({
  'ip': ['1.1.1.1','8.8.8.8'],
  'scores': [{'threat': 5, 'confidence': 0.8}, {'threat': 1, 'confidence': 0.2}],
  'tags': [['ddos','botnet'], ['resolver']],
})
Path('sample_input.parquet').unlink(missing_ok=True)
nested.to_parquet('sample_input.parquet')
print('Wrote sample_input.parquet')
PY
```

3. Simulate function logic (abuseipdb trigger) locally:

```bash
python - <<'PY'
import pandas as pd, json
from azure_function_flatten.flatten_blob_trigger.__init__ import flatten_df, sanitize_for_parquet

df = pd.read_parquet('sample_input.parquet')
flat = flatten_df(df)
flat = sanitize_for_parquet(flat)
flat.to_parquet('sample_flat.parquet', engine='pyarrow', index=False)
print(flat.head())
print('Wrote sample_flat.parquet')
PY
```

Open `sample_flat.parquet` with parquet-tools or pandas to verify nested structures are flattened and lists serialized.

## Run Functions Locally

Requires Azure Functions Core Tools:

```bash
npm i -g azure-functions-core-tools@4 --unsafe-perm true
func start
```

Ensure `local.settings.json` has:

```json
{
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "<your connection string or UseDevelopmentStorage=true>"
  }
}
```

Add a blob to the watched container path; the trigger should log upload of `flattened/<original_name>`.

## Deploy / Update

Use Core Tools publish (replace `<FUNCTION_APP_NAME>`):

```bash
func azure functionapp publish <FUNCTION_APP_NAME> --python
```

Or with Azure CLI for zip deploy:

```bash
zip -r flatten_funcs.zip . -x '*.git*'
az functionapp deployment source config-zip \
  --name <FUNCTION_APP_NAME> \
  --resource-group <RESOURCE_GROUP> \
  --src flatten_funcs.zip
```

## Verification in Azure

After deployment:

1. Upload a nested parquet blob to the source container.
2. Confirm a flattened parquet appears under `flattened/`.
3. Browse in Azure Storage Explorer or ML workspace; the previous ParquetType-NotSupported error should no longer appear.

## Notes

- If extremely large nested objects exist, consider streaming flattening or schema pruning.
- For arrays needing row explosion, replace JSON serialization with `explode()` logic and handle potential row multiplication.
