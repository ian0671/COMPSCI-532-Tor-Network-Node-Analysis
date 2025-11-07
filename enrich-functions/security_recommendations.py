"""
Security recommendations for production deployment
"""

# Key Vault integration for secrets management
PRODUCTION_SECRETS = {
    "ABUSEIPDB_API_KEY": "@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/abuseipdb-api-key/)",
    "CENSYS_API_ID": "@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/censys-api-id/)", 
    "CENSYS_SECRET": "@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/censys-secret/)",
    "EVENT_HUB_CONNECTION_STRING": "@Microsoft.KeyVault(SecretUri=https://your-keyvault.vault.azure.net/secrets/eventhub-connection/)"
}

# Managed Identity configuration
MANAGED_IDENTITY_CONFIG = {
    "type": "SystemAssigned",  # Use system-assigned managed identity
    "principalId": "will-be-generated-by-azure",
    "tenantId": "your-tenant-id"
}

# Network security
NETWORK_SECURITY = {
    "vnet_integration": True,
    "private_endpoints": True,
    "ip_restrictions": [
        "10.0.0.0/8",     # Private network only
        "172.16.0.0/12",  # Private network only  
        "192.168.0.0/16"  # Private network only
    ]
}

# API rate limiting recommendations
RATE_LIMITING = {
    "abuseipdb": "1000 requests/day",
    "censys": "120 requests/minute", 
    "event_hub": "Unlimited within quota"
}

print("🔐 Security recommendations:")
print("1. Move API keys to Azure Key Vault")
print("2. Enable system-assigned managed identity")
print("3. Configure VNet integration")
print("4. Set up IP restrictions")
print("5. Implement API rate limiting")