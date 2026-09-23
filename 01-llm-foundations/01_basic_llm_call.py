from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
sys.path.insert(0, str(root))

from openai import OpenAI
import config


PROMPT = "Reply with one short sentence: what is an LLM"
print("prompt", PROMPT)

base = config.OLLAMA_BASE_URL.rstrip("/")
if not base.endswith("/v1"):
    base = base + "/v1"
client = OpenAI(base_url=base, api_key="ollama")
raw = client.chat.completions.create(
    model=config.CHAT_MODEL,
    messages=[{"role": "user", "content": PROMPT}],
    temperature=0,
    max_tokens=256,
    extra_body={"think": False},
)
msg = raw.choices[0].message
print(raw.choices)
print("Ollama base URL", base)
print("raw_model", raw.model)
print("raw_text", msg.content)
print("raw_usage", raw.usage.model_dump() if raw.usage else None)
print("raw_finish", raw.choices[0].finish_reason)