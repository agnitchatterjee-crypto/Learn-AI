# Week 2 — Gradio, Chat History & Interactive AI Applications

## Overview

The last two study sessions focused on moving from simple LLM experiments into interactive AI applications using **Gradio**.

### What I worked on

- Built an interactive CV-to-career-plan application.
- Added `.docx` document upload.
- Added model selection.
- Built a simple AI chatbot.
- Experimented with multi-turn conversations.
- Learned how conversation history is passed to an LLM.
- Compared text-based history with structured chat messages.
- Worked with local Ollama models and hosted models.
- Investigated streaming responses.
- Debugged Gradio and SDK/API compatibility issues.
- Started thinking about how these patterns evolve into RAG and agentic applications.

The key progression is:

```text
Prompt → LLM → Response
```

towards:

```text
User
  ↓
Application UI
  ↓
Application State
  ↓
LLM
  ↓
Response
  ↓
Updated State
  ↓
User
```

---

# 1. Interactive Career Planner

I built a Gradio application that:

1. Accepts a user's CV in `.docx` format.
2. Allows the user to select an LLM.
3. Processes the CV.
4. Generates a personalized one-year career plan.

The intended use case is:

> Based on a person's current profile, what should they do to approximately 2x their salary over the next year?

## High-level architecture

```text
CV (.docx)
    ↓
Document Extraction
    ↓
Prompt Construction
    ↓
Selected LLM
    ↓
Career Plan Generation
    ↓
Gradio UI
```

This is a simple example of a real AI application.

The same architecture can later be applied to:

- Resume analysis
- Technical document analysis
- Data documentation analysis
- Source-to-target mapping
- SQL migration analysis
- Architecture document analysis

This makes the application a useful precursor to the planned **Intelligent Data Migration Agent**.

---

# 2. Simple AI Chatbot

I also created a simple Gradio chatbot to experiment with multi-turn conversations.

Example:

```text
User: Hello

Assistant: Hello! How can I assist you today?

User: May I know you more? I am Bob.

Assistant: Hello Bob! Nice to meet you.

User: Let's talk about being lonely.

Assistant: I'm sorry to hear that you're feeling lonely...
```

The important learning was not the UI itself.

The important learning was **conversation state and context**.

---

# 3. Multi-turn Conversations

A basic LLM call looks like:

```text
Prompt
  ↓
LLM
  ↓
Response
```

For a multi-turn conversation, the application needs to provide the relevant previous conversation again:

```text
Turn 1
User → Assistant

Turn 2
User → Assistant

Turn 3
User → Assistant
```

Conceptually:

```text
Application
    |
    |-- System instructions
    |-- Previous user message
    |-- Previous assistant response
    |-- New user message
    |
    v
   LLM
    |
    v
 New assistant response
```

Therefore:

> **Conversation history is part of the model's context.**

The application is responsible for deciding what history is sent to the model.

---

# 4. Understanding Chat Roles

Modern chat APIs commonly use roles such as:

- `system`
- `user`
- `assistant`
- `tool`

A typical request looks like:

```python
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant."
    },
    {
        "role": "user",
        "content": "What is Snowflake?"
    },
    {
        "role": "assistant",
        "content": "Snowflake is a cloud data platform."
    },
    {
        "role": "user",
        "content": "How does it compare with Databricks?"
    }
]
```

The roles are part of the structured API request.

They are not simply text labels.

---

# 5. Important Correction About the Original Chat History

My original implementation used a text blob containing labels such as:

```text
assistant: Hello
user: Hi
assistant: How are you?
user: Tell me about Snowflake
```

inside a single API message.

For example, conceptually:

```python
{
    "role": "assistant",
    "content": """
        assistant: Hello
        user: Hi
        assistant: How are you?
        user: Tell me about Snowflake
    """
}
```

In this case, the API technically sees the **entire block as one assistant message**.

The model may still understand the conversation because the content contains:

```text
assistant:
user:
```

and the system prompt may explain the intended meaning.

However, this is not the correct long-term architecture.

## Better approach

Use proper structured messages:

```python
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi"},
    {"role": "user", "content": "Tell me about Snowflake"}
]
```

This gives the model explicit speaker information.

---

# 6. Better Chat History Design

Instead of storing one giant text string, maintain structured messages.

```python
history = [
    {
        "role": "user",
        "content": "What is Snowflake?"
    },
    {
        "role": "assistant",
        "content": "Snowflake is a cloud data platform."
    }
]
```

Then construct the model request:

```python
messages = [
    {
        "role": "system",
        "content": system_prompt
    },
    *history
]
```

