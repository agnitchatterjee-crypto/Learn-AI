# Day 3 — LLM Fundamentals, Context, Generation & Token Economics

## Day 3 Objectives

- Revise Day 1 and Day 2 concepts.
- Strengthen the mental model of how an LLM works.
- Understand context windows and the distinction between context and memory.
- Understand how an LLM generates tokens and knows when to stop.
- Connect token counts to model limits, compute, latency, and cost.
- Extend the token-counting Python exercise.

---

# 1. Day 1 & Day 2 Revision

The core concepts covered so far:

- What is an LLM?
- What is a prompt?
- What is a token?
- Tokenization
- Token IDs
- Context
- Context window
- LLM APIs
- Ollama
- OpenAI-compatible APIs
- `base_url`
- `messages`
- `temperature`
- `max_tokens`
- Prompt tokens
- Completion/output tokens
- `finish_reason`
- `cl100k_base`
- Encoding and decoding

---

# 2. What Is an LLM?

A useful mental model is:

> An LLM is fundamentally a next-token prediction system.

It is not a traditional database or deterministic knowledge store.

At a high level:

```text
Input text
   ↓
Tokenization
   ↓
Token IDs
   ↓
Context
   ↓
Transformer
   ↓
Probability distribution
   ↓
Next-token selection
   ↓
Generated token
   ↓
Append token to context
   ↓
Repeat
   ↓
Stop condition
   ↓
Final response
```

The important idea is:

> The training objective is next-token prediction, but learning to predict tokens across huge amounts of data results in the model learning patterns related to language, facts, reasoning, style, code, and other capabilities.

---

# 3. More Detailed LLM Inference Flow

## Step 1 — Tokenization

Text is broken into tokens.

Tokens are often sub-word pieces rather than complete words.

For example, conceptually:

```text
"unbelievable"
      ↓
"un" + "believ" + "able"
```

The exact split depends on the tokenizer.

---

## Step 2 — Token IDs

Each token is mapped to an integer ID.

Conceptually:

```text
Token       Token ID

"Hello"     9906
" world"    1917
```

Therefore:

```text
"Hello world"
      ↓
[9906, 1917]
```

### Important distinction

A token ID is **not an embedding/vector**.

```text
Token ID:
9906
```

is fundamentally different from:

```text
Embedding:
[0.023, -0.182, 0.731, ...]
```

Token IDs identify tokens.

Embeddings represent information numerically in a high-dimensional vector space.

---

# 4. Embedding

After tokenization, token IDs are mapped to vectors through the model's embedding mechanism.

Conceptually:

```text
Token
  ↓
Token ID
  ↓
Embedding lookup
  ↓
High-dimensional vector
```

This is where tokens become numerical representations that can be processed by the neural network.

---

# 5. Context Window

The context window represents the tokens available to the model during a particular inference request.

It can contain:

- System instructions
- User messages
- Conversation history
- Retrieved documents
- Tool results
- Previously generated tokens

Conceptually:

```text
Context Window
┌───────────────────────────────┐
│ System instructions           │
│ User prompt                   │
│ Conversation history          │
│ Retrieved context             │
│ Generated tokens              │
└───────────────────────────────┘
```

The model can only attend to information that is available within its context.

---

# 6. Context Is Not Persistent Memory

This is an important distinction.

An LLM has different concepts that can easily be confused:

```text
Model weights
    ≠
Conversation memory
    ≠
Context window
```

## Model weights

Weights contain patterns learned during training.

They are not modified simply because you have a conversation with the model.

## Context window

The context is the information supplied to the model for the current inference.

It is not persistent memory.

A useful mental model is:

> The model does not inherently remember the conversation; the conversation is provided back to the model as context.

---

# 7. Autoregressive Generation

The model generates output one token at a time.

For example:

```text
Input:
"What is a token?"

        ↓

Predict token 1
        ↓
Predict token 2
        ↓
Predict token 3
        ↓
...
        ↓
Predict final token
        ↓
Stop
```

At each step, the model produces a probability distribution over possible next tokens.

Conceptually:

```text
Context
   ↓
Transformer
   ↓
Probability distribution

"token"       0.30
"is"          0.15
"means"       0.08
"..."         ...
"<EOS>"       0.02
```

A decoding strategy determines which token is selected.

---

# 8. Temperature

`temperature` influences how much randomness is introduced during token selection.

Conceptually:

```text
Lower temperature
      ↓
More predictable / deterministic

Higher temperature
      ↓
More variability
```

For example:

```python
temperature=0
```

is commonly used when you want highly repeatable behavior.

It is better to think of temperature as influencing the probability distribution used for sampling rather than simply saying "temperature adds randomness."

