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

text = "Hi my name is Ed and I like banoffee pie"

tiktoken_short = len(enc.encode(text))
ids = enc.encode(text)
for i in ids:
    print(i, '->', repr(enc.decode([i])))

print("-"*1000)

encoding = tiktoken.encoding_for_model("gpt-4.1-mini")

tokens = encoding.encode("Hi my name is Ed and I like banoffee pie")
print("Tokens:", tokens)

for token_id in tokens:
    token_text = encoding.decode([token_id])
    print(f"{token_id} = {token_text}")