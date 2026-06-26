import type { Request, RequestHandler } from 'express';

export interface BearerAuthOptions {
  authToken?: string;
}

export interface HostValidationOptions {
  allowedHosts?: string[];
  allowedOrigins?: string[];
}

export function requireBearerAuth(options: BearerAuthOptions = {}): RequestHandler {
  const expectedToken = options.authToken ?? process.env.AUTH_TOKEN;

  return (request, response, next) => {
    if (!expectedToken) {
      next();
      return;
    }

    if (isBearerAuthorized(request.headers.authorization, expectedToken)) {
      next();
      return;
    }

    response
      .status(401)
      .set('WWW-Authenticate', 'Bearer realm="wechat-draft"')
      .json({ error: 'unauthorized' });
  };
}

export function validateHostHeaders(options: HostValidationOptions = {}): RequestHandler {
  const allowedHosts = options.allowedHosts ?? readCsvEnv('WECHAT_DRAFT_ALLOWED_HOSTS', 'ALLOWED_HOSTS');
  const allowedOrigins =
    options.allowedOrigins ?? readCsvEnv('WECHAT_DRAFT_ALLOWED_ORIGINS', 'ALLOWED_ORIGINS');

  return (request, response, next) => {
    if (!isRequestHostAllowed(request, allowedHosts)) {
      response.status(403).json({ error: 'host_not_allowed' });
      return;
    }

    if (!isRequestOriginAllowed(request, allowedOrigins)) {
      response.status(403).json({ error: 'origin_not_allowed' });
      return;
    }

    next();
  };
}

export function extractBearerToken(header: string | undefined): string | null {
  if (!header) {
    return null;
  }

  const [scheme, token] = header.split(/\s+/, 2);
  if (scheme?.toLowerCase() !== 'bearer' || !token) {
    return null;
  }

  return token;
}

export function isBearerAuthorized(
  authorizationHeader: string | undefined,
  expectedToken: string | undefined
): boolean {
  if (!expectedToken) {
    return true;
  }

  return extractBearerToken(authorizationHeader) === expectedToken;
}

export function isHostAllowed(hostHeader: string | undefined, allowedHosts: string[]): boolean {
  if (allowedHosts.length === 0) {
    return true;
  }

  if (!hostHeader) {
    return false;
  }

  const normalizedHost = hostHeader.trim().toLowerCase();
  const hostname = extractHostname(normalizedHost);

  return allowedHosts.some((allowedHost) => {
    const normalizedAllowed = allowedHost.trim().toLowerCase();
    return normalizedAllowed === normalizedHost || normalizedAllowed === hostname;
  });
}

export function isOriginAllowed(originHeader: string | undefined, allowedOrigins: string[]): boolean {
  if (allowedOrigins.length === 0 || !originHeader) {
    return true;
  }

  const normalizedOrigin = originHeader.trim().toLowerCase();
  return allowedOrigins.some((allowedOrigin) => {
    return allowedOrigin.trim().toLowerCase() === normalizedOrigin;
  });
}

function isRequestHostAllowed(request: Request, allowedHosts: string[]): boolean {
  return isHostAllowed(request.headers.host, allowedHosts);
}

function isRequestOriginAllowed(request: Request, allowedOrigins: string[]): boolean {
  const origin = request.headers.origin;
  return isOriginAllowed(Array.isArray(origin) ? origin[0] : origin, allowedOrigins);
}

function extractHostname(hostHeader: string): string {
  try {
    return new URL(`http://${hostHeader}`).hostname.toLowerCase();
  } catch {
    return hostHeader.split(':')[0] || hostHeader;
  }
}

function readCsvEnv(primaryName: string, fallbackName: string): string[] {
  const value = process.env[primaryName] || process.env[fallbackName] || '';
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}