---

# 9. How Does the Model Know When to Stop?

Stopping is part of the generation process.

One mechanism is a special token such as:

```text
<EOS>
```

meaning:

> End Of Sequence

Conceptually:

```text
Token → Token → Token → Token → EOS
                              ↓
                            STOP
```

The model can learn from training data that certain contexts are associated with an appropriate ending.

However, generation can stop for several reasons.

## 9.1 EOS / end token

The model generates an end-of-sequence or relevant end-of-turn token.

```text
Generated tokens → EOS → STOP
```

## 9.2 Maximum output token limit

For example:

```python
max_tokens=256
```

If the model reaches the configured generation limit, the serving system can stop generation.

## 9.3 Stop sequence

An application can specify a sequence that should terminate generation.

For example:

```text
stop = ["</json>"]
```

When the sequence appears, the serving layer can stop generation.

---

# 10. Why Do More Tokens Cost More?

There are two different sides to think about:

## Input tokens

More input tokens mean more context for the model to process.

```text
More input tokens
        ↓
More context processing
        ↓
More compute
```

## Output tokens

Output is generated autoregressively.

```text
Generate token 1
      ↓
Generate token 2
      ↓
Generate token 3
      ↓
...
Generate token N
```

Therefore:

> More output tokens generally mean more generation steps, more computation, more latency, and potentially more cost.

A simplified mental model:

```text
Input tokens
      ↓
Context processing

Output tokens
      ↓
Autoregressive generation
      ↓
More generation work
```

Modern inference systems use optimizations such as KV caching, so the exact compute characteristics are more complicated than simply saying "the model processes the entire context from scratch for every token."

---

# 11. Token Economics

Token counts matter in production LLM engineering.

They influence:

- API cost
- Latency
- Context-window utilization
- Throughput
- Memory requirements
- RAG design
- Prompt design
- Output limits

For example:

```text
User question
      +
System instructions
      +
Conversation history
      +
Retrieved documents
      +
Tool results
      ↓
Large prompt
      ↓
Large token count
      ↓
Higher input-token consumption
```

This is why production LLM systems need token-aware design.

---

# 12. `01_ollama_chat.py` Concepts

## `PROMPT`

A prompt is the input/instruction given to the model.

In a simple application:

```python
PROMPT = "Explain what an LLM is."
```

It represents the user's request.

More broadly, a prompt can contain instructions, context, examples, questions, or structured information.

---

## `OpenAI()`

Using:

```python
OpenAI()
```

does not necessarily mean an OpenAI model is being used.

Ollama exposes an OpenAI-compatible API.

The architecture can therefore be:

```text
Python Application
       ↓
OpenAI Python Client
       ↓
base_url
       ↓
Ollama API
       ↓
Qwen3
```

The OpenAI client is being used as the API interface.

---

## `base_url`

`base_url` tells the client where the API endpoint is located.

For a local Ollama setup, this is typically based around:

```text
http://localhost:11434/v1
```

Therefore:

```text
OpenAI client
      ↓
base_url
      ↓
Local Ollama endpoint
```

---

## `messages=[...]`

`messages` represents the structured conversation being sent to the model.

Example:

```python
messages=[
    {"role": "user", "content": PROMPT}
]
```

It can also contain multiple roles:

```python
messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain LLMs."}
]
```

Therefore:

> `messages` = structured representation of the conversation/context sent to the model.

---

## `max_tokens`

Controls the maximum number of tokens that may be generated in the output.

It is not simply:

```text
input + output <= max_tokens
```

It primarily limits the generated completion.

---

## `raw.choices[0].message.content`

The API response can contain multiple layers.

Conceptually:

```text
raw
 ├── choices
 │    └── [0]
 │         └── message
 │              └── content
 └── usage
      ├── prompt_tokens
      ├── completion_tokens
      └── total_tokens
```

Therefore:

```python
raw.choices[0].message.content
```

means:

> Get the first generated choice and extract the actual message content.

---

## `prompt_tokens`

Number of tokens in the input/context supplied to the model.

```text
Prompt → Tokenizer → Prompt tokens
```

---

## `completion_tokens`

Number of tokens generated by the model.

```text
LLM → Generated tokens → Completion tokens
```

Often:

```text
total_tokens
=
prompt_tokens
+
completion_tokens
```

---

## `finish_reason`

Reports why generation stopped.

For example:

```text
finish_reason = "stop"
```

generally indicates normal termination.

Another possible reason can be a length limit, depending on the API/model.

---

# 13. `02_token_counts.py` Concepts

## `cl100k_base`

`cl100k_base` is a tokenizer encoding associated with OpenAI's tokenizer ecosystem.

