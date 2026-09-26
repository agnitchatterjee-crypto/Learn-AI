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

text = "I am learning about LLMs"

tiktoken_short = len(enc.encode(text))
ids = enc.encode(text)
for i in ids:
    print(i, '->', repr(enc.decode([i])))