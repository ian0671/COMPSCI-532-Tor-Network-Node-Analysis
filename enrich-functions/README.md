# Azure Durable Functions: Orchestrator + Event Hub + Validator# Enrich Functions: Orchestrator + EventHub + Validator



This Azure Functions app implements a complete data pipeline with:This Azure Functions app includes:



1. **Timer-triggered producers** - Query Censys and AbuseIPDB APIs and publish to Event Hub- Two timer-triggered producers that query Censys and AbuseIPDB and publish results to Azure Event Hub

2. **Durable orchestrator** - Reads from Event Hubs, joins/enriches by IP, sinks to Event Hub or ADLS- A Durable Functions orchestrator that (on a schedule) reads from Event Hubs, joins/normalizes by IP, and sinks to Event Hub or ADLS

3. **Event Hub validator** - Consumes joined data, validates schema, stores to ADLS- A validation function that consumes the joined Event Hub and writes validated rows to ADLS Gen2



## Architecture## App settings (local.settings.json)



```Populate the following (no secrets are committed):

Timer(Censys) ──┐

                ├──► Event Hubs ──► Durable Orchestrator ──┐- EVENTHUB_CONNECTION: Event Hubs namespace connection string (no EntityPath)

Timer(AbuseIPDB)┘                                          ├──► Event Hub/ADLS ──► Validator ──► ADLS- ABUSE_EH_NAME: Event Hub name for AbuseIPDB producer (e.g., abuseipdbdata)

                                                          │                                      ↓- CENSYS_EH_NAME: Event Hub name for Censys producer (e.g., censysdata)

                                                          └──────────────────────────────────► validated/- JOINED_EH_NAME: Event Hub name for joined/enriched output (e.g., joinedrecords)

```- ABUSE_API_KEY, ABUSE_IP_LIST

- CENSYS_API_TOKEN, CENSYS_QUERY

## Key Features- JOINED_OUTPUT_TARGET: eventhub or adls

- ADLS_ACCOUNT_URL: https://<account>.dfs.core.windows.net

- **Auto-scaling**: Consumption plan scales based on Event Hub triggers- ADLS_FILESYSTEM: Filesystem/container name

- **Timer orchestration**: Runs every 5 minutes, joins latest data from both streams- ADLS_DIR_BASE: Base path (e.g., tor-pipeline)

- **Flexible sink**: Choose Event Hub (real-time) or ADLS (batch) for joined output

- **Schema validation**: Downstream validator ensures data quality before final storageOptional:

- **IP-based joining**: Combines AbuseIPDB reputation with Censys host/service data

- ABUSE_CONSUMER_GROUP, CENSYS_CONSUMER_GROUP, VALIDATOR_CONSUMER_GROUP (defaults $Default)

## Configuration

## Dependencies

Configure these app settings in Azure or `local.settings.json`:

Install with:

### Event Hub Settings

- `EVENTHUB_CONNECTION`: Namespace connection string (no EntityPath)```

- `ABUSE_EH_NAME`: Hub for AbuseIPDB data (e.g., "abuseipdbdata")pip install -r requirements.txt

- `CENSYS_EH_NAME`: Hub for Censys data (e.g., "censysdata")  ```

- `JOINED_EH_NAME`: Hub for joined output (e.g., "joinedrecords")

## Run locally

### API Credentials

- `ABUSE_API_KEY`: AbuseIPDB API keyRequires Azure Functions Core Tools v4, Python 3.9+.

- `ABUSE_IP_LIST`: Comma-separated IPs to check (e.g., "8.8.8.8,1.1.1.1")

- `CENSYS_API_TOKEN`: Censys search API token1. Log in to Azure for ADLS/Managed Identity (optional):

- `CENSYS_QUERY`: Search query (e.g., "services.service_name:HTTP")

```

### Sink Configurationaz login

- `JOINED_OUTPUT_TARGET`: "eventhub" or "adls"```

