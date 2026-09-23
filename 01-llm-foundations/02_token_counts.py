import os
from pathlib import Path
import json
import sys
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
sys.path.insert(0, str(root))

import tiktoken

import config

enc = tiktoken.get_encoding("cl100k_base")
print("encoding", "cl100k_base")

SHORT = "Where is order DF-1002?"

KB_FILES = [
    root
    / "dataflow"
    / "knowledge_base"
    / "internal_operations"
    / "support_operations"
    / "customer_support_procedures.markdown",
    root
    / "dataflow"
    / "knowledge_base"
    / "customer_facing"
    / "product_user_guide.markdown",
    root
    / "dataflow"
    / "knowledge_base"
    / "customer_facing"
    / "troubleshooting_guide.txt",
]


def load_stuffed() -> str:
    chunks = [SHORT, "", "Knowledge base dump:"]
    for path in KB_FILES:
        chunks.append("")
        chunks.append("FILE " + path.name)
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


STUFFED = load_stuffed()
tiktoken_short = len(enc.encode(SHORT))
ids = enc.encode(SHORT)
for i in ids:
    print(i, '->', repr(enc.decode([i])))
tiktoken_stuffed = len(enc.encode(STUFFED))
print("tiktoken_short", tiktoken_short)
print("tiktoken_stuffed", tiktoken_stuffed)
print("files", [p.name for p in KB_FILES])
print("-"*500)
print("-"*500)
print("-"*500)
print("-"*500)
print("-"*500)
print("-"*500)
print("-"*500)


def ollama_show(model_id: str) -> dict:
    url = config.OLLAMA_BASE_URL.rstrip("/") + "/api/show"
    body = json.dumps({"name": model_id}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def context_length_from_show(payload: dict) -> int | None:
    info = payload.get("model_info") or {}
    for key, value in info.items():
        if "context_length" in str(key).lower():
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    params = str(payload.get("parameters") or "")
    for line in params.splitlines():
        if "num_ctx" in line.lower():
            bits = line.split()
            for bit in reversed(bits):
                if bit.isdigit():
                    return int(bit)
    return None


def ollama_ps() -> dict | None:
    url = config.OLLAMA_BASE_URL.rstrip("/") + "/api/ps"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


print("OLLAMA Chat Model = " + (os.environ.get("OLLAMA_CHAT_MODEL", "qwen3:8b")))
print("-"*500)
show = ollama_show(config.CHAT_MODEL)
for key, value in show.items():
    print(key, "=", json.dumps(value, indent=2, ensure_ascii=False))
print("-"*500)
card_ctx = context_length_from_show(show)
print("model_card_context_length", card_ctx)
print("model_card_expected", 40960)
print("-"*500)

