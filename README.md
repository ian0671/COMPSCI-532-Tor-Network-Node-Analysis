# COMPSCI 532
This is the group project repository for COMPSCI 532.


---

### 🧠 Enrichment Functions – Azure Function App

Two timer-triggered enrichment functions run automatically at fixed intervals, fetch external intelligence data, and stream results to Azure Event Hub for further analysis.

| Function | Trigger | Source | Purpose |
|-----------|----------|---------|----------|
| `CensysTimer` | Every 5 minutes | [Censys API v2](https://search.censys.io/api) | Queries internet hosts and sends metadata (IP, ASN, country, last seen) to Event Hub |
| `AbuseIPDBTimer` | Every 10 minutes | [AbuseIPDB API](https://www.abuseipdb.com/api) | Checks listed IPs for threat reputation and streams results to Event Hub |

---

### ⚙️ Environment Configuration

| Variable | Description |
|-----------|-------------|
| `CENSYS_API_TOKEN` | Bearer token for authenticating Censys API |
| `ABUSE_API_KEY` | API key for AbuseIPDB |
| `ABUSE_IP_LIST` | Optional list of IPs to check (default: `8.8.8.8,1.1.1.1`) |
| `EVENTHUB_CONNECTION` | Azure Event Hub connection string |
| `CENSYS_EH_NAME` | Event Hub name for Censys function output |
| `ABUSE_EH_NAME` | Event Hub name for AbuseIPDB function output |

All values are configured via **Azure App Settings** in the Function App portal.

---

### 💻 Local Development

```bash
# Create and activate virtual environment
python -m venv .venv && source .venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Run locally for testing
func start

# Deploy to Azure Function App
func azure functionapp publish COMPSCI532-Function-App


