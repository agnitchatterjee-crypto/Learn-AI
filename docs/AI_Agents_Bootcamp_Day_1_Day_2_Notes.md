# AI Agents Bootcamp — Day 1 & Day 2 Learning Notes

## Overview

This document captures the learning, setup, experiments, and architectural takeaways from the first two days of the **AI Agents Bootcamp: LangChain, LangGraph, RAG & MCP** course.

The objective is not just to complete the course, but to build a strong mental model of LLM-based systems and connect the concepts to production-grade data and AI architecture.

---

# Day 1 — Environment Setup & Course Orientation

## 1. Course

**Course:** AI Agents Bootcamp: LangChain, LangGraph, RAG & MCP [2026]

The first day was primarily focused on understanding the structure of the course, setting up the local development environment, validating the repository, and getting the local LLM runtime working.

---

## 2. Development Environment Setup

### Python

Installed:

- Python Install Manager 26.3

Created a project-specific virtual environment:

```bash
python -m venv .venv
```

Activated the virtual environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Git / GitHub

Cloned the course repository:

```bash
git clone https://github.com/pragatidev/AIAgentsBootcamp.git
```

This provides the baseline code used throughout the course.

### Ollama

Installed Ollama to enable local LLM inference.

Pulled the Qwen3 8B model:

```bash
ollama pull qwen3:8b
```

This means the initial experiments can be executed locally without immediately depending on a commercial hosted LLM API.

---

## 3. Course Progress

Completed the first four videos of the course.

Ran the setup commands/scripts provided by the course.

### Result

The local environment was successfully validated:

```text
Windows
  |
  +-- Python
  |     |
  |     +-- .venv
  |
  +-- Git
  |     |
  |     +-- AIAgentsBootcamp
  |
  +-- Ollama
        |
        +-- Qwen3 8B
```

Everything required for continuing with the course was working.

---

# Day 1 Key Learning

The most important outcome from Day 1 was not the number of videos completed.

It was establishing a working local AI development environment:

```text
Python
  ↓
Virtual Environment
  ↓
Course Code
  ↓
LangChain / AI Libraries
  ↓
Ollama
  ↓
Qwen3 8B
```

This provides a controlled environment for experimenting with LLMs before introducing external APIs and cloud-based models.

---

# Day 2 — LLM Fundamentals

Day 2 focused on the conceptual foundation required before going deeper into LangChain, LangGraph, RAG, tools, and agents.

The six areas identified for Day 2 were:

1. What is an LLM?
2. Generative AI fundamentals
3. How LLMs work at a high level
4. Tokens
5. Context
6. LLM APIs

The goal was to understand the underlying mechanics before relying heavily on framework abstractions.

---

# 1. What Is an LLM?

A useful mental model is:

> An LLM is fundamentally a next-token prediction system, not a traditional database or deterministic knowledge store.

At a high level:

```text
Input text
   ↓
Tokenization
   ↓
Context
   ↓
Transformer
   ↓
Next-token prediction
   ↓
Generated token
   ↓
Repeat
   ↓
Final response
```

The model generates a response incrementally by predicting what token should come next based on the context available to it.

This is important because an LLM does not operate like:

```text
Question
   ↓
Database lookup
   ↓
Known answer
```

Instead, it performs inference over the supplied context and learned model parameters.

---

# 2. Generative AI Fundamentals

Generative AI refers to systems capable of generating new content based on learned patterns.

LLMs are one category of generative AI.

Models can differ by:

- Size
- Architecture
- Training data
- Context window
- Modality
- Inference characteristics
- Cost
- Latency

A useful distinction is:

```text
Large Language Model
        vs
Small Language Model
        vs
Multimodal Model
```

The important architectural point is that model selection is an engineering decision.

It depends on requirements such as:

- Accuracy
- Latency
- Cost
- Privacy
- Hardware
- Context requirements
- Deployment model
- Data sensitivity

---

# 3. Transformer — High-Level Understanding

The transformer is the underlying architecture behind modern LLMs.

The important conceptual component to understand initially is **attention**.

At a high level, attention allows the model to determine which parts of the input are relevant to each other when generating the next token.

For example:

```text
"The customer opened a new account because he needed a loan."
```

The model needs to understand relationships between words and concepts rather than simply treating the text as an unstructured sequence.

For Day 2, the goal is conceptual understanding rather than implementing a transformer from scratch.

---

# 4. Tokens

One of the most important Day 2 concepts was **tokenization**.

A token is not necessarily:

- A character
- A word
- A sentence

A word may become one token or several tokens depending on the tokenizer.

Therefore:

```text
characters ≠ words ≠ tokens
```

Token count matters because it influences:

