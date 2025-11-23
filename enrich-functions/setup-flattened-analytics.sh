#!/bin/bash
# Azure Stream Analytics Setup Script for Flattened Data
# This script creates and configures a Stream Analytics job to read from flattened parquet files

set -e

# Configuration
RESOURCE_GROUP="COMPSCI532"
LOCATION="eastus"
JOB_NAME="COMPSCI532-FlattenedAnalytics"
STORAGE_ACCOUNT="compsci532mlwo6133466000"
STORAGE_CONTAINER_ABUSE="abuseipdb"
STORAGE_CONTAINER_CENSYS="censys"

echo "🚀 Creating Stream Analytics Job: $JOB_NAME"
echo "================================================"

# Step 1: Create Stream Analytics Job
echo ""
echo "Step 1: Creating Stream Analytics Job..."
az stream-analytics job create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$JOB_NAME" \
  --location "$LOCATION" \
  --compatibility-level "1.2" \
  --data-locale "en-US" \
  --tags "Environment=Production" "Purpose=FlattenedDataAnalytics"

echo "✅ Stream Analytics Job created successfully!"

# Step 2: Get Storage Account Key
echo ""
echo "Step 2: Getting storage account key..."
STORAGE_KEY=$(az storage account keys list \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$STORAGE_ACCOUNT" \
  --query '[0].value' \
  --output tsv)

echo "✅ Storage key retrieved"

# Step 3: Create Blob Storage Input for AbuseIPDB
echo ""
echo "Step 3: Creating AbuseIPDB flattened data input..."
cat > /tmp/abuse-input.json <<EOF
{
  "type": "Reference",
  "datasource": {
    "type": "Microsoft.Storage/Blob",
    "properties": {
      "storageAccounts": [
        {
          "accountName": "$STORAGE_ACCOUNT",
          "accountKey": "$STORAGE_KEY"
        }
      ],
      "container": "$STORAGE_CONTAINER_ABUSE",
      "pathPattern": "flattened/",
      "dateFormat": "yyyy/MM/dd",
      "timeFormat": "HH"
    }
  },
  "serialization": {
    "type": "Parquet"
  }
}
EOF

az stream-analytics input create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "FlattenedAbuseIPDB" \
  --properties @/tmp/abuse-input.json

echo "✅ AbuseIPDB input created"

# Step 4: Create Blob Storage Input for Censys
echo ""
echo "Step 4: Creating Censys flattened data input..."
cat > /tmp/censys-input.json <<EOF
{
  "type": "Reference",
  "datasource": {
    "type": "Microsoft.Storage/Blob",
    "properties": {
      "storageAccounts": [
        {
          "accountName": "$STORAGE_ACCOUNT",
          "accountKey": "$STORAGE_KEY"
        }
      ],
      "container": "$STORAGE_CONTAINER_CENSYS",
      "pathPattern": "flattened/",
      "dateFormat": "yyyy/MM/dd",
      "timeFormat": "HH"
    }
  },
  "serialization": {
    "type": "Parquet"
  }
}
EOF

az stream-analytics input create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "FlattenedCensys" \
  --properties @/tmp/censys-input.json

echo "✅ Censys input created"

# Step 5: Create Output for AbuseIPDB Analytics
echo ""
echo "Step 5: Creating analytics outputs..."
cat > /tmp/abuse-output.json <<EOF
{
  "datasource": {
    "type": "Microsoft.Storage/Blob",
    "properties": {
      "storageAccounts": [
        {
          "accountName": "$STORAGE_ACCOUNT",
          "accountKey": "$STORAGE_KEY"
        }
      ],
      "container": "analytics",
      "pathPattern": "abuseipdb/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/{rand-guid}",
      "dateFormat": "yyyy/MM/dd",
      "timeFormat": "HH"
    }
  },
  "serialization": {
    "type": "Parquet"
  }
}
EOF

az stream-analytics output create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "AbuseIPDBAnalyticsOutput" \
  --properties @/tmp/abuse-output.json

echo "✅ AbuseIPDB output created"

# Step 6: Create Output for Censys Analytics
cat > /tmp/censys-output.json <<EOF
{
  "datasource": {
    "type": "Microsoft.Storage/Blob",
    "properties": {
      "storageAccounts": [
        {
          "accountName": "$STORAGE_ACCOUNT",
          "accountKey": "$STORAGE_KEY"
        }
      ],
      "container": "analytics",
      "pathPattern": "censys/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/{rand-guid}",
      "dateFormat": "yyyy/MM/dd",
      "timeFormat": "HH"
    }
  },
  "serialization": {
    "type": "Parquet"
  }
}
EOF

az stream-analytics output create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "CensysAnalyticsOutput" \
  --properties @/tmp/censys-output.json

echo "✅ Censys output created"

# Step 7: Create Output for Combined Analytics
cat > /tmp/combined-output.json <<EOF
{
  "datasource": {
    "type": "Microsoft.Storage/Blob",
    "properties": {
      "storageAccounts": [
        {
          "accountName": "$STORAGE_ACCOUNT",
          "accountKey": "$STORAGE_KEY"
        }
      ],
      "container": "analytics",
      "pathPattern": "combined/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/{rand-guid}",
      "dateFormat": "yyyy/MM/dd",
      "timeFormat": "HH"
    }
  },
  "serialization": {
    "type": "Parquet"
  }
}
EOF

az stream-analytics output create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "CombinedThreatAnalytics" \
  --properties @/tmp/combined-output.json

echo "✅ Combined analytics output created"

# Step 8: Create Output for Hourly Aggregates
cat > /tmp/aggregates-output.json <<EOF
{
  "datasource": {
    "type": "Microsoft.Storage/Blob",
    "properties": {
      "storageAccounts": [
        {
          "accountName": "$STORAGE_ACCOUNT",
          "accountKey": "$STORAGE_KEY"
        }
      ],
      "container": "analytics",
      "pathPattern": "aggregates/year={datetime:yyyy}/month={datetime:MM}/day={datetime:dd}/{rand-guid}",
      "dateFormat": "yyyy/MM/dd",
      "timeFormat": "HH"
    }
  },
  "serialization": {
    "type": "Parquet"
  }
}
EOF

az stream-analytics output create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "HourlyAggregates" \
  --properties @/tmp/aggregates-output.json

echo "✅ Hourly aggregates output created"

# Step 9: Create analytics container if it doesn't exist
echo ""
echo "Step 9: Creating analytics container..."
az storage container create \
  --name analytics \
  --account-name "$STORAGE_ACCOUNT" \
  --account-key "$STORAGE_KEY" \
  --public-access off || echo "Container may already exist"

echo "✅ Analytics container ready"

# Step 10: Set the query
echo ""
echo "Step 10: Setting Stream Analytics query..."

# Read the query from file
QUERY=$(cat enrich-functions/stream-analytics-query-flattened.sql)

# Create transformation
cat > /tmp/transformation.json <<EOF
{
  "streamingUnits": 1,
  "query": $(echo "$QUERY" | jq -Rs .)
}
EOF

az stream-analytics transformation create \
  --resource-group "$RESOURCE_GROUP" \
  --job-name "$JOB_NAME" \
  --name "FlattenedDataTransformation" \
  --properties @/tmp/transformation.json

echo "✅ Query configured"

# Clean up temp files
rm -f /tmp/abuse-input.json /tmp/censys-input.json /tmp/abuse-output.json \
      /tmp/censys-output.json /tmp/combined-output.json /tmp/aggregates-output.json \
      /tmp/transformation.json

echo ""
echo "================================================"
echo "✅ Stream Analytics Job Setup Complete!"
echo "================================================"
echo ""
echo "Job Name: $JOB_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo ""
echo "Inputs:"
echo "  - FlattenedAbuseIPDB (from abuseipdb/flattened/)"
echo "  - FlattenedCensys (from censys/flattened/)"
echo ""
echo "Outputs:"
echo "  - AbuseIPDBAnalyticsOutput (to analytics/abuseipdb/)"
echo "  - CensysAnalyticsOutput (to analytics/censys/)"
echo "  - CombinedThreatAnalytics (to analytics/combined/)"
echo "  - HourlyAggregates (to analytics/aggregates/)"
echo ""
echo "Next step: Start the job!"
echo ""
echo "Run: bash enrich-functions/start-flattened-analytics.sh"
echo ""
