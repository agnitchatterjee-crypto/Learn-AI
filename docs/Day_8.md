# Day 8 — Context, Tokenization, API Economics & First Real-World LLM Application

## Overview

Day 8 was the point where I moved from understanding LLM concepts to building a small, practical LLM application.

The main topics covered were:

- Context windows
- Conversation state and the illusion of model memory
- API usage and token economics
- `tiktoken`
- Model-specific tokenization
- Claude token counting
- Building a real-world application using an LLM
- Passing a document as context to an LLM
- Context engineering
- The relationship between context management and RAG

---

## 1. Context Window

The **context window** is the maximum amount of context, measured in tokens, that a model can consider when processing a request and generating its response.

It is not limited to the latest user message.

A request can contain:

- System instructions
- Previous conversation history
- The latest user message
- Previous assistant responses
- Retrieved documents
- Tool definitions and results
- Other supplied context

A useful mental model is:

```text
                 CONTEXT WINDOW
┌──────────────────────────────────────────────┐
│ System instructions                         │
│ Conversation history                        │
│ Latest user message                         │
│ Retrieved documents                         │
│ Tool definitions / results                   │
│ Other supplied context                      │
│                                              │
│                  ↓                           │
│                MODEL                         │
│                  ↓                           │
│             Generated output                │
└──────────────────────────────────────────────┘
```

### Important distinction

The context window should not simply be thought of as "conversation length".

It is better understood as **the context supplied to the model for a particular request**.

---

## 2. LLM Memory vs Application State

One of the most important experiments today was understanding that an API-based LLM does not automatically remember previous independent API calls.

For example, the first request contained:

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hi! I'm Ed!"}
]
```

A later request containing only:

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "What's my name?"}
]
```

does not necessarily know that the earlier request contained `"Hi! I'm Ed!"`.

The application needs to preserve and resend the relevant conversation history.

This means:

```text
LLM
 ↓
Does not inherently maintain application conversation state
```

while:

```text
Application
 ↓
Maintains conversation history
 ↓
Supplies relevant history to LLM
```

This creates the appearance of conversational memory.

### Important distinction

There are three concepts to keep separate:

**Model memory**

Information encoded in the model's learned parameters.

**Context**

Information supplied to the model for the current request.

**Application memory**

Information persisted outside the model and retrieved when required.

This distinction becomes particularly important for RAG and agent architectures.

---

## 3. Conversation State Experiment

The experiment was extended by retaining the previous assistant response and appending the next user message:

```python
messages.append({
    "role": "assistant",
    "content": response.choices[0].message.content
})

messages.append({
    "role": "user",
    "content": "What's my name?"
})
```

The entire message history was then sent with the next API request.

This demonstrated the core pattern:

```text
User message
     ↓
Application stores conversation
     ↓
Previous messages + new message
     ↓
LLM API
     ↓
Response
     ↓
Application stores response
```

The application is responsible for managing state.

---

## 4. Prompt Caching

Prompt caching should be thought of as an optimization mechanism rather than additional conversational memory.

Cached tokens are still part of the supplied context, but caching does not create semantic memory by itself.

Conceptually:

```text
System prompt
+
Conversation history
+
New user message
        ↓
Tokenized input
        ↓
Some input may be cached
        ↓
Model
```

Caching can therefore affect performance and cost, but it should not be confused with persistent application memory.

---

## 5. API Economics

A major topic was understanding the difference between using a chat product and using an API.

### Chat interface

Typically operates through a subscription/plan model with usage limits or quotas.

### API

Typically follows usage-based pricing where costs can depend on:

- Input tokens
- Cached input tokens
- Output tokens
- Reasoning tokens for applicable models
- Other metered services where applicable

A simplified model is:

```text
API cost
   ≈
Input tokens
+
Cached input tokens
+
Output tokens
+
Applicable additional usage
```

### Reasoning tokens

Reasoning models may use internal reasoning tokens before producing the visible response.

These tokens may not appear in the final response but can contribute to usage and cost according to the model's pricing rules.

---

## 6. `tiktoken`

`tiktoken` is OpenAI's tokenizer library.

It converts text into token IDs that can be processed by compatible OpenAI models and can also decode token IDs back into text.

Example:

```python
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

text = "Hi my name is Ed and I like banoffee pie"

tokens = enc.encode(text)

print(tokens)
```

The token IDs are integers representing entries in the tokenizer vocabulary.

Tokenization is important because:

- Context windows are measured in tokens
- API usage is measured in tokens
- API cost can depend on token counts
- Prompt length needs to be managed
- RAG chunking needs to consider token limits

---

## 7. `get_encoding()` vs `encoding_for_model()`

Two approaches were explored.

### `get_encoding()`

```python
enc = tiktoken.get_encoding("cl100k_base")
```

This explicitly requests a particular tokenizer encoding.

