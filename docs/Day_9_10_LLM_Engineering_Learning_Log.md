# LLM Engineering Learning Log — Day 9 & Day 10

**Dates**
- Day 9: Friday, 2 October 2026
- Saturday, 3 October 2026: Trip / no study
- Sunday, 4 October 2026: Trip / no study
- Day 10: Monday, 5 October 2026

---

# Day 9 — Friday, 2 October 2026

## Focus

Hands-on exploration of LLM inference, model providers, reasoning, and different ways of accessing models.

---

## 1. Training vs Inference

### Training

Training is where the model learns by adjusting its weights.

Typical characteristics:

- Huge training datasets
- Forward pass
- Loss calculation
- Backpropagation
- Gradient calculation
- Weight updates
- Large amounts of GPU compute
- Model weights change during training

### Inference

Inference is when a trained model uses its existing weights to generate an answer.

Typical characteristics:

- Model weights are fixed
- Input is supplied as a prompt
- The model performs a forward pass
- Output tokens are generated
- Compute is spent for each request

My code experiments are performing **inference**, not training.

### Key distinction

> **Training builds/updates the model. Inference uses the trained model.**

---

# 2. Where Reasoning Fits

Reasoning is not a separate stage like training or inference.

A reasoning-capable model can be:

1. **Trained** to perform better on multi-step reasoning.
2. During **inference**, it can spend additional compute/tokens working through a difficult problem before producing the final answer.

This connects to the idea of **inference-time scaling / test-time compute**.

The important mental model is:

```text
Training
    ↓
Model learns capabilities
    ↓
Inference
    ↓
Model receives a prompt
    ↓
Reasoning / computation may happen
    ↓
Final response
```

---

# 3. Experimenting with Reasoning Effort

I experimented with GPT-5 using the `reasoning_effort` parameter.

Example:

```python
response = openai.chat.completions.create(
    model="gpt-5-nano",
    messages=easy_puzzle,
    reasoning_effort="minimal"
)
```

The important learning was that inference can be configured not only by selecting a model, but also by controlling aspects of how much reasoning effort is used.

This is important for production architecture because there is a trade-off between:

- reasoning quality
- latency
- token usage
- cost

---

# 4. Grok vs Groq

I clarified the difference between **Grok** and **Groq**.

## Grok

- AI model family from xAI
- Used through xAI and X
- Provides LLM capabilities

## Groq

- AI inference company
- Focuses on high-speed inference
- Provides GroqCloud
- Hosts models from different model developers

### Mental model

```text
Grok
  → AI model / model family

Groq
  → Inference infrastructure / provider
```

The similar names are confusing, but they solve very different problems.

---

# 5. LangChain vs OpenRouter

I learned that LangChain and OpenRouter are **not direct alternatives**.

## LangChain

LangChain is an application framework/library.

It provides abstractions for:

- Prompt templates
- Chains
- Agents
- Tools
- Retrievers
- RAG
- Output parsers
- Model integrations

It helps orchestrate the logic of an LLM application.

## OpenRouter

OpenRouter is a hosted model gateway.

It provides access to models from multiple providers through a common API.

The important benefit is that applications can switch between models/providers without completely rewriting the application integration.

### Mental model

```text
Application
    ↓
LangChain
    ↓
OpenRouter
    ↓
Model Provider / Model
```

They can therefore be used together.

---

# 6. LangChain vs LiteLLM

I also explored the difference between LangChain and LiteLLM.

## LiteLLM

LiteLLM provides a unified interface to different LLM providers.

It is useful for:

- Provider abstraction
- Switching models
- Cost tracking
- Retries
- Fallbacks
- Routing
- Load balancing
- Proxy/gateway scenarios

## LangChain

LangChain focuses more on application orchestration:

- Chains
- Agents
- Tools
- RAG
- Retrievers
- Memory/state
- Output parsing

### Mental model

```text
                 LLM Application
                       │
              ┌────────┴────────┐
              │                 │
          LangChain          LiteLLM
              │                 │
      App orchestration    Model abstraction
      Agents               Cost tracking
      RAG                   Routing
      Tools                Fallbacks
              │                 │
              └────────┬────────┘
                       ↓
                LLM Providers
```

### Rule of thumb

