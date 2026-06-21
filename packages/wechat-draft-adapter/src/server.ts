/**
 * ECS WeChat Adapter HTTP Server
 *
 * Provides private HTTP endpoints for NAS-side MCP:
 * - GET /health - Health check
 * - POST /accounts/:account/check-credentials - AccessToken dry-run
 * - POST /accounts/:account/drafts - Create draft
 *
 * Authentication: Bearer token (from env ADAPTER_AUTH_TOKEN)
 * Network: Private endpoint only (Tailscale/WireGuard/SSH tunnel)
 */

import express, { Request, Response, NextFunction, Express } from 'express';
import { TokenManager, TokenError } from './wechat/TokenManager.js';
import { WeChatApiClient, WeChatApiError } from './wechat/WeChatApiClient.js';
import { AccountCredential, DraftAddRequest } from './types/wechat.js';

const PORT = parseInt(process.env.PORT || '3000', 10);
const ADAPTER_AUTH_TOKEN = process.env.ADAPTER_AUTH_TOKEN;
const ALLOWED_ACCOUNTS = (process.env.ALLOWED_ACCOUNTS || 'yueliang').split(',');

// ============================================================================
// Server Setup
// ============================================================================

export function createServer(): Express {
  const app = express();
  app.use(express.json({ limit: '10mb' }));

  // Load credentials
  const credentials = loadCredentials();
  const tokenManager = new TokenManager(credentials);
  const apiClient = new WeChatApiClient(tokenManager);

  // ============================================================================
  // Middleware: Authentication
  // ============================================================================

  const authMiddleware = (req: Request, res: Response, next: NextFunction): void => {
    if (!ADAPTER_AUTH_TOKEN) {
      res.status(500).json({
        error: 'adapter_misconfigured',
        message: 'ADAPTER_AUTH_TOKEN not configured',
      });
      return;
    }

    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({
        error: 'unauthorized',
        message: 'Missing or invalid Authorization header',
      });
      return;
    }

    const token = authHeader.substring(7);
    if (token !== ADAPTER_AUTH_TOKEN) {
      res.status(401).json({
        error: 'unauthorized',
        message: 'Invalid auth token',
      });
      return;
    }

    next();
  };

  // ============================================================================
  // Middleware: Account Validation
  // ============================================================================

  const validateAccount = (req: Request, res: Response, next: NextFunction): void => {
    const account = Array.isArray(req.params.account) ? req.params.account[0] : req.params.account;
    if (!ALLOWED_ACCOUNTS.includes(account)) {
      res.status(403).json({
        error: 'account_not_allowed',
        message: `Account "${account}" is not in allowed list`,
      });
      return;
    }

    if (!credentials.has(account)) {
      res.status(404).json({
        error: 'account_not_found',
        message: `Credential not found for account "${account}"`,
      });
      return;
    }

    next();
  };

  // ============================================================================
  // Routes
  // ============================================================================

  // Health check (no auth required)
  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      capabilities: ['check_credentials', 'draft_add'],
      allowed_accounts: ALLOWED_ACCOUNTS,
    });
  });

  // Check credentials (AccessToken dry-run)
  app.post('/accounts/:account/check-credentials', authMiddleware, validateAccount, async (req, res) => {
    const account = Array.isArray(req.params.account) ? req.params.account[0] : req.params.account;

    try {
      // Try to get token (will refresh if needed)
      await tokenManager.getToken(account);
      const metadata = tokenManager.getTokenMetadata(account);

      res.json({
        success: true,
        account,
        token_valid: metadata.isValid,
        expires_in: metadata.expiresIn,
      });
    } catch (error) {
      if (error instanceof TokenError) {
        res.status(400).json({
          success: false,
          error: 'token_error',
          errcode: error.errcode,
          errmsg: error.errmsg,
          account,
        });
        return;
      }

      res.status(500).json({
        success: false,
        error: 'internal_error',
        message: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  // Create draft
  app.post('/accounts/:account/drafts', authMiddleware, validateAccount, async (req, res) => {
    const account = Array.isArray(req.params.account) ? req.params.account[0] : req.params.account;
    const draftRequest: DraftAddRequest = req.body;

    // Validate request
    if (!draftRequest.articles || !Array.isArray(draftRequest.articles) || draftRequest.articles.length === 0) {
      res.status(400).json({
        success: false,
        error: 'invalid_request',
        message: 'Missing or invalid articles array',
      });
      return;
    }

    try {
      const response = await apiClient.createDraft(account, draftRequest);

      res.json({
        success: true,
        account,
        media_id: response.media_id,
      });
    } catch (error) {
      if (error instanceof WeChatApiError) {
        res.status(400).json({
          success: false,
          error: 'wechat_api_error',
          errcode: error.errcode,
          errmsg: error.errmsg,
          account,
        });
        return;
      }

      if (error instanceof TokenError) {
        res.status(400).json({
          success: false,
          error: 'token_error',
          errcode: error.errcode,
          errmsg: error.errmsg,
          account,
        });
        return;
      }

      res.status(500).json({
        success: false,
        error: 'internal_error',
        message: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  // 404 handler
  app.use((req, res) => {
    res.status(404).json({
      error: 'not_found',
      message: `Endpoint not found: ${req.method} ${req.path}`,
    });
  });

  return app;
}

// ============================================================================
// Credential Loading
// ============================================================================

function loadCredentials(): Map<string, AccountCredential> {
  const credentials = new Map<string, AccountCredential>();

  // Load from environment variables
  // Format: WECHAT_APPID_<ACCOUNT> and WECHAT_APPSECRET_<ACCOUNT>
  for (const account of ALLOWED_ACCOUNTS) {
    const appid = process.env[`WECHAT_APPID_${account.toUpperCase()}`];
    const appsecret = process.env[`WECHAT_APPSECRET_${account.toUpperCase()}`];

    if (appid && appsecret) {
      credentials.set(account, { appid, appsecret });
      console.log(`Loaded credentials for account: ${account}`);
    } else {
      console.warn(`Missing credentials for account: ${account}`);
    }
  }

  return credentials;
}

// ============================================================================
// Start Server
// ============================================================================

export function startServer() {
  const app = createServer();

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`WeChat Adapter running on port ${PORT}`);
    console.log(`Allowed accounts: ${ALLOWED_ACCOUNTS.join(', ')}`);
  });
}
