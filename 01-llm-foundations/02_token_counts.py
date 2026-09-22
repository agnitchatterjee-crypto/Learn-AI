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