- `ADLS_ACCOUNT_URL`: https://<account>.dfs.core.windows.net

- `ADLS_FILESYSTEM`: ADLS container/filesystem name2. Start functions host:

- `ADLS_DIR_BASE`: Base directory (e.g., "tor-pipeline")

```

### Optionalfunc start

- `ABUSE_CONSUMER_GROUP`, `CENSYS_CONSUMER_GROUP`, `VALIDATOR_CONSUMER_GROUP`: Default "$Default"```

- `CENSYS_PER_PAGE`, `CENSYS_MAX_PAGES`: API pagination limits

The timers (every minute) will publish to Event Hub. The Durable orchestrator will run every 5 minutes and either publish joined messages to `JOINED_EH_NAME` or write JSON files to ADLS under `processed/joined/` path. The `ValidateAndStore` Event Hub trigger consumes `JOINED_EH_NAME` and writes validated rows to `validated/joined/` in ADLS.

## Local Development

## Deploy

### Prerequisites

Create the Function App (Linux Consumption) and configure settings:

```bash

# Azure Functions Core Tools v4```

brew install azure-functions-core-tools@4az group create -n <rg> -l <region>

az storage account create -n <sa> -g <rg> -l <region> --sku Standard_LRS

# Azure CLI (for ADLS auth)az functionapp create -n <funcapp> -g <rg> -s <sa> -c <region> --consumption-plan-location <region> --os-type Linux --runtime python --runtime-version 3.9

brew install azure-cli

```# Event Hubs namespace + hubs

az eventhubs namespace create -g <rg> -n <ehns> -l <region>

### Setupaz eventhubs eventhub create -g <rg> --namespace-name <ehns> -n abuseipdbdata --message-retention 1 --partition-count 2

az eventhubs eventhub create -g <rg> --namespace-name <ehns> -n censysdata --message-retention 1 --partition-count 2

```bashaz eventhubs eventhub create -g <rg> --namespace-name <ehns> -n joinedrecords --message-retention 1 --partition-count 2

cd enrich-functions

python3 -m venv .venv# Get namespace connection string

source .venv/bin/activateEH_CONN=$(az eventhubs namespace authorization-rule keys list -g <rg> --namespace-name <ehns> --name RootManageSharedAccessKey --query primaryConnectionString -o tsv)

pip install -r requirements.txt

# Configure app settings

# Configure local.settings.json with your valuesaz functionapp config appsettings set -g <rg> -n <funcapp> --settings \

# Authenticate for ADLS (if using)  EVENTHUB_CONNECTION="$EH_CONN" \

az login  ABUSE_EH_NAME=abuseipdbdata CENSYS_EH_NAME=censysdata JOINED_EH_NAME=joinedrecords \

```  ABUSE_API_KEY=<secret> CENSYS_API_TOKEN=<secret> \

  JOINED_OUTPUT_TARGET=eventhub

### Test Join Logic

# (Optional) ADLS settings if using ADLS sinks

```bashaz functionapp config appsettings set -g <rg> -n <funcapp> --settings \

python test_join.py  ADLS_ACCOUNT_URL=https://<account>.dfs.core.windows.net ADLS_FILESYSTEM=<fs> ADLS_DIR_BASE=tor-pipeline

```

# Deploy

### Run Locallyfunc azure functionapp publish <funcapp>

```

```bash

func start## Notes

```

- Throughput/partitioning: adjust Event Hub partitions and consider Capture if needed. Retry policies are handled by the SDK and Functions host. For heavy loads, switch to Dedicated/Event Hubs Standard with higher TU.

Expected behavior:- Scaling: The Consumption plan scales out automatically. Durable Functions manages fan-in/fan-out. The orchestrator is started by a timer every 5 minutes (customize in code).

- AbuseIPDB/Censys timers fire every minute (and on startup)- Schema: The validator enforces a minimal schema and drops bad rows; extend with stricter checks as needed.

