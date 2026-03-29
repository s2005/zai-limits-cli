from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
import os

API_URL = "https://api.z.ai/api/monitor/usage/quota/limit"
TIMEOUT_SECONDS = 10
console = Console()


@dataclass
class LimitItem:
    name: str
    used_percent: float
    remaining_percent: float
    reset_at_raw: str | None
    reset_at_local: str


@dataclass
class LimitsResult:
    plan: str
    limits: list[LimitItem]


def build_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(description="Inspect z.ai code plan limits")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    return parser


def format_limit_name(limit_type: str | None, number: int | None) -> str:
    """Map z.ai limit types to user-facing names."""
    if limit_type == "TOKENS_LIMIT":
        return f"{number} Hours Quota"
    if limit_type == "TIME_LIMIT":
        return "Total Monthly Web Search / Reader / Zread Quota"
    return limit_type or "Unknown"


def format_reset_time(value: str | int | None) -> str:
    """Convert an ISO timestamp or Unix epoch into local time when possible."""
    if not value:
        return "-"
    try:
        if isinstance(value, int):
            dt = datetime.fromtimestamp(value / 1000, tz=datetime.now().astimezone().tzinfo)
        else:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        local = dt.astimezone()
        offset = local.utcoffset()
        if offset is None:
            return local.strftime("%Y-%m-%d %H:%M:%S")
        offset_hours = int(offset.total_seconds() // 3600)
        sign = "+" if offset_hours >= 0 else ""
        return local.strftime(f"%Y-%m-%d %H:%M:%S GMT{sign}{offset_hours}")
    except (ValueError, OSError, OverflowError):
        return str(value)


def fetch_limits(api_key: str) -> dict[str, Any]:
    """Fetch raw limits payload from z.ai."""
    response = requests.get(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def parse_limits(data: dict[str, Any]) -> LimitsResult:
    """Parse z.ai API response into a stable internal representation."""
    if not data.get("success") or data.get("code") != 200:
        message = data.get("msg") or "Unknown API error"
        raise RuntimeError(f"API error: {message}")

    payload = data.get("data", {})
    plan_name = payload.get("planName") or payload.get("plan") or "Unknown"
    limits = payload.get("limits", [])

    items: list[LimitItem] = []
    for limit in limits:
        used_percent = float(limit.get("percentage", 0))
        items.append(
            LimitItem(
                name=format_limit_name(limit.get("type"), limit.get("number")),
                used_percent=used_percent,
                remaining_percent=max(0.0, 100.0 - used_percent),
                reset_at_raw=limit.get("nextResetTime"),
                reset_at_local=format_reset_time(limit.get("nextResetTime")),
            )
        )

    return LimitsResult(plan=plan_name, limits=items)


def render_table(result: LimitsResult) -> None:
    """Render limits using Rich table output."""
    console.print(f"[bold]Plan:[/bold] {result.plan}\n")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Limit")
    table.add_column("Used", justify="right")
    table.add_column("Remaining", justify="right")
    table.add_column("Reset")

    for item in result.limits:
        table.add_row(
            item.name,
            f"{item.used_percent:.1f}%",
            f"{item.remaining_percent:.1f}%",
            item.reset_at_local,
        )

    console.print(table)


def main() -> int:
    """CLI entry point."""
    load_dotenv()
    args = build_parser().parse_args()

    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("ERROR: ZAI_API_KEY is not set. Put it into .env file.", file=sys.stderr)
        return 1

    try:
        raw = fetch_limits(api_key)
        result = parse_limits(raw)
    except requests.HTTPError as exc:
        print(f"HTTP error: {exc}", file=sys.stderr)
        return 2
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 4

    if args.json:
        payload = {
            "plan": result.plan,
            "limits": [asdict(item) for item in result.limits],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        render_table(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