Use **LiteLLM** when the primary problem is:

> "How do I call and manage many different LLM providers consistently?"

Use **LangChain** when the primary problem is:

> "How do I build the logic and workflow of an LLM application?"

They can also be combined.

---

# 7. Key Architecture Learning from Day 9

The important shift today was from thinking about an LLM as just a model to thinking about the **LLM ecosystem**.

An application can have multiple abstraction layers:

```text
                    LLM Application
                           │
                    Application Logic
                           │
                    LangChain / Agent
                           │
                  Provider Abstraction
                   LiteLLM / OpenRouter
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
           OpenAI       Anthropic     Local/Ollama
              │
           Models
```

This is directly relevant to production AI architecture because model choice can change independently from application orchestration.

---

# Day 10 — Monday, 5 October 2026

## Focus

Hands-on implementation using multiple LLM providers, local inference, token/cost tracking, document extraction, and streaming.

---

# 8. OpenRouter Experiment

I created an OpenRouter client using the OpenAI-compatible API.

```python
openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
openrouter_url = "https://openrouter.ai/api/v1"

openrouter = OpenAI(
    base_url=openrouter_url,
    api_key=openrouter_api_key
)
```

This demonstrated an important concept:

> An application can use the familiar OpenAI Python client while pointing it at a different OpenAI-compatible provider.

I also captured:

- Input tokens
- Output tokens
- Total tokens
- Cost

Example:

```python
print(f"Input tokens: {response.usage.prompt_tokens}")
print(f"Output tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
```

This introduced me to the idea of **LLM observability and cost awareness**.

For production systems, token usage should not be treated as an afterthought.

---

# 9. Local LLM Inference with Ollama

I also used LangChain with Ollama.

```python
model = ChatOllama(
    model="llama3.2:latest",
    temperature=0.7,
)

response = model.invoke(tell_a_joke)

print(response.content)
```

This was useful because it demonstrated a completely different deployment model:

```text
Cloud API

Application
    ↓
API
    ↓
Cloud-hosted LLM
```

versus:

```text
Local inference

Application
    ↓
Ollama
    ↓
Local model
    ↓
Local hardware
```

This is important when considering:

- Data privacy
- Network dependency
- Cost
- Latency
- Model availability
- Infrastructure requirements

---

# 10. Document Intelligence Experiment

The most interesting hands-on exercise was using my CV as input to an LLM application.

I used `python-docx` to extract information from the DOCX file.

The extraction function handles:

- Paragraphs
- Tables

Example:

```python
def extract_text(path):
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs]

    for table in doc.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))

    return "\n".join(parts)
```

This gave me a structured text representation of an enterprise document that could then be supplied to the LLM.

---

# 11. Combining Multiple Sources into a Prompt

I combined:

- My CV
- The course contents
- Instructions about my current skills
- Instructions about current industry trends
- Requirements for identifying real-world projects

The LLM was then asked to act as a career/project guide.

This is an important transition from:

```text
Simple prompt
    ↓
Answer
```

to:

```text
Multiple data sources
       ↓
Context construction
       ↓
Prompt
       ↓
LLM
       ↓
Structured output / recommendations
```

This is starting to look much closer to a real **LLM application architecture**.

---

# 12. Streaming LLM Responses

I also implemented streaming responses.

The core pattern was:

```python
stream = openai.chat.completions.create(
    model="gpt-4.1-mini",
    messages=messages,
    response_format={"type": "text"},
    stream=True
)

response = ""

for chunk in stream:
    response += chunk.choices[0].delta.content or ""
```

Instead of waiting for the complete response, the application receives chunks as they are generated.

Conceptually:

```text
LLM
 │
 ├── chunk 1
 ├── chunk 2
 ├── chunk 3
 ├── chunk 4
 └── ...
        ↓
Application
        ↓
Incremental rendering
```

This improves the perceived responsiveness of an LLM application.

---

# 13. Rich Live Markdown Rendering

I used:

```python
with Live(Markdown(""), refresh_per_second=8) as live:
```

The idea is to maintain a live terminal area and repeatedly update it as new response chunks arrive.

The accumulated response is re-rendered:

```python
live.update(Markdown(response))
```

This means the user can see formatted Markdown while the LLM is still generating.

Important implementation detail:

