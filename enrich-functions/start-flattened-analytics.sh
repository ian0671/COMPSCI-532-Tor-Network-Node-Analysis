#!/bin/bash
# Start the Stream Analytics Job to process flattened data

set -e

RESOURCE_GROUP="COMPSCI532"
JOB_NAME="COMPSCI532-FlattenedAnalytics"

echo "🚀 Starting Stream Analytics Job: $JOB_NAME"
echo "================================================"

# Start the job
az stream-analytics job start \
  --resource-group "$RESOURCE_GROUP" \
  --name "$JOB_NAME" \
  --output-start-mode "CustomTime" \
  --output-start-time "2024-01-01T00:00:00Z"

echo ""
echo "✅ Job starting... This will process all 1350 flattened files!"
echo ""
echo "Monitor progress:"
echo "  Portal: https://portal.azure.com/#blade/HubsExtension/BrowseResource/resourceType/Microsoft.StreamAnalytics%2Fstreamingjobs"
echo ""
echo "Check job status:"
echo "  az stream-analytics job show --resource-group $RESOURCE_GROUP --name $JOB_NAME --query 'jobState'"
echo ""
echo "View metrics:"
echo "  az monitor metrics list --resource /subscriptions/\$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.StreamAnalytics/streamingjobs/$JOB_NAME --metric InputEvents,OutputEvents"
echo ""
