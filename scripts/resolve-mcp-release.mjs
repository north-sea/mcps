#!/usr/bin/env node

import { readFileSync, appendFileSync } from "node:fs";
import path from "node:path";

const [, , tagName, manifestPath = "deploy/mcp-services.json"] = process.argv;

if (!tagName) {
  console.error("Usage: resolve-mcp-release.mjs <tag-name> [manifest-path]");
  process.exit(2);
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const services = manifest.services ?? {};

const serviceName = Object.keys(services)
  .sort((a, b) => b.length - a.length)
  .find((name) => tagName.startsWith(`${name}-`));

if (!serviceName) {
  console.error(`Tag "${tagName}" does not match any service in ${manifestPath}`);
  process.exit(1);
}

const version = tagName.slice(serviceName.length + 1);
if (!/^v\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?$/.test(version)) {
  console.error(
    `Tag "${tagName}" must use service version format like ${serviceName}-v1.2.3`,
  );
  process.exit(1);
}

const service = services[serviceName];
const deploy = service.deploy ?? {};
const test = service.test ?? {};

const outputs = {
  service: serviceName,
  version,
  image: service.image,
  image_ref: `${service.image}:${version}`,
  context: service.context,
  dockerfile: service.dockerfile,
  platforms: (service.platforms ?? ["linux/amd64"]).join(","),
  test_working_directory: test.workingDirectory ?? "",
  test_command: test.command ?? "",
  compose_project_dir: deploy.composeProjectDir ?? "",
  compose_file: deploy.composeFile ?? "docker-compose.yml",
  compose_service: deploy.composeService ?? "",
  container_name: deploy.containerName ?? deploy.composeService ?? "",
};

const githubOutput = process.env.GITHUB_OUTPUT;
if (githubOutput) {
  for (const [key, value] of Object.entries(outputs)) {
    const normalized = String(value);
    if (normalized.includes("\n")) {
      const delimiter = `EOF_${key}_${Date.now()}`;
      appendFileSync(githubOutput, `${key}<<${delimiter}\n${normalized}\n${delimiter}\n`);
    } else {
      appendFileSync(githubOutput, `${key}=${normalized}\n`);
    }
  }
} else {
  console.log(JSON.stringify(outputs, null, 2));
}

const relativeManifest = path.relative(process.cwd(), manifestPath);
console.error(`Resolved ${tagName} using ${relativeManifest || manifestPath}`);