And call the model:

```python
response = client.chat.completions.create(
    model=model,
    messages=messages
)
```

## Why this is better

### Explicit speaker identity

The API knows which message came from the user and which came from the assistant.

### Less prompt engineering

The prompt does not need to explain:

```text
The assistant is you.
The user is the other person.
```

### Better model compatibility

The structure matches the format used by modern chat-oriented APIs.

### Easier extension

The structure can later support:

```text
system
user
assistant
tool
```

and tool calls.

### Easier context management

Old turns can later be:

- Removed
- Summarized
- Compressed
- Persisted
- Retrieved
- Selectively included

without manipulating one large text blob.

---

# 7. Application State vs Model Context

This distinction is important.

## Application state

What the application stores:

```text
Conversation history
Uploaded documents
User selections
Session information
```

## Model context

What is actually sent to the LLM for a particular inference request:

```text
System instructions
Relevant conversation history
Retrieved documents
Tool results
Current user request
```

They are related, but they are not the same thing.

A mature AI application should explicitly control what moves from **application state** into **model context**.

This becomes extremely important with RAG and agents.

---

# 8. Neutral Conversation State and Model Adapters

A useful architecture is to separate application state from provider-specific message formats.

For example:

```python
history = [
    ("user", "Hello"),
    ("assistant", "Hi"),
    ("user", "Explain Snowflake")
]
```

Then an adapter can convert this into the format expected by a provider:

```text
Application State
       |
       +---- OpenAI adapter
       |
       +---- Ollama adapter
       |
       +---- Anthropic adapter
       |
       +---- Gemini adapter
```

This is an early example of a **model abstraction layer**.

For a larger application, the application should ideally not contain provider-specific logic everywhere.

---

# 9. Streaming Responses

I also encountered code similar to:

```python
response += chunk.choices[0].delta.content or ""
```

This is associated with streaming LLM responses.

Without streaming:

```text
Request
  ↓
Wait
  ↓
Complete response
```

With streaming:

```text
Request
  ↓
Chunk 1
  ↓
Chunk 2
  ↓
Chunk 3
  ↓
...
  ↓
Final response
```

Streaming improves perceived latency because the UI can start displaying output immediately.

For a chatbot, this creates a much better user experience.

---

# 10. Debugging the `tuple` Error

One error encountered was:

```text
AttributeError: 'tuple' object has no attribute 'choices'
```

The failing logic expected something like:

```python
chunk.choices[0].delta.content
```

which assumes that `chunk` is an SDK response object.

However, the runtime object was actually a:

```text
tuple
```

This means the actual return type did not match the assumption in the code.

## Debugging technique

When unsure about an object's structure:

```python
print(type(chunk))
print(chunk)
```

or:

```python
for chunk in response:
    print(type(chunk))
    print(chunk)
```

This establishes the actual runtime contract.

## Engineering lesson

Do not assume that different LLM providers return identical response objects.

For example:

```text
OpenAI SDK
    ≠
Ollama SDK
    ≠
Anthropic SDK
    ≠
LangChain abstraction
```

The conceptual operation may be identical while the Python objects and streaming interfaces differ.

---

# 11. Gradio API Compatibility Issue

Another error was:

```text
TypeError: File.__init__() got an unexpected keyword argument 'info'
```

The code attempted:

```python
gr.File(
    file_types=[".docx"],
    info="Upload your CV..."
)
```

The installed Gradio version did not support the `info` parameter for `gr.File`.

This is an API contract/version issue rather than a problem with the overall application architecture.

Useful debugging commands include:

```python
import gradio as gr

print(gr.__version__)
```

and:

```python
help(gr.File)
```

General lesson:

```text
Python Code
    ↓
Installed Library Version
    ↓
Actual API Contract
```

Always verify the API supported by the installed version.

---

# 12. Local Ollama Models

The local environment currently contains models including:

```text
gemma3:270m
llama3.2:latest
qwen3:8b
```

The experiments helped demonstrate the difference between local inference and hosted inference.

## Local

```text
Application
    ↓
Ollama
    ↓
Local Model
```

Advantages:

- No external API call required.
- Useful for experimentation.
- Potentially better data privacy.
- No per-token API cost.
- Can work offline once the model is available.

Limitations:

- Hardware constraints.
- Smaller models can have weaker capabilities.
- Model/runtime management is the user's responsibility.

## Hosted

```text
Application
    ↓
API
    ↓
Cloud LLM
```

Advantages:

- Access to larger models.
- Generally stronger capabilities.
- Infrastructure is managed by the provider.

Limitations:

