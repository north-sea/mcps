#!/bin/bash
# Upload test image to WeChat material library
# Usage: ./upload-test-image.sh <image-path>

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <image-path>"
  exit 1
fi

IMAGE_PATH="$1"
ACCOUNT="weiyuchengchun"
ADAPTER_URL="http://100.117.14.128:3000"
AUTH_TOKEN="${WECHAT_ADAPTER_AUTH_TOKEN}"

# Check if image exists
if [ ! -f "$IMAGE_PATH" ]; then
  echo "Error: Image file not found: $IMAGE_PATH"
  exit 1
fi

# Get access token from adapter
echo "Getting access token..."
TOKEN_RESPONSE=$(curl -s -X POST "$ADAPTER_URL/accounts/$ACCOUNT/check-credentials" \
  -H "Authorization: Bearer $AUTH_TOKEN")

echo "Token response: $TOKEN_RESPONSE"

TOKEN_VALID=$(echo "$TOKEN_RESPONSE" | jq -r '.token_valid')
if [ "$TOKEN_VALID" != "true" ]; then
  echo "Error: Token validation failed"
  exit 1
fi

# Note: WeChat material upload requires direct API call
# This script demonstrates the approach, but actual implementation needs:
# 1. Get access_token from adapter's internal token manager
# 2. Call WeChat API: POST https://api.weixin.qq.com/cgi-bin/material/add_material
#
# For T021 live smoke, we'll use a simpler approach:
# - Create a minimal test artifact without real WeChat images
# - Validate workflow up to payload building
# - Skip actual draft creation (or use placeholder media_id)

echo "
Note: Full material upload requires extending the adapter API.
For T021, we recommend using mock data or existing media_id.
"
