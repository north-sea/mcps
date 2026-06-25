#!/bin/bash
# Quick Deploy - 本地构建后上传
# 适用于 ECS 不安装 pnpm/不在 ECS 构建的情况；ECS 仍需 Node.js 20+ 和 npm

set -e

echo "=== Quick Deploy: WeChat Draft Adapter ==="
echo ""

# Configuration
ECS_HOST="${ECS_HOST:-ali}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/wechat-adapter}"

# Step 1: Build locally
echo "Step 1: Building adapter locally..."
cd "$(dirname "$0")"
pnpm run build

# Step 3: Create deploy directory on ECS
echo "Step 3: Creating deploy directory on ECS..."
ssh "$ECS_HOST" "mkdir -p '$DEPLOY_DIR'"

# Step 4: Copy dist and package.json
echo "Step 4: Copying files to ECS..."
rsync -avz --delete \
  dist/ \
  "$ECS_HOST:$DEPLOY_DIR/dist/"

rsync -avz \
  package.json \
  "$ECS_HOST:$DEPLOY_DIR/"

# Step 5: Check if .env exists
echo "Step 5: Checking environment configuration..."
if ssh "$ECS_HOST" "test -f '$DEPLOY_DIR/.env'"; then
  echo "✅ Environment file exists"
else
  echo "⚠️  Environment file not found at $DEPLOY_DIR/.env"
  echo "Creating template..."
  ssh "$ECS_HOST" "cat > '$DEPLOY_DIR/.env'" << 'EOF'
PORT=3000
ADAPTER_AUTH_TOKEN=change-me
ALLOWED_ACCOUNTS=weiyuchengchun,yueliang,xiaban
WECHAT_APPID_WEIYUCHENGCHUN=wx...
WECHAT_APPSECRET_WEIYUCHENGCHUN=change-me
WECHAT_APPID_YUELIANG=wx...
WECHAT_APPSECRET_YUELIANG=change-me
WECHAT_APPID_XIABAN=wx...
WECHAT_APPSECRET_XIABAN=change-me
EOF
  echo "⚠️  Please update $DEPLOY_DIR/.env with real credentials"
  echo "Run: ssh $ECS_HOST 'nano $DEPLOY_DIR/.env'"
  exit 1
fi

# Step 6: Check Node.js on ECS
echo "Step 6: Checking Node.js on ECS..."
NODE_BIN=$(ssh "$ECS_HOST" "command -v node" 2>/dev/null || true)
if [ -z "$NODE_BIN" ]; then
  echo "❌ Node.js not found on ECS!"
  echo ""
  echo "Please install Node.js on ECS:"
  echo "  1. SSH to ECS: ssh $ECS_HOST"
  echo "  2. Install Node.js 20+:"
  echo "     curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -"
  echo "     sudo yum install -y nodejs"
  echo "  3. Verify: node --version"
  exit 1
fi

NODE_VERSION=$(ssh "$ECS_HOST" "'$NODE_BIN' --version")
echo "✅ Node.js version: $NODE_VERSION ($NODE_BIN)"

echo "Step 6b: Installing production dependencies on ECS..."
ssh "$ECS_HOST" "cd '$DEPLOY_DIR' && npm install --omit=dev"

# Step 7: Setup systemd service
echo "Step 7: Setting up systemd service..."
ssh "$ECS_HOST" "sudo tee /etc/systemd/system/wechat-adapter.service > /dev/null" << EOF
[Unit]
Description=WeChat Draft Adapter
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$DEPLOY_DIR
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=$NODE_BIN $DEPLOY_DIR/dist/index.js
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Reload systemd and restart service
echo "Step 8: Restarting service..."
ssh "$ECS_HOST" "sudo systemctl daemon-reload"
ssh "$ECS_HOST" "sudo systemctl enable wechat-adapter"
ssh "$ECS_HOST" "sudo systemctl restart wechat-adapter"

# Step 9: Wait and check status
echo "Step 9: Checking service status..."
sleep 2
ssh "$ECS_HOST" "sudo systemctl status wechat-adapter --no-pager" || true

# Step 10: Health check
echo ""
echo "Step 10: Health check..."
sleep 1
if ssh "$ECS_HOST" "curl -sf http://localhost:3000/health" > /dev/null; then
  echo "✅ Adapter is running!"
  ssh "$ECS_HOST" "curl -s http://localhost:3000/health | python3 -m json.tool"
  if ssh "$ECS_HOST" "curl -sf http://localhost:3000/health | grep -q asset_upload"; then
    echo "✅ asset_upload capability is present"
  else
    echo "❌ asset_upload capability missing from /health"
    exit 1
  fi
else
  echo "❌ Health check failed!"
  echo ""
  echo "Check logs:"
  echo "  ssh $ECS_HOST 'sudo journalctl -u wechat-adapter -n 50 --no-pager'"
  exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Verify asset_upload capability is present in /health response above."
echo ""