```python
chunk.choices[0].delta.content or ""
```

The `or ""` prevents problems when a streamed chunk does not contain content.

---

# 14. What I Built Conceptually

My current experiment can be represented as:

```text
                  CV / DOCX
                     │
                     ↓
              python-docx
                     │
                     ↓
             Extracted Text
                     │
                     │
Course Contents ─────┤
                     ↓
              Prompt Builder
                     │
                     ↓
              LLM API
                     │
               Streaming
                     │
                     ↓
              Rich Markdown
                     │
                     ↓
                output.md
```

This is a basic but legitimate **document-to-LLM pipeline**.

---

# 15. What I Learned This Week

The learning has moved through several layers.

## LLM fundamentals

- Tokens
- Tokenization
- Context windows
- Parameters
- Training
- Inference
- Reasoning
- Inference-time scaling

## Model ecosystem

- OpenAI
- Grok / xAI
- Groq
- OpenRouter
- Ollama
- Local models

## Application frameworks

- LangChain
- LiteLLM
- OpenAI-compatible APIs

## Engineering concepts

- API keys and environment variables
- Provider abstraction
- Token tracking
- Cost tracking
- Local inference
- Document extraction
- Prompt construction
- Streaming
- Markdown rendering

---

# 16. Architecture Takeaway

The biggest takeaway is that building an AI application is not simply:

```text
Prompt → LLM → Response
```

A production-grade architecture increasingly looks more like:

```text
                    User / Application
                           │
                           ↓
                    Application API
                           │
                           ↓
                  Orchestration Layer
                  LangChain / LangGraph
                           │
             ┌─────────────┼─────────────┐
             ↓             ↓             ↓
          Tools           RAG        Model Router
             │             │             │
             │       ┌─────┴─────┐       │
             │       ↓           ↓       │
             │   Vector DB    Documents  │
             │                         │
             └─────────────┬───────────┘
                           ↓
                   Model Abstraction
                  LiteLLM / Gateway
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
           OpenAI      Anthropic      Ollama
```

This is the direction I want to continue toward as a Data Engineer / Solution Architect.

---

# 17. Gaps / Things to Revisit

I should revisit these concepts rather than just moving on:

- Difference between training, inference and reasoning
- Inference-time scaling
- OpenRouter vs LiteLLM
- LangChain vs LiteLLM
- When to use local models vs hosted models
- Token economics
- Streaming architecture
- How model routing works
- How RAG fits into the architecture
- How agents fit on top of tools + LLMs
- How to productionize the current document-processing experiment

---

# 18. Connection to My Real-World Project

The current learning maps directly to my planned project:

## Intelligent Data Migration Agent

The concepts learned so far can eventually map to:

```text
Source Database / Files
          │
          ↓
   Metadata Extraction
          │
          ↓
   LLM-powered Analysis
          │
     ┌────┴────┐
     ↓         ↓
 Schema     ETL Logic
 Analysis   Analysis
     │         │
     └────┬────┘
          ↓
   Migration Planning
          │
          ↓
     SQL / dbt Code
          │
          ↓
    Validation Agent
          │
          ↓
 Migration Report
```

The current CV/document experiment is therefore useful practice for the same broader pattern:

> **Extract data → construct context → invoke LLM → stream/process output → produce an artifact.**

---

# 19. Next Step

The next stage should move beyond basic API calls.

I should start learning and implementing:

1. Structured outputs
2. Function/tool calling
3. Embeddings
4. Vector databases
5. RAG
6. Chunking strategies
7. Retrieval evaluation
8. LangChain/LangGraph
9. Agent workflows
10. Building the first version of the **Intelligent Data Migration Agent**

The objective is to progressively move from:

```text
LLM experimentation
```

to:

```text
LLM Engineering
```

and eventually to:

```text
Production AI / Data Architecture
```

---

# Overall Progress

**Status: Good progress**

The most important improvement is that I am no longer learning LLMs only as an end user.

I am starting to understand the components required to **engineer systems around LLMs**:

- Models
- Providers
- APIs
- Inference
- Reasoning
- Token economics
- Frameworks
- Local inference
- Documents
- Streaming
- Application orchestration

This is the right foundation for progressing toward AI-focused Data Engineering and Solution Architecture.