- Context-window utilization
- API cost
- Potential latency
- Amount of information that can be supplied to the model

---

# 5. Tokens and Real-World Cost

A token count can be mapped to real-world API cost when the pricing model is known.

The basic calculation is:

```text
Input cost =
(input tokens / 1,000,000) × input price per 1M tokens

Output cost =
(output tokens / 1,000,000) × output price per 1M tokens

Total cost =
input cost + output cost
```

### Example

Suppose an API request uses:

```text
Input  = 20,000 tokens
Output = 2,000 tokens
```

And, hypothetically:

```text
Input  = $2 / 1M tokens
Output = $10 / 1M tokens
```

Then:

```text
Input cost
= 20,000 / 1,000,000 × $2
= $0.04

Output cost
= 2,000 / 1,000,000 × $10
= $0.02

Total
= $0.06
```

The exact pricing must always be checked against the current provider/model pricing.

---

# 6. Tokenizer vs Provider

A critical learning point:

> A token count from one tokenizer should not automatically be assumed to be the exact token count used by another model/provider.

For example:

```text
tiktoken
   ↓
OpenAI tokenizer family
```

does not imply:

```text
tiktoken count == Claude token count
```

Different providers/models can tokenize the same text differently.

Therefore there is a distinction between:

### Estimated token count

Using a tokenizer such as `tiktoken` as a proxy.

### Provider-specific token count

Using the provider's own token-counting mechanism or actual API usage information.

This distinction becomes important when calculating production costs.

---

# 7. Context

An LLM does not automatically have access to every piece of information that exists in an application.

The application typically constructs the model input.

A simplified conversation flow is:

```text
User message
      ↓
Application
      ↓
Conversation history + instructions + current message
      ↓
LLM
```

Therefore, when an application appears to "remember" a previous message, the system may actually be supplying the relevant conversation history as part of the model context.

This distinction becomes particularly important for:

- Chat applications
- RAG
- Agents
- Context management
- Long conversations

---

# 8. Context Window

The context window represents the amount of tokenized information the model can process within a given request/session boundary.

Conceptually:

```text
System instructions
        +
Conversation history
        +
User prompt
        +
Retrieved documents
        +
Tool information
        ↓
      Context
        ↓
       LLM
```

More context is not automatically better.

Excessive context can result in:

- Higher cost
- Higher latency
- Context-window pressure
- More irrelevant information
- Potentially poorer retrieval/application behavior

This becomes a major architectural concern in RAG systems.

---

# 9. LLM APIs

The underlying interaction can be viewed as:

```text
Application
     |
     | Prompt + parameters
     ↓
LLM API / Runtime
     |
     ↓
Model inference
     |
     ↓
Generated response
```

Frameworks such as LangChain add abstraction around this process.

A useful progression is:

```text
Raw LLM API
     ↓
LangChain
     ↓
LangGraph
     ↓
Agents
```

The goal is to understand what the abstraction is doing rather than simply learning framework syntax.

---

# 10. Local LLM Architecture

The Day 1 setup provides a local model path:

```text
Python Application
        ↓
LLM abstraction
        ↓
Ollama
        ↓
Qwen3 8B
        ↓
Local inference
        ↓
Response
```

This is useful for experimentation because it allows development without necessarily incurring external API costs.

---

# 11. RAG Connection — Why Tokens Matter Architecturally

One of the most important connections made during Day 2 was between tokens and RAG.

A typical RAG flow looks like:

```text
User Question
      ↓
Retriever
      ↓
Relevant Documents
      ↓
Context Assembly
      ↓
LLM
      ↓
Answer
```

Suppose:

```text
Question          100 tokens
Retrieved docs   18,000 tokens
Instructions       500 tokens
--------------------------------
Input             18,600 tokens
```

The retrieved documents become part of the LLM input.

Therefore:

```text
More retrieved context
        ↓
More tokens
        ↓
Higher potential cost
        ↓
Higher potential latency
        ↓
More context-window consumption
```

This means RAG design is not simply about retrieving "more information."

It requires balancing:

- Retrieval quality
- Top-K
- Chunk size
- Reranking
- Context compression
- Token consumption
- Cost
- Latency
- Answer quality

---

# 12. Data Engineering / Architecture Perspective

The LLM application can be viewed as another distributed data-processing system.

A simplified architecture is:

```text
                    ┌──────────────┐
                    │     User     │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Application  │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │     LLM      │
                    └──────┬───────┘
                           ↓
                 ┌─────────┴─────────┐
                 ↓                   ↓
              Knowledge            Tools
                 ↓                   ↓
                RAG              APIs / DB
                 └─────────┬─────────┘
                           ↓
                         Agent
```

