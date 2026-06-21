#!/bin/bash
# Generate secure ADAPTER_AUTH_TOKEN

TOKEN=$(openssl rand -base64 32)

echo "=== Generated ADAPTER_AUTH_TOKEN ==="
echo ""
echo "$TOKEN"
echo ""
echo "Add this to:"
echo "1. ECS: /opt/wechat-adapter/.env"
echo "2. Local: ~/.zshrc or ~/.bashrc"
echo "   export WECHAT_ADAPTER_AUTH_TOKEN=\"$TOKEN\""
echo ""