- API cost.
- Network dependency.
- Data governance concerns.
- Provider-specific APIs and limits.

---

# 13. Model Selection for the Intelligent Data Migration Agent

I currently have **`qwen3:8b`** available locally through Ollama.

For the initial version of the **Intelligent Data Migration Agent**, I decided to continue using this model rather than immediately moving to a larger model.

The important learning is that the success of an agentic AI application should not depend only on choosing the largest available LLM. The application architecture, deterministic tools, context management and quality of the inputs are equally important.

## Why `qwen3:8b` is a reasonable starting point

For the current stage of the project, `qwen3:8b` is suitable for experimenting with:

- SQL understanding
- Python code generation
- SQL / dbt code generation
- Tool calling and agent workflows
- Structured outputs
- Individual database artifact analysis
- Migration explanations and recommendations

The model may be less capable when asked to perform very complex reasoning across a large repository or a very large amount of source code in a single context.

Therefore, the architecture should avoid simply sending the entire source repository to the LLM.

## Better architecture

Instead of:

```text
55 SQL files
      ↓
bundle.md
      ↓
LLM
      ↓
"Understand everything"
```

use deterministic Python processing first:

```text
Source SQL files
       ↓
Deterministic Python analysis
       ↓
┌─────────────────────────┐
│ Inventory               │
│ Tables                  │
│ Procedures              │
│ Views                   │
│ Functions               │
│ Dependencies            │
│ SQL constructs          │
│ Complexity              │
│ Lineage / relationships │
└─────────────────────────┘
       ↓
Structured metadata
       ↓
Qwen3 8B
       ↓
Migration reasoning
       ↓
Migration plan / SQL / dbt / mappings
```

This follows an important AI engineering principle:

> **Use deterministic code to extract facts; use the LLM to interpret those facts and make migration recommendations.**

## Model abstraction

The model should also remain configurable rather than being hard-coded throughout the application.

Conceptually:

```text
Migration Agent
       ↓
   Model Interface
       │
       ├── qwen3:8b
       ├── qwen3.5:9b
       ├── gpt-oss:20b
       └── qwen3-coder:30b
```

The initial implementation can use `qwen3:8b`. Larger models can be introduced later and evaluated against the same migration tasks.

## Future model evaluation

Once the agent is functional, model selection itself can become an engineering experiment:

```text
                 Same migration task
                         ↓
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
      Qwen3 8B      Qwen3.5 9B     GPT-OSS 20B
          │              │              │
          └──────────────┼──────────────┘
                         ↓
                  Evaluation results
```

Potential evaluation dimensions include:

- SQL / migration accuracy
- Tool-calling reliability
- Structured-output compliance
- Reasoning quality
- Response latency
- Memory / resource consumption
- Overall usefulness for migration tasks

This is more useful than selecting a model purely based on parameter count.

---

# 15. Model Capability vs Application Bugs

A very small model such as:

```text
gemma3:270m
```

may struggle with a complex prompt containing multiple instructions.

For example:

```text
Analyze CV
+
Identify skills
+
Identify gaps
+
Create a 12-month plan
+
Consider salary progression
+
Format output
```

This is much harder than:

```text
Say hello.
```

Therefore:

> **A poor model response is not automatically an application bug.**

The result depends on:

```text
Model capability
+
Prompt complexity
+
Context size
+
Task complexity
+
Output requirements
```

This is an important debugging distinction.

---

# 15. Structured LLM Output

The career planner currently generates mainly textual output.

A future version should produce structured data such as:

```python
career_plan = {
    "current_profile": "...",
    "target_role": "...",
    "salary_target": "...",
    "skill_gaps": [
        "...",
        "..."
    ],
    "quarter_1": [],
    "quarter_2": [],
    "quarter_3": [],
    "quarter_4": [],
    "recommended_projects": []
}
```

The UI can then render individual sections.

This leads to an important AI engineering principle:

> **LLM output should increasingly be treated as data rather than just text.**

This becomes particularly important for:

- RAG
- Tool calling
- Agents
- SQL generation
- Data mapping
- Migration recommendations
- API integrations

---

# 16. Connection to the Intelligent Data Migration Agent

The current experiments are directly relevant to the planned:

**Intelligent Data Migration Agent**

## Current CV application

```text
DOCX
  ↓
Document Extraction
  ↓
Context / Prompt
  ↓
LLM
  ↓
Career Plan
  ↓
Gradio
```

## Future migration agent

```text
Source Documentation
        ↓
Document / Schema Extraction
        ↓
Schema Analysis
        ↓
RAG / Knowledge Retrieval
        ↓
LLM / Agent
        ↓
Migration Recommendations
        ↓
SQL / dbt / Mapping Generation
        ↓
Human Review
```