This gives a useful progression for the bootcamp:

```text
LLM fundamentals
       ↓
LLM application
       ↓
Prompting
       ↓
Structured outputs
       ↓
Embeddings
       ↓
RAG
       ↓
Tools
       ↓
Agents
       ↓
LangGraph
       ↓
MCP
```

---

# 13. Day 2 Hands-On Philosophy

The objective is not to write large amounts of code.

The preferred learning loop is:

```text
Course example
      ↓
Run unchanged
      ↓
Understand it
      ↓
Change ONE thing
      ↓
Observe the result
      ↓
Explain WHY
```

The course repository should be treated as the baseline implementation.

Experiments should extend or modify the course examples rather than unnecessarily rebuilding infrastructure from scratch.

---

# 14. Key Experiments

## Experiment 1 — Token Count

Start with a small prompt and progressively increase its size.

For example:

```text
100 tokens
1,000 tokens
5,000 tokens
10,000 tokens
```

Observe:

- Token count
- Context utilization
- Estimated cost

---

## Experiment 2 — Context

Test a conversation such as:

```text
User: My name is Bob and I am a data engineer.

User: What do I do?

User: What technology am I learning?
```

Then inspect what information is actually supplied to the model.

The key learning is understanding the difference between:

```text
Model memory
```

and

```text
Application-provided context
```

---

## Experiment 3 — Raw LLM Call

Understand the underlying interaction before relying completely on framework abstractions.

Conceptually:

```text
Application
    ↓
Prompt + parameters
    ↓
LLM runtime/API
    ↓
Model
    ↓
Response
```

Then understand what LangChain adds around that interaction.

---

## Experiment 4 — Model Parameters

Experiment with parameters such as:

```text
temperature
max tokens
system prompt
user prompt
```

The objective is to observe how changing the request changes the generated output.

---

# 15. Important Mental Models

### Mental Model 1 — LLM

```text
LLM ≠ Database

LLM = learned model performing inference
      based on supplied context
```

### Mental Model 2 — Tokens

```text
Tokens
  ↓
Context
  ↓
Cost
  ↓
Latency
```

### Mental Model 3 — RAG

```text
Retrieval quality
        +
Context management
        +
Token economics
        +
LLM reasoning
        =
RAG application
```

### Mental Model 4 — Frameworks

```text
Raw API
   ↓
Abstraction
   ↓
Orchestration
   ↓
Agent
```

Do not learn LangChain/LangGraph as isolated APIs. Understand the problem each abstraction solves.

---

# 16. Day 1 + Day 2 Overall Progress

## Completed

- Python development environment
- Virtual environment
- Git/GitHub repository
- Ollama
- Qwen3 8B
- Course setup
- Initial course modules
- LLM fundamentals
- Generative AI fundamentals
- Transformer high-level understanding
- Tokens
- Context
- LLM API concepts
- Token economics
- Initial RAG/token-cost connection

## Current Architecture Mental Model

```text
                   ┌─────────────────┐
                   │      User       │
                   └────────┬────────┘
                            ↓
                   ┌─────────────────┐
                   │   Application   │
                   └────────┬────────┘
                            ↓
                   ┌─────────────────┐
                   │  LLM / Agent   │
                   └────────┬────────┘
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
         Context / RAG                 Tools
              ↓                           ↓
        Documents / DB                APIs / DB
              └─────────────┬─────────────┘
                            ↓
                     Final Response
```

---

# 17. Key Takeaways

1. **An LLM is fundamentally a next-token prediction system.**
2. **Tokens are the bridge between text, model processing, context limits, and API economics.**
3. **Tokenizer output is model/provider dependent.**
4. **Token counts can be translated into API costs when the correct provider pricing is applied.**
5. **Input and output tokens should be treated separately when calculating cost.**
6. **Context is constructed by the application and is not equivalent to permanent model memory.**
7. **RAG introduces additional context, which directly affects token usage, cost, latency, and context-window utilization.**
8. **LangChain and LangGraph are abstractions/orchestration frameworks; they should not replace understanding the underlying LLM interaction.**
9. **Local models such as Qwen3 through Ollama are useful for experimentation and learning.**
10. **The right learning loop is: run → understand → modify → observe → explain.**

---

# Day 3 Starting Point

The next logical layer is:

```text
LLM Fundamentals
       ↓
Prompt Engineering
       ↓
Structured Outputs
       ↓
Chains
       ↓
Embeddings
       ↓
RAG
```

The focus should remain on understanding the underlying architecture while using the course code as the implementation baseline.

---

## Personal Learning Principle

> **Don't just learn how to call an LLM. Learn how to design, operate, optimize, and architect systems that use LLMs.**