It defines how text is broken into tokens and mapped to integer token IDs.

It is **not vectorization**.

Think:

```text
Text
 ↓
cl100k_base tokenizer
 ↓
Tokens
 ↓
Token IDs
```

---

## `enc.encode(SHORT)`

For example:

```python
tokens = enc.encode(SHORT)
```

returns a list of integer token IDs according to that encoding.

Conceptually:

```text
"Hello world"
       ↓
[9906, 1917]
```

The exact IDs depend on the tokenizer.

---

## Why integers?

Integers act as IDs/indexes into the tokenizer vocabulary.

They are not embeddings.

```text
Token ID
   ↓
Integer identifier
```

versus:

```text
Embedding
   ↓
High-dimensional numerical vector
```

---

## `enc.decode(...)`

Decoding converts token IDs back into text.

```text
Text
 ↓
encode()
 ↓
Token IDs
 ↓
decode()
 ↓
Text
```

Conceptually:

```python
ids = enc.encode("Hello world")
text = enc.decode(ids)
```

---

# 14. Why Can One Word Become Multiple Tokens?

Tokenizers often use subword tokenization.

Therefore:

```text
1 word
  ≠
1 token
```

A word may be split into several token pieces, especially when it is long, uncommon, or contains unusual patterns.

Also:

```text
1 token
  ≠
1 word
```

A token can contain spaces, punctuation, or partial words.

---

# 15. Why Did the Large Text Produce 12,322 Tokens?

Because the tokenizer processed the entire input and represented it using 12,322 token IDs under the selected encoding.

The general relationship is:

```text
More text
   ↓
More tokens
   ↓
More context consumption
```

The exact number depends on the tokenizer and the actual text.

---

# 16. Is `cl100k_base` Necessarily Qwen3's Tokenizer?

No.

This is a critical distinction.

If you run:

```python
enc = tiktoken.get_encoding("cl100k_base")
tokens = enc.encode(text)
```

you are asking:

> How many tokens does this text represent under the `cl100k_base` tokenizer?

You are **not necessarily measuring the number of tokens that Qwen3 itself will use**.

Different models can have different tokenizers.

Therefore:

```text
cl100k_base token count
        ≠ necessarily
Qwen3 token count
```

For accurate model-specific token counting, use the tokenizer associated with the model you are actually deploying.

---

# 17. Key Distinction: Token IDs vs Embeddings

This is one of the most important corrections from Day 2/3.

### Tokenization

```text
Text
 ↓
Tokens
 ↓
Integer token IDs
```

Example:

```text
"Hello world"
      ↓
[9906, 1917]
```

### Embedding

```text
Text / Token representation
       ↓
Embedding model
       ↓
Vector
```

Example:

```text
[0.023, -0.182, 0.731, ...]
```

Therefore:

> Token IDs are identifiers. Embeddings are vectors representing learned numerical relationships.

Do not use "vectorization" when describing tokenizer output.

---

# 18. Day 3 Core Mental Model

The most important model to retain:

```text
                INPUT
                  ↓
              Tokenizer
                  ↓
             Token IDs
                  ↓
              Embeddings
                  ↓
               Context
                  ↓
             Transformer
                  ↓
       Probability distribution
                  ↓
          Select next token
                  ↓
          Append to context
                  ↓
               Repeat
                  ↓
           EOS / max limit /
           stop sequence
                  ↓
               OUTPUT
```

---

# 19. The Three Concepts to Keep Separate

### 1. Token

A piece of text.

```text
"hello"
```

### 2. Token ID

An integer identifying that token in a particular tokenizer vocabulary.

```text
15339
```

### 3. Embedding

A high-dimensional vector representation.

```text
[0.12, -0.42, 0.77, ...]
```

Mental model:

```text
Text
 ↓
Tokenization
 ↓
Token IDs
 ↓
Model / embedding mechanism
 ↓
Vectors
```

---

# 20. Day 3 Takeaway

The most important sentence from Day 3:

> An LLM takes a sequence of tokens as context, uses its learned parameters to produce a probability distribution for the next token, selects a token, appends it to the sequence, and repeats until generation stops.

And the second key distinction:

> Token IDs are not embeddings, and context is not persistent memory.

---

# Day 3 Status

- [x] Revised Day 1
- [x] Revised Day 2
- [x] Extended `02_token_counts.py`
- [x] Understood LLM inference at a high level
- [x] Clarified context vs memory
- [x] Clarified how generation stops
- [x] Connected token counts to cost and compute
- [x] Distinguished token IDs from embeddings
- [x] Understood that tokenizer choice is model-specific

**Day 3 is complete.**
