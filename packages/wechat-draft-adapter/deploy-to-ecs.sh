#!/bin/bash
# ECS Adapter Deployment Script
# Usage: ./deploy-to-ecs.sh

set -e

echo "=== WeChat Draft Adapter Deployment ==="
echo ""

# Configuration
ECS_HOST="ali"  # SSH alias
DEPLOY_DIR="/opt/wechat-adapter"
ENV_FILE="$DEPLOY_DIR/.env"

# Step 1: Build locally
echo "Step 1: Building adapter..."
cd "$(dirname "$0")"
pnpm run build

# Step 2: Create deploy directory on ECS
echo "Step 2: Creating deploy directory on ECS..."
ssh $ECS_HOST "mkdir -p $DEPLOY_DIR"

# Step 3: Copy files to ECS
echo "Step 3: Copying files to ECS..."
rsync -avz --exclude node_modules --exclude .git --exclude dist \
  . $ECS_HOST:$DEPLOY_DIR/

# Step 4: Install dependencies on ECS
echo "Step 4: Installing dependencies on ECS..."
ssh $ECS_HOST "cd $DEPLOY_DIR && npm install --omit=dev"

# Step 5: Build on ECS
echo "Step 5: Building on ECS..."
ssh $ECS_HOST "cd $DEPLOY_DIR && npm run build"

# Step 6: Check if .env exists
echo "Step 6: Checking environment configuration..."
if ssh $ECS_HOST "test -f $ENV_FILE"; then
  echo "✅ Environment file exists at $ENV_FILE"
else
  echo "⚠️  Environment file not found!"
  echo "Please create $ENV_FILE on ECS with:"
  echo ""
  cat << 'EOF'
PORT=3000
ADAPTER_AUTH_TOKEN=<generate-with-openssl-rand-base64-32>
ALLOWED_ACCOUNTS=yueliang
WECHAT_APPID_YUELIANG=wx...
WECHAT_APPSECRET_YUELIANG=<your-secret>
EOF
  echo ""
  echo "Run: ssh $ECS_HOST 'nano $ENV_FILE'"
  exit 1
fi

# Step 7: Setup systemd service
echo "Step 7: Setting up systemd service..."
ssh $ECS_HOST "sudo tee /etc/systemd/system/wechat-adapter.service" << 'EOF'
[Unit]
Description=WeChat Draft Adapter
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wechat-adapter
EnvironmentFile=/opt/wechat-adapter/.env
ExecStart=/usr/bin/node /opt/wechat-adapter/dist/server.js
Restart=on-failure
RestartSec=10s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Reload systemd and start service
echo "Step 8: Starting service..."
ssh $ECS_HOST "sudo systemctl daemon-reload"
ssh $ECS_HOST "sudo systemctl enable wechat-adapter"
ssh $ECS_HOST "sudo systemctl restart wechat-adapter"

# Step 9: Wait and check status
echo "Step 9: Checking service status..."
sleep 2
ssh $ECS_HOST "sudo systemctl status wechat-adapter --no-pager"

# Step 10: Health check
echo ""
echo "Step 10: Health check..."
if ssh $ECS_HOST "curl -s http://localhost:3000/health | grep ok"; then
  echo "✅ Adapter is running!"
else
  echo "❌ Health check failed!"
  echo "Check logs: ssh $ECS_HOST 'sudo journalctl -u wechat-adapter -n 50'"
  exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Get ECS public IP: ssh $ECS_HOST 'curl -s ifconfig.me'"
echo "2. Add IP to WeChat IP whitelist"
echo "3. Test token: ssh $ECS_HOST 'curl -X POST http://localhost:3000/accounts/yueliang/check-credentials -H \"Authorization: Bearer \$ADAPTER_AUTH_TOKEN\"'"
echo ""
