"""
Pattern Mirror — entrypoint.

Week 1 stub: smoke-test a single Messages API call.
Expand in Week 2: collect reflection answers from the user, pass to Claude,
print the response. Keep it ugly at first — ship before you polish.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing ANTHROPIC_API_KEY. Copy .env.example to .env and fill it in."
        )

    client = Anthropic(api_key=api_key)

    # First call — prove the pipe works end-to-end.
    response = client.messages.create(
        model="claude-sonnet-4-0",  # update to the exact model string you want to use
        max_tokens=300,
        messages=[
            {"role": "user", "content": "What are you designed to help with"}
        ],
    )

    print(response.content[0].text)


if __name__ == "__main__":
    main()
