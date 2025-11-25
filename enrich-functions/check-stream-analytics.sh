#!/bin/bash

echo " Stream Analytics Job Status Check"
echo "===================================="

# Check job status
echo " Job Status:"
az stream-analytics job show \
    --resource-group COMPSCI532 \
    --name COMPSCI532-StreamAnalytics \
    --query "{name:name, state:jobState, location:location, sku:sku.name}" \
    --output table

echo ""
echo "📥 Configured Inputs:"
az stream-analytics input list \
    --resource-group COMPSCI532 \
    --job-name COMPSCI532-StreamAnalytics \
    --output table

echo ""
echo "📤 Configured Outputs:"
az stream-analytics output list \
    --resource-group COMPSCI532 \
    --job-name COMPSCI532-StreamAnalytics \
    --output table

echo ""
echo " Next Steps:"
echo "1. Go to Azure Portal: https://portal.azure.com"
echo "2. Search for: COMPSCI532-StreamAnalytics"
echo "3. Add outputs for AbuseIPDBParquetOutput, CensysParquetOutput, CombinedThreatOutput"
echo "4. Add the multi-stream query from stream-analytics-query.sql"
echo "5. Start the job"

echo ""
echo " Complete setup guide: STREAM_ANALYTICS_SETUP.md"