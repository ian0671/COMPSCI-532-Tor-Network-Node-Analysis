#!/usr/bin/env zsh
# Deploy updated flatten functions to Azure Function App.
# Usage: ./deploy.sh <function_app_name> <resource_group>
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: $0 <function_app_name> <resource_group>" >&2
  exit 1
fi
APP="$1"
RG="$2"

if ! command -v func >/dev/null 2>&1; then
  echo "Azure Functions Core Tools 'func' not found. Install first." >&2
  exit 2
fi

pushd "$(dirname $0)" >/dev/null

echo "Publishing Python functions to $APP (RG: $RG)"
func azure functionapp publish "$APP" --python

echo "Deployment complete. Verify in portal: Functions list should include both flatten triggers."
