# COMPSCI 532 - Threat Intelligence Pipeline
## Cloud-based ML Pipeline for Real-time Cybersecurity Threat Detection

[![Azure](https://img.shields.io/badge/Azure-Functions%20%7C%20ML%20%7C%20Stream%20Analytics-0078D4?logo=microsoftazure)](https://portal.azure.com)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Production-success)]()

This is a comprehensive threat intelligence pipeline built on Azure, combining real-time data enrichment, stream processing, and machine learning for cybersecurity threat detection.

---

##  Architecture Overview

```
External APIs → Azure Functions → Event Hub → Stream Analytics → Blob Storage → ML Pipeline
   (Censys,      (Enrichment)      (Ingest)    (Flatten Data)   (Parquet)    (Scikit-learn)
   AbuseIPDB)
```

### Key Components

1. **Data Enrichment** - Azure Functions fetch threat intelligence from external APIs
2. **Stream Processing** - Event Hub ingests real-time data, Stream Analytics flattens and stores
3. **Storage Layer** - Blob Storage with flattened Parquet files for efficient queries
4. **ML Pipeline** - Random Forest model for threat classification and risk scoring
5. **Blob Triggers** - Automatic flattening of nested Parquet structures

---

##  Enrichment Functions – Azure Function App

Two timer-triggered enrichment functions run automatically at fixed intervals, fetch external intelligence data, and stream results to Azure Event Hub for further analysis.

| Function | Trigger | Source | Purpose |
|-----------|----------|---------|----------|
| `CensysTimer` | Every 5 minutes | [Censys API v2](https://search.censys.io/api) | Queries internet hosts and sends metadata (IP, ASN, country, last seen) to Event Hub |
| `AbuseIPDBTimer` | Every 10 minutes | [AbuseIPDB API](https://www.abuseipdb.com/api) | Checks listed IPs for threat reputation and streams results to Event Hub |

---

##  Stream Analytics & Data Flattening

### Problem Solved
Azure Parquet files with nested structures (arrays, objects) caused `ParquetType-NotSupported` errors when browsing in the Portal.

### Solution
**Stream Analytics Query** - Flattens all nested structures before writing to Parquet:
- Arrays (`ips`, `services`, `reports`) → JSON strings + extracted key fields
- Objects (`location`, `autonomous_system`) → JSON strings + extracted properties
- All complex types cast to `NVARCHAR(MAX)` for compatibility

**Blob Triggers** - Automatic flattening of existing files:
- `flatten_blob_trigger` - Monitors `abuseipdb` container
- `flatten_blob_trigger_censys` - Monitors `censys` container
- Writes flattened output to `flattened/` prefix

📄 See [STREAM_ANALYTICS_FIX_COMPLETE.md](STREAM_ANALYTICS_FIX_COMPLETE.md) for details

---

##  Machine Learning Pipeline

### Features
- **Threat Classification** - Random Forest model trained on labeled threat intelligence
- **Risk Scoring** - Multi-factor risk assessment combining AbuseIPDB confidence and Censys port data
- **Real-time Inference** - Loads data from Azure Blob Storage for predictions
- **Azure ML Integration** - Model training and deployment on Azure ML workspace

### Data Sources
| Source | Records | Features |
|--------|---------|----------|
| AbuseIPDB | 675+ | IP, abuse_score, reports, country, isTor |
| Censys | 675+ | IP, services, ports, ASN, location |
| Tor Relays | 100+ | IP, consensus_weight, exit_policy |

### Model Performance
- **Accuracy**: Trained on flattened data with extracted features
- **Deployment**: Azure ML endpoint ready for real-time scoring
- **Storage**: Models saved in `azureml` blob container

📄 See [ML_FLATTENED_DATA_GUIDE.md](ML_FLATTENED_DATA_GUIDE.md) for usage

---

##  Environment Configuration

| Variable | Description |
|-----------|-------------|
| `CENSYS_API_TOKEN` | Bearer token for authenticating Censys API |
| `ABUSE_API_KEY` | API key for AbuseIPDB |
| `ABUSE_IP_LIST` | Optional list of IPs to check (default: `8.8.8.8,1.1.1.1`) |
| `EVENTHUB_CONNECTION` | Azure Event Hub connection string |
| `CENSYS_EH_NAME` | Event Hub name for Censys function output |
| `ABUSE_EH_NAME` | Event Hub name for AbuseIPDB function output |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string for blob storage |
| `AzureWebJobsStorage` | Storage account for Azure Functions |

All values are configured via **Azure App Settings** in the Function App portal.

---

##  Local Development

### Prerequisites
- Python 3.12+
- Azure CLI
- Azure Functions Core Tools
- Valid Azure credentials

### Setup

```bash
# Clone repository
git clone https://github.com/ian0671/COMPSCI-532.git
cd COMPSCI-532

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r ml-requirements.txt

# Configure Azure CLI
az login
az account set --subscription "your-subscription-id"

# Run enrichment functions locally
cd enrich-functions
func start

# Run ML pipeline
python src/ml_threat_detection.py
```

### Deploy to Azure

```bash
# Deploy enrichment functions
cd enrich-functions
func azure functionapp publish COMPSCI532-Function-App

# Deploy flatten functions
cd ../azure_function_flatten
func azure functionapp publish COMPSCI532-Function-App

# Deploy ML model
python deploy/azure_ml_deploy.py
```

---

##  Project Structure

```
COMPSCI-532/
├── enrich-functions/          # Azure Functions for data enrichment
│   ├── function_app.py        # Timer-triggered functions (Censys, AbuseIPDB)
│   ├── stream-analytics-query-fixed.sql  # Flattened Stream Analytics query
│   └── STREAM_ANALYTICS_FLATTENED_SETUP.md
├── azure_function_flatten/    # Blob trigger functions for flattening
│   ├── function_app.py        # Python v2 model with blob triggers
│   ├── flatten_blob_trigger/  # AbuseIPDB flattening
│   └── flatten_blob_trigger_censys/  # Censys flattening
├── src/                       # ML pipeline source code
│   ├── ml_threat_detection.py # Main ML training script
│   ├── features.py            # Feature engineering
│   ├── train.py               # Model training utilities
│   └── azure_ml_train.py      # Azure ML integration
├── deploy/                    # Deployment scripts
│   └── azure_ml_deploy.py     # ML model deployment
├── scripts/                   # Utility scripts
│   └── batch_flatten_and_upload.py  # Batch parquet flattening
├── README.md                  # This file
├── STREAM_ANALYTICS_FIX_COMPLETE.md  # Stream Analytics fix documentation
├── ML_FLATTENED_DATA_GUIDE.md        # ML pipeline guide
└── AZURE_PIPELINE_TEST_RESULTS.md    # Complete test results
```

---

##  Key Features

###  Automated Data Collection
- Timer-triggered Azure Functions fetch data every 5-10 minutes
- Event Hub handles real-time streaming ingestion
- Scalable architecture for high-volume data processing

###  Intelligent Data Flattening
- **Stream Analytics Query** - Flattens nested structures in real-time
- **Blob Triggers** - Automatically processes existing files
- **JSON Serialization** - Complex types stored as strings for Parquet compatibility

###  Machine Learning Pipeline
- **Random Forest Classifier** - Threat detection and risk scoring
- **Feature Engineering** - Extracts meaningful signals from raw data
- **Azure ML Integration** - Model training, versioning, and deployment
- **Real-time Inference** - Loads flattened data directly from blob storage

###  Production-Ready
- **Error Handling** - Comprehensive logging and monitoring
- **Authentication** - Azure CLI credentials via DefaultAzureCredential
- **Scalability** - Handles 1350+ files with batch processing
- **Documentation** - Complete setup guides and test results

---

##  Data Flow

1. **Collection**: External APIs (Censys, AbuseIPDB) → Azure Functions
2. **Ingestion**: Azure Functions → Event Hub (real-time stream)
3. **Processing**: Event Hub → Stream Analytics (flatten nested data)
4. **Storage**: Stream Analytics → Blob Storage (Parquet files)
5. **Trigger**: New blobs → Flatten Functions (additional processing)
6. **Analysis**: ML Pipeline → Load flattened data → Train/Predict

---

##  Use Cases

- **Threat Intelligence Aggregation** - Combine multiple data sources for comprehensive threat analysis
- **Risk Scoring** - Automated assessment of IP reputation and behavior
- **Security Analytics** - Real-time detection of malicious activity patterns
- **Research & Training** - ML model development on labeled threat data

---

##  Documentation

| Document | Description |
|----------|-------------|
| [STREAM_ANALYTICS_FIX_COMPLETE.md](STREAM_ANALYTICS_FIX_COMPLETE.md) | Complete guide to the flattening fix |
| [ML_FLATTENED_DATA_GUIDE.md](ML_FLATTENED_DATA_GUIDE.md) | ML pipeline usage and integration |
| [AZURE_PIPELINE_TEST_RESULTS.md](AZURE_PIPELINE_TEST_RESULTS.md) | Comprehensive testing validation |
| [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) | Deployment history and status |

---

##  Production Status

| Component | Status | Details |
|-----------|--------|---------|
| Enrichment Functions |  Running | Timer-triggered every 5-10 min |
| Stream Analytics |  Running | Flattening query deployed |
| Blob Triggers |  Deployed | Auto-flatten on upload |
| ML Pipeline |  Functional | Loads from flattened/ folders |
| Storage |  Ready | 1350+ flattened files available |

---

##  Contributors

**COMPSCI 532 Group Project**
- University of Massachusetts Amherst
- Cloud Computing & Machine Learning Course

---

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

##  Resources

- [Azure Functions Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [Azure Stream Analytics](https://docs.microsoft.com/en-us/azure/stream-analytics/)
- [Azure Machine Learning](https://docs.microsoft.com/en-us/azure/machine-learning/)
- [Censys API](https://search.censys.io/api)
- [AbuseIPDB API](https://www.abuseipdb.com/api)

---

**Last Updated**: November 23, 2025  
**Branch**: amogh-deploy  
**Azure Resource Group**: COMPSCI532