- Orchestrator starts every 5 minutes: "Started JoinOrchestrator with ID=..."
- Validator processes joined Event Hub messages and writes to ADLS

## Azure Deployment

### 1. Create Infrastructure

```bash
# Variables
RG="cs532-prod-rg"
LOC="eastus"  
FUNC_APP="cs532-orchestrator-func"
STORAGE_ACCOUNT="cs532storage$(date +%s)"
EH_NAMESPACE="cs532-eventhub-ns"

# Resource group and storage
az group create -n "$RG" -l "$LOC"
az storage account create -n "$STORAGE_ACCOUNT" -g "$RG" -l "$LOC" --sku Standard_LRS

# Function App (Linux Consumption)
az functionapp create \
  -n "$FUNC_APP" -g "$RG" -s "$STORAGE_ACCOUNT" \
  -c "$LOC" --consumption-plan-location "$LOC" \
  --os-type Linux --runtime python --runtime-version 3.11

# Event Hubs namespace and hubs
az eventhubs namespace create -g "$RG" -n "$EH_NAMESPACE" -l "$LOC" --sku Standard
az eventhubs eventhub create -g "$RG" --namespace-name "$EH_NAMESPACE" -n abuseipdbdata --message-retention 1 --partition-count 2
az eventhubs eventhub create -g "$RG" --namespace-name "$EH_NAMESPACE" -n censysdata --message-retention 1 --partition-count 2  
az eventhubs eventhub create -g "$RG" --namespace-name "$EH_NAMESPACE" -n joinedrecords --message-retention 1 --partition-count 2

# Get connection string
EH_CONN=$(az eventhubs namespace authorization-rule keys list \
  -g "$RG" --namespace-name "$EH_NAMESPACE" --name RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv)
```

### 2. Optional: Create ADLS Gen2

```bash
# ADLS storage account
ADLS_ACCOUNT="cs532adls$(date +%s)"
az storage account create -n "$ADLS_ACCOUNT" -g "$RG" -l "$LOC" \
  --sku Standard_LRS --kind StorageV2 --hierarchical-namespace true

# Filesystem
az storage fs create -n cs532 --account-name "$ADLS_ACCOUNT"

# Grant Function App access
FUNC_PRINCIPAL=$(az functionapp identity assign -g "$RG" -n "$FUNC_APP" --query principalId -o tsv)
ADLS_RESOURCE_ID=$(az storage account show -n "$ADLS_ACCOUNT" -g "$RG" --query id -o tsv)
az role assignment create --assignee "$FUNC_PRINCIPAL" --role "Storage Blob Data Contributor" --scope "$ADLS_RESOURCE_ID"

ADLS_URL="https://${ADLS_ACCOUNT}.dfs.core.windows.net"
```

### 3. Configure App Settings

```bash
# Required settings
az functionapp config appsettings set -g "$RG" -n "$FUNC_APP" --settings \
  "EVENTHUB_CONNECTION=$EH_CONN" \
  "ABUSE_EH_NAME=abuseipdbdata" \
  "CENSYS_EH_NAME=censysdata" \
  "JOINED_EH_NAME=joinedrecords" \
  "ABUSE_API_KEY=<your_abuse_api_key>" \
  "CENSYS_API_TOKEN=<your_censys_token>" \
  "JOINED_OUTPUT_TARGET=eventhub"

# Optional ADLS settings (if using ADLS sink or validator)
az functionapp config appsettings set -g "$RG" -n "$FUNC_APP" --settings \
  "ADLS_ACCOUNT_URL=$ADLS_URL" \
  "ADLS_FILESYSTEM=cs532" \
  "ADLS_DIR_BASE=tor-pipeline"
```

### 4. Deploy

```bash
func azure functionapp publish "$FUNC_APP"
```

### 5. Monitor

