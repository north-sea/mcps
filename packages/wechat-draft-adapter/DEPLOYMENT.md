# WeChat Draft Adapter - Docker Deployment Guide

**Service**: `wechat-draft-adapter`  
**Deployment**: Docker on Ali ECS  
**Network**: Private endpoint (Tailscale/WireGuard/SSH tunnel)

---

## Prerequisites

### 1. ECS Environment

- Ali ECS instance with Docker installed
- Public IP/EIP configured in WeChat IP whitelist
- Private network access (Tailscale/WireGuard/SSH tunnel) from NAS

### 2. WeChat Credentials

- WeChat AppID and AppSecret for each allowed account. Current production accounts include `weiyuchengchun`, `yueliang`, and `xiaban`.
- IP whitelist configured in WeChat backend

### 3. Environment Variables

Required environment variables:

```bash
# Adapter auth token (shared secret with NAS)
ADAPTER_AUTH_TOKEN=<random-secure-token>

# WeChat credentials (one pair per account)
WECHAT_APPID_YUELIANG=<appid>
WECHAT_APPSECRET_YUELIANG=<appsecret>
WECHAT_APPID_XIABAN=<appid>
WECHAT_APPSECRET_XIABAN=<appsecret>

# Allowed accounts (comma-separated)
ALLOWED_ACCOUNTS=weiyuchengchun,yueliang,xiaban

# Port (optional, default: 3000)
PORT=3000
```

---

## Build Docker Image

### On Development Machine

```bash
cd packages/wechat-draft-adapter

# Build image
docker build -t wechat-draft-adapter:latest .

# Tag for registry (if using private registry)
docker tag wechat-draft-adapter:latest your-registry/wechat-draft-adapter:latest

# Push to registry
docker push your-registry/wechat-draft-adapter:latest
```

### On ECS (Alternative: Build Directly)

```bash
# Clone repo
git clone <your-repo> /opt/mcps
cd /opt/mcps/packages/wechat-draft-adapter

# Build image
docker build -t wechat-draft-adapter:latest .
```

---

## Run Container

### Docker Run (Recommended for Production)

```bash
docker run -d \
  --name wechat-adapter \
  --restart unless-stopped \
  -p 127.0.0.1:3000:3000 \
  -e ADAPTER_AUTH_TOKEN="${ADAPTER_AUTH_TOKEN}" \
  -e WECHAT_APPID_YUELIANG="${WECHAT_APPID_YUELIANG}" \
  -e WECHAT_APPSECRET_YUELIANG="${WECHAT_APPSECRET_YUELIANG}" \
  -e WECHAT_APPID_XIABAN="${WECHAT_APPID_XIABAN}" \
  -e WECHAT_APPSECRET_XIABAN="${WECHAT_APPSECRET_XIABAN}" \
  -e ALLOWED_ACCOUNTS="weiyuchengchun,yueliang,xiaban" \
  wechat-draft-adapter:latest
```

**Notes**:
- `-p 127.0.0.1:3000:3000`: Only bind to localhost (access via Tailscale/WireGuard)
- `--restart unless-stopped`: Auto-restart on failure
- Environment variables from secure source (e.g., `.env` file or secrets manager)

### Docker Compose (Alternative)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  wechat-adapter:
    image: wechat-draft-adapter:latest
    container_name: wechat-adapter
    restart: unless-stopped
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - ADAPTER_AUTH_TOKEN=${ADAPTER_AUTH_TOKEN}
      - WECHAT_APPID_YUELIANG=${WECHAT_APPID_YUELIANG}
      - WECHAT_APPSECRET_YUELIANG=${WECHAT_APPSECRET_YUELIANG}
      - ALLOWED_ACCOUNTS=weiyuchengchun,yueliang,xiaban
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"]
      interval: 30s
      timeout: 3s
      retries: 3
```

Start:

```bash
docker-compose up -d
```

---

## Environment Variables Management

### Option A: .env File (Simple)

Create `/opt/wechat-adapter/.env`:

```bash
ADAPTER_AUTH_TOKEN=your-secure-token-here
WECHAT_APPID_YUELIANG=wx1234567890abcdef
WECHAT_APPSECRET_YUELIANG=1234567890abcdef1234567890abcdef
WECHAT_APPID_XIABAN=wxabcdef1234567890
WECHAT_APPSECRET_XIABAN=abcdef1234567890abcdef1234567890
ALLOWED_ACCOUNTS=weiyuchengchun,yueliang,xiaban
```

Load and run:

```bash
docker run -d \
  --name wechat-adapter \
  --restart unless-stopped \
  -p 127.0.0.1:3000:3000 \
  --env-file /opt/wechat-adapter/.env \
  wechat-draft-adapter:latest
