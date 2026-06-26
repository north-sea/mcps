import type { IncomingHttpHeaders, IncomingMessage, ServerResponse } from 'node:http';
import { randomUUID } from 'node:crypto';
import pino, { type DestinationStream, type Logger, type LoggerOptions } from 'pino';
import pinoHttp from 'pino-http';
import { SERVICE_VERSION } from '../version.js';

export type AppLogger = Logger;

export interface CreateLoggerOptions {
  level?: string;
  stream?: DestinationStream;
}

export function createLogger(options: CreateLoggerOptions = {}): AppLogger {
  const loggerOptions: LoggerOptions = {
    level: options.level || process.env.WECHAT_DRAFT_LOG_LEVEL || process.env.LOG_LEVEL || 'info',
    base: {
      service: 'wechat-draft-mcp',
      version: SERVICE_VERSION,
    },
    timestamp: pino.stdTimeFunctions.isoTime,
    redact: {
      censor: '<redacted>',
      paths: [
        'authorization',
        'Authorization',
        'auth_token',
        'token',
        'access_token',
        'secret',
        'req.headers.authorization',
        'req.headers.cookie',
        'headers.authorization',
        'headers.cookie',
      ],
    },
  };

  return options.stream ? pino(loggerOptions, options.stream) : pino(loggerOptions);
}

export function createHttpLogger(logger: AppLogger = createLogger()) {
  return pinoHttp({
    logger,
    genReqId: (request) => readRequestId(request.headers) || randomUUID(),
    customLogLevel: (_request, response, error) => {
      if (error || response.statusCode >= 500) {
        return 'error';
      }
      return 'info';
    },
    serializers: {
      req(request: IncomingMessage & { id?: string }) {
        return {
          id: request.id,
          method: request.method,
          url: sanitizeLogUrl(request.url),
          remoteAddress: request.socket?.remoteAddress,
        };
      },
      res(response: ServerResponse) {
        return {
          statusCode: response.statusCode,
        };
      },
      err: pino.stdSerializers.err,
    },
  });
}

export function readRequestId(headers: IncomingHttpHeaders): string | undefined {
  const value = headers['x-request-id'];
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

export function sanitizeLogUrl(value: string | undefined): string | undefined {
  if (!value) {
    return value;
  }

  try {
    const url = new URL(value, 'http://localhost');
    url.username = '';
    url.password = '';

    for (const key of Array.from(url.searchParams.keys())) {
      if (isSensitiveQueryParam(key)) {
        url.searchParams.set(key, '<redacted>');
      }
    }

    return `${url.pathname}${url.search}`;
  } catch {
    return value.replace(/([?&](?:token|access_token|auth|authorization|key|secret)=)[^&\s]+/gi, '$1<redacted>');
  }
}

function isSensitiveQueryParam(key: string): boolean {
  return /^(token|access_token|auth|authorization|key|secret)$/i.test(key);
}