```bash
# Function logs
func azure functionapp logstream "$FUNC_APP"

# Event Hub metrics in Azure Portal
# - Navigate to Event Hubs namespace
# - Check "Incoming Messages", "Outgoing Messages" 
# - joinedrecords hub should show periodic bursts every 5 minutes

# ADLS files (if enabled)
az storage fs file list -f cs532 --path tor-pipeline --account-name "$ADLS_ACCOUNT" --query "[].name" -o table
```

## Validation & Metrics

### Event Hub Health
- **Connection**: Namespace SAS policy has Send/Listen rights
- **Partitioning**: Start with 2 partitions, scale up for higher throughput
- **Throughput Units**: Standard tier starts with 1 TU (1MB/s ingress, 2MB/s egress)
- **Metrics**: Portal shows message flow, throttling, consumer lag

### Function Performance  
- **Triggers**: Timer functions run every minute, orchestrator every 5 minutes
- **Scaling**: Consumption plan auto-scales based on Event Hub partition load
- **Errors**: Check Application Insights for exceptions, timeouts

### ADLS Verification
- **Authentication**: Function App Managed Identity needs "Storage Blob Data Contributor" 
- **Structure**: Files appear under `<ADLS_DIR_BASE>/processed/joined/dt=YYYY-MM-DD/hour=HH/`
- **Validator output**: `<ADLS_DIR_BASE>/validated/joined/dt=YYYY-MM-DD/hour=HH/`

## Data Flow

1. **Producers** (every 1 min):
   - `CensysTimer`: Queries Censys API → publishes to `censysdata` hub
   - `AbuseIPDBTimer`: Queries AbuseIPDB API → publishes to `abuseipdbdata` hub

2. **Orchestrator** (every 5 min):
   - `fetch_abuse_batch`: Reads latest from `abuseipdbdata` hub
   - `fetch_censys_batch`: Reads latest from `censysdata` hub  
   - `join_and_enrich`: IP-based join + normalization
   - `sink_joined`: Outputs to Event Hub (`joinedrecords`) or ADLS

3. **Validator** (Event Hub trigger):
   - Consumes `joinedrecords` hub
   - Schema validation, data quality checks
   - Writes validated JSON-lines to ADLS `validated/joined/`

## Schema

### Joined Record Format
```json
{
  "ip": "1.2.3.4",
  "joined_at": "2025-11-06T12:00:00Z",
  "abuse": {
    "abuseConfidenceScore": 42,
    "countryCode": "US",
    "usageType": "isp"
  },
  "censys": {
    "services": ["HTTP", "HTTPS"],
    "location": {
      "country": "US",
      "city": "San Francisco"
    }
  }
}
```

### Validated Record Format  
```json
{
  "ip": "1.2.3.4",
  "joined_at": "2025-11-06T12:00:00Z", 
  "abuse_score": 42,
  "services": ["HTTP", "HTTPS"],
  "location": {
    "country": "US",
    "city": "San Francisco"  
  }
}
```

## Scaling Considerations

- **Event Hub partitions**: Scale up for high throughput (consider 4-8 partitions)
- **Throughput Units**: Bump to 2-5 TUs for production loads
- **Function plan**: Consider Premium plan for consistent performance  
- **ADLS**: Use hierarchical namespace for better performance with many files
- **Batch sizes**: Tune `max_wait_time` in consumers and batch sizes in sink

## Troubleshooting

### Common Issues
- **Import errors**: Ensure all packages in `requirements.txt` are installed
- **Event Hub connection**: Verify connection string format and hub names
- **ADLS permissions**: Function App Managed Identity needs blob permissions
- **Timer not firing**: Check Function App is running and not in stopped state

### Debug Commands
```bash
# Check function status
az functionapp show -g "$RG" -n "$FUNC_APP" --query state

# View recent logs  
az functionapp log tail -g "$RG" -n "$FUNC_APP"

# Test Event Hub connectivity
python test_eventhub.py  # (create simple send/receive test)
```