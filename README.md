# zai-limits-cli

Simple Python CLI to inspect z.ai code plan limits.

## Features

- Loads `ZAI_API_KEY` from `.env`
- Normal mode renders a Rich table
- `--json` prints raw structured output
- Installable as a CLI via `pyproject.toml`

## Installation

```bash
python -m venv .venv
source .venv/bin/activate

# For GitBash use -
# source .venv/Scripts/activate

pip install -e .
```

## Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
ZAI_API_KEY=your_api_key_here
```

## Usage

```bash
zai-limits
zai-limits --json
```

## Notes

The CLI calls the z.ai endpoint used by OpenClaw:

- `https://api.z.ai/api/monitor/usage/quota/limit`