Conceptually:

```text
get_encoding()
    ↓
"I want this exact encoding."
```

### `encoding_for_model()`

```python
encoding = tiktoken.encoding_for_model("gpt-4.1-mini")
```

This asks `tiktoken` to determine the encoding associated with a particular model.

Conceptually:

```text
encoding_for_model()
        ↓
"Give me the encoding associated
 with this model."
```

The second approach is generally more convenient when the goal is model-specific token counting.

---

## 8. Token Counts vs Complete API Requests

A token count generated by a tokenizer should not automatically be assumed to represent the complete token count of every API request.

An actual request can contain additional structures such as:

- Roles
- Message structure
- Tool definitions
- JSON schemas
- Files
- Images
- Other request-specific information

Therefore:

```text
Plain text token count
        ≠
Always the complete API request token count
```

This distinction matters when building production applications where accurate cost and context management are important.

---

## 9. Claude Tokenization

A key lesson was that OpenAI's `tiktoken` should not be treated as the authoritative tokenizer for Claude.

Different model providers can use different tokenization mechanisms.

The general architecture is:

```text
OpenAI model
    ↓
Provider/model-specific tokenizer

Claude model
    ↓
Provider/model-specific tokenizer

Other provider
    ↓
Provider/model-specific tokenizer
```

For Claude-specific token estimation, the provider's own token-counting mechanism or API usage information should be used rather than assuming OpenAI's tokenizer produces the same count.

The important principle is:

> Tokenization is model/provider specific.

---

# 10. First Real-World LLM Application

The most important practical milestone of Day 8 was building a real application.

The application takes my CV in `.docx` format and asks an LLM to generate a one-year career development plan.

### Application flow

```text
Resume (.docx)
      ↓
python-docx
      ↓
Extract resume text
      ↓
Construct prompt
      ↓
Add career objectives + requirements
      ↓
OpenAI API
      ↓
GPT model
      ↓
Career plan
      ↓
Markdown output
```

This was implemented using Python.

---

## 11. Document Ingestion

The first step was extracting the text from the CV.

The application uses `python-docx` to read the document:

```python
from docx import Document

def extract_text(path):
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]

    for table in doc.tables:
        for row in table.rows:
            parts.append("	".join(cell.text for cell in row.cells))

    return "
".join(parts)
```

This is effectively a small document-ingestion pipeline.

---

## 12. Context Engineering

The extracted CV text was then included in the prompt along with explicit instructions.

The prompt requested:

- A one-year career plan
- Consideration of current skills and experience
- Industry trends
- Month-by-month actions
- Learning resources
- Networking strategies
- Certifications
- Progress measurement
- A business-like Markdown output

The important concept is:

> The LLM is not magically aware of my CV. I explicitly supplied my CV as context.

This is **context engineering**.

---

## 13. LLM Inference

The application then sent the constructed context to the OpenAI API:

```python
response = openai.chat.completions.create(
    model="gpt-4.1-mini",
    messages=messages
)
```

The model generated the career plan based on the instructions and CV context.

---

## 14. Output Generation

The generated response was written directly to a Markdown file:

```python
with open("output.md", "w", encoding="utf-8") as file:
    file.write(response.choices[0].message.content)
```

This turns the LLM response into a reusable business artifact rather than leaving it as a chat response.

---

# 15. The Bigger Architecture

This small application demonstrated a general LLM application architecture:

```text
INGEST
   ↓
TRANSFORM
   ↓
CONTEXT ENGINEERING
   ↓
LLM INFERENCE
   ↓
OUTPUT / ARTIFACT
```

This is an important realization for a data engineer:

> The LLM is only one component of the overall application.

The surrounding application is responsible for:

- Data ingestion
- State management
- Context construction
- Retrieval
- Tool integration
- Output handling
- Security
- Observability
- Cost management

---

# 16. LLM ≠ Chat Application

A key architectural lesson from Day 8:

```text
LLM
=
Inference engine
```

An AI application adds capabilities around the model:

```text
                  AI APPLICATION
┌─────────────────────────────────────────┐
│                                         │
│  State / Memory                         │
│  Retrieval                              │
│  Tools                                  │
│  Orchestration                          │
│  Context Management                     │
│  Security                               │
│  Observability                          │
│  Cost Controls                          │
│                                         │
│              ↓                          │
│             LLM                         │
│                                         │
└─────────────────────────────────────────┘
```

This distinction is critical when moving toward RAG and agent architectures.

---

# 17. Limitations of the First Application

The application asked the LLM to consider:

> "latest trends in the industry"

However, the application did not actually provide live industry data or external research.

The application supplied:

```text
CV
+
instructions
```

Therefore:

> Asking an LLM for current information does not automatically make the information current.

For claims involving:

- Current job openings
- Current salary information
- Latest industry trends
- Current courses
- Current certifications
- Current market conditions

