import express, { type Express, type NextFunction, type Request, type Response } from 'express';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import type { WechatDraftService } from '../service/index.js';
import { createMcpServer } from '../mcp/index.js';
import { requireBearerAuth, validateHostHeaders, type HostValidationOptions } from './auth.js';
import { registerHealthRoutes } from './health.js';
import { createHttpLogger, createLogger, readRequestId, type AppLogger } from '../logging/index.js';

export interface CreateHttpAppOptions extends HostValidationOptions {
  service: WechatDraftService;
  authToken?: string;
  logger?: AppLogger;
}

export function createHttpApp(options: CreateHttpAppOptions): Express {
  const app = express();
  const logger = options.logger || createLogger();

  app.disable('x-powered-by');
  app.use(createHttpLogger(logger));

  registerHealthRoutes(app, options.service);

  app.post(
    '/mcp',
    validateHostHeaders({
      allowedHosts: options.allowedHosts,
      allowedOrigins: options.allowedOrigins,
    }),
    requireBearerAuth({ authToken: options.authToken }),
    express.json({ limit: '2mb', type: ['application/json', 'application/*+json'] }),
    async (request: Request, response: Response, next: NextFunction) => {
      const requestLogger = getRequestLogger(request, logger);
      const mcpServer = createMcpServer(options.service, {
        logger: requestLogger,
        requestId: getRequestId(request),
      });
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined,
        enableJsonResponse: true,
      });

      try {
        await mcpServer.connect(transport);
        await transport.handleRequest(request, response, request.body);
      } catch (error) {
        next(error);
      } finally {
        await transport.close().catch(() => undefined);
        await mcpServer.close().catch(() => undefined);
      }
    }
  );

  app.all('/mcp', (_request, response) => {
    response
      .status(405)
      .set('Allow', 'POST')
      .json({ error: 'method_not_allowed' });
  });

  app.use((error: unknown, _request: Request, response: Response, next: NextFunction) => {
    if (response.headersSent) {
      next(error);
      return;
    }

    const status = isBodyParserError(error) ? 400 : 500;
    response.status(status).json({
      error: status === 400 ? 'invalid_json' : 'internal_error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  });

  return app;
}

function getRequestLogger(request: Request, fallback: AppLogger): AppLogger {
  return (request as Request & { log?: AppLogger }).log || fallback;
}

function getRequestId(request: Request): string | undefined {
  return (
    (request as Request & { id?: string }).id ||
    readRequestId(request.headers)
  );
}

function isBodyParserError(error: unknown): boolean {
  return Boolean(
    error &&
      typeof error === 'object' &&
      'type' in error &&
      (error as { type?: string }).type === 'entity.parse.failed'
  );
}
