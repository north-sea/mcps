import type { RequestHandler } from 'express';
import type { HealthSnapshot } from '../service/index.js';

export interface HealthProvider {
  getHealthSnapshot(): Promise<HealthSnapshot>;
}

export interface HealthResponseWriter {
  status(code: number): unknown;
  json(body: unknown): unknown;
  end(): unknown;
}

export function registerHealthRoutes(
  app: {
    get: (path: string, handler: RequestHandler) => unknown;
    head: (path: string, handler: RequestHandler) => unknown;
  },
  provider: HealthProvider
): void {
  app.get('/health', async (_request, response, next) => {
    try {
      await sendHealthResponse(response, await provider.getHealthSnapshot(), true);
    } catch (error) {
      next(error);
    }
  });

  app.head('/health', async (_request, response, next) => {
    try {
      await sendHealthResponse(response, await provider.getHealthSnapshot(), false);
    } catch (error) {
      next(error);
    }
  });
}

export async function sendHealthResponse(
  response: HealthResponseWriter,
  snapshot: HealthSnapshot,
  includeBody: boolean
): Promise<void> {
  const statusCode = getHealthHttpStatus(snapshot);
  response.status(statusCode);

  if (includeBody) {
    response.json(snapshot);
    return;
  }

  response.end();
}

export function getHealthHttpStatus(snapshot: HealthSnapshot): number {
  return snapshot.status === 'unhealthy' ? 503 : 200;
}