```

**Security**: Restrict .env file permissions:

```bash
chmod 600 /opt/wechat-adapter/.env
chown root:root /opt/wechat-adapter/.env
```

### Option B: Docker Secrets (Recommended for Production)

Use Docker Swarm secrets or external secrets manager (Ali KMS, HashiCorp Vault).

---

## Verify Deployment

### 1. Check Container Status

```bash
docker ps | grep wechat-adapter
docker logs wechat-adapter
```

Expected output:

```
WeChat Adapter running on port 3000
Allowed accounts: weiyuchengchun, yueliang, xiaban
Loaded credentials for account: yueliang
Loaded credentials for account: xiaban
```

### 2. Health Check

```bash
curl http://localhost:3000/health
```

Expected response:

```json
{
  "status": "ok",
  "capabilities": ["check_credentials", "draft_add", "draft_batchget", "asset_upload"],
  "allowed_accounts": ["weiyuchengchun", "yueliang", "xiaban"]
}
```

### 3. Check Credentials (From NAS via Tailscale)

```bash
curl -X POST http://<ECS_TAILSCALE_IP>:3000/accounts/xiaban/check-credentials \
  -H "Authorization: Bearer ${ADAPTER_AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

Expected response:

```json
{
  "success": true,
  "account": "xiaban",
  "token_valid": true,
  "expires_in": 7200
}
```

---

## Monitoring

### Container Logs

```bash
# Real-time logs
docker logs -f wechat-adapter

# Last 100 lines
docker logs --tail 100 wechat-adapter
```

### Health Check

```bash
# Check container health
docker inspect wechat-adapter | grep -A 5 Health
```

### Restart Container

```bash
docker restart wechat-adapter
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs wechat-adapter

# Common issues:
# - Missing ADAPTER_AUTH_TOKEN
# - Missing WeChat credentials
# - Port already in use
```

### Token Error (40001, 40013)

- **Cause**: Invalid AppID/AppSecret
- **Fix**: Verify credentials in WeChat backend

### IP Whitelist Error (40164)

- **Cause**: ECS public IP not in WeChat IP whitelist
- **Fix**: 
  1. Get ECS public IP: `curl ifconfig.me`
  2. Add to WeChat backend IP whitelist

### Adapter Unreachable from NAS

- **Cause**: Private network (Tailscale/WireGuard) not configured
- **Fix**: 
  1. Verify Tailscale/WireGuard running on both ECS and NAS
  2. Test connectivity: `ping <ECS_TAILSCALE_IP>`
  3. Check firewall rules

---

## Update and Rollback

### Update to New Version

```bash
# Pull new image
docker pull wechat-draft-adapter:latest

# Stop and remove old container
docker stop wechat-adapter
docker rm wechat-adapter

# Run new container (same command as initial deployment)
docker run -d \
  --name wechat-adapter \
  --restart unless-stopped \
  -p 127.0.0.1:3000:3000 \
  --env-file /opt/wechat-adapter/.env \
  wechat-draft-adapter:latest
```

### Rollback

```bash
# Stop current container
docker stop wechat-adapter
docker rm wechat-adapter

# Run previous version
docker run -d \
  --name wechat-adapter \
  --restart unless-stopped \
  -p 127.0.0.1:3000:3000 \
  --env-file /opt/wechat-adapter/.env \
  wechat-draft-adapter:<previous-version>
```

---

## Security Checklist

- ✅ Container only binds to localhost (127.0.0.1)
- ✅ Access only via private network (Tailscale/WireGuard)
- ✅ ADAPTER_AUTH_TOKEN is strong random token
- ✅ .env file has restricted permissions (600)
- ✅ WeChat credentials not logged
- ✅ ECS public IP in WeChat whitelist
- ✅ Container runs as non-root user
- ✅ No publish/update/delete endpoints exposed

---

## Maintenance

### Token Cache

Token is cached for 7200s (2 hours) with 300s safety margin. No manual cache management needed.

### Log Rotation

Docker handles log rotation. Configure in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Backup

No persistent data. Secrets should be backed up in secure secrets manager.
