import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    timeout=30,
    max_retries=3,
)