The current exercises are therefore not isolated toys.

They are building the components needed for the larger architecture.

---

# 17. Evolution of the Architecture

## Level 1 — Simple LLM Call

```text
Prompt
  ↓
LLM
  ↓
Response
```

## Level 2 — Interactive AI Application

```text
User
  ↓
Gradio
  ↓
LLM
  ↓
Response
```

## Level 3 — Stateful Chat Application

```text
User
  ↓
Gradio
  ↓
Conversation State
  ↓
LLM
  ↓
Updated State
```

## Level 4 — Document-aware Application

```text
Document
  ↓
Extraction
  ↓
Context
  ↓
LLM
  ↓
Response
```

## Level 5 — RAG

```text
Document
  ↓
Chunking
  ↓
Embeddings
  ↓
Vector Store
  ↓
Retrieval
  ↓
LLM
```

## Level 6 — Agent

```text
User
  ↓
Agent
  ↓
Reason
  ↓
Retrieve / Tool
  ↓
Observe
  ↓
Reason
  ↓
Tool
  ↓
Final Response
```

Ultimate target:

```text
RAG + Tools + Agent + Data Engineering
                    ↓
       Intelligent Data Migration Agent
```

---

# 18. Key Concepts Learned

## Gradio

Python framework for quickly creating interactive interfaces around ML/AI applications.

Useful components:

- `gr.File`
- `gr.Textbox`
- `gr.Dropdown`
- `gr.Button`
- `gr.Chatbot`
- `gr.Interface`
- `gr.Blocks`

## Conversation State

Previous conversation turns must be available to the application so the relevant context can be supplied to the LLM.

## Message Roles

Use structured roles such as:

```text
system
user
assistant
tool
```

instead of manually embedding:

```text
user:
assistant:
```

inside one large text prompt.

## Streaming

Allows generated content to be delivered incrementally.

## Model Abstraction

Different providers expose different SDKs and response structures. Provider-specific code should ideally be isolated behind an abstraction.

## Application State vs Model Context

The application may store more information than is actually sent to the model.

This distinction becomes critical when context windows and token costs become important.

---

# 19. Engineering Lessons

### Lesson 1

Do not treat an LLM as a database.

The application must explicitly manage the context it wants the model to see.

### Lesson 2

Use structured messages instead of giant conversation strings.

### Lesson 3

Separate application state from model-provider-specific request formats.

### Lesson 4

Inspect runtime object types when debugging SDK integrations.

```python
print(type(response))
print(response)
```

### Lesson 5

Library versions matter.

Check the installed version when an API parameter is rejected.

### Lesson 6

A model limitation is not necessarily an application bug.

### Lesson 7

Move toward structured LLM output.

Text is useful for humans; structured data is much more useful for software.

---

# 20. Next Learning Steps

## Step 1 — Clean up the chatbot

Implement:

```text
Gradio Chatbot
      ↓
Structured message history
      ↓
System prompt
      ↓
LLM abstraction
      ↓
Streaming response
```

## Step 2 — Document Q&A

```text
Upload DOCX
      ↓
Extract text
      ↓
Ask questions
      ↓
LLM
```

## Step 3 — Introduce chunking

```text
Document
   ↓
Chunks
   ↓
Relevant chunks
   ↓
LLM
```

## Step 4 — Introduce embeddings

```text
Document
   ↓
Chunks
   ↓
Embeddings
   ↓
Vector Database
```

## Step 5 — Build RAG

```text
Question
   ↓
Retriever
   ↓
Relevant Context
   ↓
LLM
   ↓
Answer
```

## Step 6 — Introduce tools

```text
LLM
 ↓
Tool Selection
 ↓
Tool Execution
 ↓
Result
 ↓
LLM
```

## Step 7 — Build the Intelligent Data Migration Agent

```text
Source System
      ↓
Metadata / Documentation
      ↓
RAG
      ↓
Agent
      ↓
SQL / dbt / Mapping / Documentation
      ↓
Human Review
      ↓
Migration Artifacts
```

---

# 21. Overall Progress

The biggest shift during these sessions was:

```text
"I am learning how to call an LLM."
```

to:

```text
"I am learning how to build an application around an LLM."
```

That is an important milestone.

As a data engineer / architect, the second capability is considerably more valuable.

The next major learning objective is understanding how:

```text
LLM
+
Context
+
State
+
Documents
+
Retrieval
+
Tools
+
Orchestration
```

combine into a production-grade AI system.
