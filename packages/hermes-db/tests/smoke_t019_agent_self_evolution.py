#!/usr/bin/env python3
"""
T019 deployed live smoke for agent_self_evolution foundation.

Workflow:
1. Insert an approved learning_candidate via SQL
2. promote_learning_candidate_to_policy via MCP
3. get_applicable_agent_policies via MCP
4. record_policy_application via MCP
5. list_policy_applications via MCP
6. Cleanup test candidate and policy via SQL

Usage:
  python3 smoke_t019_agent_self_evolution.py <mcp_url> <api_token> <pg_dsn>

Example:
  python3 smoke_t019_agent_self_evolution.py \
    http://127.0.0.1:8765/mcp \
    "$(ssh nas 'grep ^API_TOKEN= /vol1/1000/Docker/hermes-db-mcp/.env | cut -d= -f2-')" \
    "$(ssh nas 'grep ^PG_DSN= /vol1/1000/Docker/hermes-db-mcp/.env | cut -d= -f2-')"
"""
import json
import sys
import time
import urllib.request
from urllib.error import URLError
from uuid import uuid4
from datetime import date


def mcp_call(url: str, token: str, tool_name: str, arguments: dict, *, attempt_limit=5):
    """Call MCP tool via streamable HTTP."""
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    request_obj = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    last_error = None
    for attempt in range(1, attempt_limit + 1):
        try:
            with urllib.request.urlopen(request_obj, timeout=15) as response:
                raw = response.read().decode("utf-8")
            print(f"   [DEBUG] {tool_name} raw response (first 800 chars):\n{raw[:800]}")
            if not raw.strip():
                raise ValueError(f"Empty response from MCP {tool_name}")
            break
        except (ConnectionError, TimeoutError, URLError, OSError) as exc:
            last_error = exc
            if attempt == attempt_limit:
                raise SystemExit(f"MCP {tool_name} failed after {attempt_limit} attempts: {last_error}")
            time.sleep(min(attempt, 3))

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"MCP {tool_name} returned invalid JSON: {e}\nRaw: {raw[:500]}")

    if "error" in data:
        raise SystemExit(f"MCP {tool_name} returned error: {data['error']}")

    result = data.get("result", {})
    structured = result.get("structuredContent")
    if structured:
        return structured

    content = result.get("content", [])
    if not content:
        raise SystemExit(f"MCP {tool_name} response missing content: {data}")

    text = content[0].get("text")
    if text is None:
        raise SystemExit(f"MCP {tool_name} response missing text: {data}")

    return json.loads(text)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    mcp_url, api_token, pg_dsn = sys.argv[1:4]

    # Import asyncpg inline to avoid dependency in workflow
    try:
        import asyncio
        import asyncpg
    except ImportError:
        raise SystemExit("asyncpg not available; install with: pip install asyncpg")

    candidate_id = uuid4()
    report_id = uuid4()
    policy_id_holder = {}

    async def run_smoke():
        conn = await asyncpg.connect(pg_dsn)
        try:
            # 1. Insert dummy report and approved test candidate
            print(f"1. Inserting test report and candidate...")
            await conn.execute(
                """
                INSERT INTO hermes.wechat_retrospective_reports (
                    report_id, account, report_type, period_start, period_end,
                    scoring_version, generation_mode, status, summary_json
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                report_id,
                "test-smoke",
                "weekly",
                date(2026, 1, 1),
                date(2026, 1, 7),
                "v1.0-smoke",
                "structured_only",
                "completed",
                json.dumps({"note": "T019 smoke dummy report"}),
            )

            print(f"   ✓ dummy report {report_id}")

            await conn.execute(
                """
                INSERT INTO hermes.learning_candidates (
                    candidate_id, account, domain, source_report_id,
                    source_suggestion_ids_json, candidate_type, scope_json,
                    trigger_conditions_json, proposed_policy_json, confidence,
                    evidence_refs_json, status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                candidate_id,
                "test-smoke",
                "wechat",
                report_id,
                json.dumps([]),
                "topic_strategy",
                json.dumps({"account": "test-smoke"}),
                json.dumps({}),
                json.dumps({"hint": "T019 smoke test policy"}),
                0.9,
                json.dumps({}),
                "approved",
            )

            print(f"   ✓ approved candidate {candidate_id}")

            # 2. Promote candidate to policy via MCP
            print(f"2. Promoting candidate to policy via MCP...")
            promote_result = mcp_call(
                mcp_url,
                api_token,
                "promote_learning_candidate_to_policy",
                {
                    "input": {
                        "candidate_id": str(candidate_id),
                        "approved_by": "t019-smoke",
                        "review_note": "T019 deployed live smoke",
                    }
                },
            )

            if "error" in promote_result:
                raise SystemExit(f"promote failed: {promote_result}")

            policy_id = promote_result["policy_id"]
            policy_version_id = promote_result["policy_version_id"]
            policy_version = promote_result["version"]
            policy_id_holder["policy_id"] = policy_id

            print(f"   ✓ policy_id={policy_id}, version={policy_version}")

            # 3. Query applicable policies via MCP
            print(f"3. Querying applicable policies...")
            applicable_result = mcp_call(
                mcp_url,
                api_token,
                "get_applicable_agent_policies",
                {
                    "input": {
                        "domain": "wechat",
                        "scope": {"account": "test-smoke"},
                        "task_type": "topic_planning",
                    }
                },
            )

            if "error" in applicable_result:
                raise SystemExit(f"get_applicable failed: {applicable_result}")

            items = applicable_result.get("items", [])
            if not any(p["policy_id"] == policy_id for p in items):
                raise SystemExit(f"Promoted policy not in applicable result: {applicable_result}")

            print(f"   ✓ found {len(items)} applicable policies, including promoted one")

            # 4. Record policy application via MCP
            print(f"4. Recording policy application...")
            record_result = mcp_call(
                mcp_url,
                api_token,
                "record_policy_application",
                {
                    "input": {
                        "domain": "wechat",
                        "agent_name": "t019-smoke-agent",
                        "task_type": "topic_planning",
                        "decision_point": "select_strategy",
                        "policy_id": policy_id,
                        "policy_version_id": policy_version_id,
                        "policy_version": policy_version,
                        "scope": {"account": "test-smoke"},
                        "matched_conditions": {},
                        "application_status": "applied",
                        "applied_action": {"action": "t019_smoke_test"},
                        "outcome_summary": {"status": "success"},
                    }
                },
            )

            if "error" in record_result:
                raise SystemExit(f"record_policy_application failed: {record_result}")

            application_id = record_result["application_id"]
            print(f"   ✓ application_id={application_id}")

            # 5. List policy applications via MCP
            print(f"5. Listing policy applications...")
            list_result = mcp_call(
                mcp_url,
                api_token,
                "list_policy_applications",
                {
                    "policy_id": policy_id,
                    "limit": 10,
                    "offset": 0,
                },
            )

            if "error" in list_result:
                raise SystemExit(f"list_policy_applications failed: {list_result}")

            apps = list_result.get("items", [])
            if not any(a["application_id"] == application_id for a in apps):
                raise SystemExit(f"Recorded application not in list result: {list_result}")

            print(f"   ✓ found {len(apps)} applications, including recorded one")

        finally:
            # 6. Cleanup
            print(f"6. Cleaning up test data...")
            if policy_id_holder.get("policy_id"):
                await conn.execute(
                    "DELETE FROM hermes.policy_applications WHERE policy_id = $1::uuid",
                    policy_id_holder["policy_id"],
                )
                await conn.execute(
                    "DELETE FROM hermes.agent_policies WHERE policy_id = $1::uuid",
                    policy_id_holder["policy_id"],
                )
            await conn.execute(
                "DELETE FROM hermes.learning_candidates WHERE candidate_id = $1",
                candidate_id,
            )
            await conn.execute(
                "DELETE FROM hermes.wechat_retrospective_reports WHERE report_id = $1",
                report_id,
            )
            await conn.close()
            print("   ✓ cleanup complete")

    asyncio.run(run_smoke())
    print("\n✅ T019 deployed live smoke PASSED")


if __name__ == "__main__":
    main()
