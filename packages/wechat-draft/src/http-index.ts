#!/usr/bin/env node

import 'dotenv/config';
import { createHttpApp } from './http/index.js';
import { createLogger } from './logging/index.js';
import { WechatDraftService } from './service/index.js';

const DEFAULT_PORT = 3001;
const DEFAULT_HOST = '0.0.0.0';

async function main(): Promise<void> {
  const logger = createLogger();
  const service = await WechatDraftService.create();
  service.startHealthMonitor();
  const app = createHttpApp({ service, logger });
  const port = parsePort(process.env.PORT || process.env.WECHAT_DRAFT_PORT);
  const host = process.env.HOST || DEFAULT_HOST;

  const server = app.listen(port, host, () => {
    logger.info({ event: 'service_start', host, port }, 'WeChat Draft MCP HTTP service listening');
  });

  const shutdown = (signal: NodeJS.Signals) => {
    logger.info({ event: 'service_shutdown', signal }, 'Shutting down WeChat Draft MCP HTTP service');
    server.close((error) => {
      if (error) {
        logger.error({ event: 'service_shutdown_failed', error }, 'Failed to close HTTP service cleanly');
        process.exit(1);
      }
      service.stopHealthMonitor();
      process.exit(0);
    });
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

function parsePort(value: string | undefined): number {
  if (!value) {
    return DEFAULT_PORT;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed) || parsed <= 0 || parsed > 65535) {
    throw new Error(`Invalid HTTP port: ${value}`);
  }

  return parsed;
}

main().catch((error) => {
  createLogger().error({ event: 'service_start_failed', error }, 'Failed to start WeChat Draft MCP HTTP service');
  process.exit(1);
});