external retrieval or verification is required.

---

# 18. Hallucination / Verification

Another important lesson:

```text
LLM output
    ≠
Ground truth
```

An LLM can produce plausible-looking recommendations or facts that require verification.

A production-oriented architecture therefore moves toward:

```text
Generate
   ↓
Retrieve / Verify
   ↓
Evaluate
   ↓
Present
```

rather than:

```text
Generate
   ↓
Trust everything
```

This will become increasingly important as applications become more autonomous.

---

# 19. Connection to RAG

The first application is effectively:

```text
CV → LLM → Career Plan
```

The next evolution could be:

```text
CV
 │
 ▼
Extract profile
 │
 ├──────────────┐
 │              │
 ▼              ▼
Job postings   Industry information
 │              │
 └──────┬───────┘
        ▼
    Retrieval
        ↓
 Context Builder
        ↓
       LLM
        ↓
 Career Plan
```

This is where **Retrieval-Augmented Generation (RAG)** naturally enters.

The core idea is:

> Instead of putting every available piece of information into the context window, retrieve only the information relevant to the current question.

---

# 20. Context Management and Data Engineering

There is a strong connection between LLM architecture and traditional data engineering.

For example:

```text
Data Engineering
----------------
Partition
Filter
Prune
Cache
Transform
Move only required data
```

maps conceptually to:

```text
LLM Engineering
----------------
Chunk
Retrieve
Filter
Cache
Construct context
Send only relevant context
```

This leads to an important principle:

> **RAG retrieval is fundamentally a context-selection problem.**

Instead of:

```text
Entire knowledge base
        ↓
      LLM
```

we want:

```text
Question
   ↓
Retrieve relevant information
   ↓
Small, high-quality context
   ↓
LLM
```

This helps with:

- Context-window limitations
- Cost
- Latency
- Relevance
- Grounding

---

# 21. Evolution of the Application

The learning path is now becoming:

```text
Version 1
CV → LLM → Career Plan
```

Then:

```text
Version 2
CV
 +
Job postings
 +
Industry information
        ↓
     Retrieval
        ↓
       LLM
        ↓
 Career Strategy
```

And eventually:

```text
Version 3 — Agent

                    ┌── Job search
                    ├── Resume analysis
User → Career Agent ├── Salary research
                    ├── Skill-gap analysis
                    ├── Course search
                    └── Progress tracking
                             │
                             ▼
                            LLM
```

This provides a natural progression:

```text
LLM
 ↓
RAG
 ↓
Tools
 ↓
Agents
```

---

# 22. Key Takeaways

### Conceptual

- Context windows are measured in tokens.
- Context is broader than just the latest user message.
- Independent API requests do not automatically share conversation state.
- Application code can maintain conversation history.
- Model memory, context and application memory are different concepts.
- Tokenization is provider/model specific.
- API costs are closely connected to token usage.
- Reasoning tokens can contribute to usage and cost.
- Prompt caching is an optimization mechanism, not persistent memory.

### Engineering

- An LLM is only one component of an AI application.
- Context engineering is a core AI engineering skill.
- Document ingestion is a natural precursor to RAG.
- Token management becomes increasingly important as context grows.
- LLM output should not automatically be treated as ground truth.
- External retrieval and verification are required for current or authoritative information.
- RAG can be viewed as intelligent context selection.

### Personal milestone

I built my first practical LLM application:

```text
Resume
  ↓
Document extraction
  ↓
Context engineering
  ↓
LLM
  ↓
Career plan
  ↓
Markdown artifact
```

This was the first point where I moved beyond simply learning about LLMs and started building an actual LLM-powered application.

---

# Day 8 — What I Should Be Able to Explain

By the end of Day 8, I should be able to explain:

1. What a context window is.
2. Why an API-based LLM does not automatically remember previous requests.
3. How an application maintains conversational state.
4. The difference between model memory, context and application memory.
5. What tokens are and why they matter for cost and context.
6. What `tiktoken` does.
7. The difference between `get_encoding()` and `encoding_for_model()`.
8. Why tokenization should be treated as model/provider specific.
9. Why LLM output is not automatically ground truth.
10. How my first real-world LLM application works.
11. What context engineering means.
12. Why the application I built is a natural stepping stone toward RAG.
13. Why an LLM should be viewed as one component inside a larger AI application architecture.

---

# Day 8 Reflection

The biggest shift in my understanding today was:

> **An LLM is not the application.**

The model performs inference, but the application provides the context, state, data, retrieval, tools and orchestration required to make the model useful.

My first CV-to-career-plan application made this tangible.

The next major step is to understand how to provide an LLM with **relevant external knowledge at scale** without simply stuffing everything into its context window.

That leads directly into:

**Embeddings → Vector Search → RAG → Tool Calling → Agents**
