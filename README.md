# Pattern Mirror

An AI-powered personal reflection tool. POC built against the Claude API to surface recurring psychological and behavioural patterns from structured self-reflection.

Secondary purpose: hands-on vehicle for the Claude Certified Architect (CCA-F) exam preparation — every exam domain gets demonstrated here in practice.

## Status

Week 1 — Orientation. Not shippable. Not yet functional.

## Stack (planned)

- Python 3.11+
- `anthropic` SDK (Claude Sonnet 4.6)
- Streamlit (Week 3+)
- chromadb + sentence-transformers (Week 5+, RAG)
- Custom MCP server (Week 7+)

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic python-dotenv
cp .env.example .env
# Put your API key into .env
python main.py
```

## Project Layout

```
pattern-mirror/
├── main.py           # entrypoint — currently a smoke-test API call
├── .env.example      # template; real secrets live in .env (gitignored)
├── .gitignore
└── README.md
```

More structure arrives as sprints progress. See `../Antarjyoti/Arka_12_Week_CCA_Preparation_Plan.md`.

## License

Private. Not for redistribution.
