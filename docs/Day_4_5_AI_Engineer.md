# AI Engineer Learning Journey — Day 4 & Day 5

## Day 4 — Tokens, Token IDs and Embeddings

### Context

Day 4 was a late and very tired study session, so the focus was deliberately kept small. The goal was to reinforce the fundamentals rather than push through a large amount of new material.

### What I learned

#### 1. Token

A **token** is a piece of text that an LLM's tokenizer converts into a unit that the model can process.

A token can be:

- a complete word
- part of a word
- punctuation
- whitespace combined with text
- a special token

Tokenization depends on the tokenizer and vocabulary used by the model.

Example:

```text
"LLMs"
```

can be split into something like:

```text
[" L", "LM", "s"]
```

The exact tokens depend on the tokenizer.

### 2. Token ID

A **token ID** is the integer identifier assigned to a token in the tokenizer's vocabulary.

Conceptually:

```text
Text
  ↓
Tokenizer
  ↓
Tokens
  ↓
Token IDs
```

For example:

```text
"hello"
   ↓
["hello"]
   ↓
[15339]
```

The important distinction:

> **A token ID is an identifier, not a semantic representation of the token.**

### 3. Token ID vs Embedding

This was an important distinction from Day 4.

| Concept | Meaning |
|---|---|
| Token | Text unit produced by the tokenizer |
| Token ID | Integer index representing that token in the vocabulary |
| Embedding | Dense numerical vector representing learned semantic information |

The flow is approximately:

```text
Text
  ↓
Tokenizer
  ↓
Tokens
  ↓
Token IDs
  ↓
Embedding / model representation
  ↓
Transformer processing
  ↓
Output
```

A token ID such as:

```text
15339
```

does **not** mean that the number itself contains semantic meaning.

The model uses the token ID to look up a learned vector representation.

### 4. Hands-on Python experiment

Created a small tokenizer Python script to:

- generate tokens from text
- inspect token IDs
- count tokens
- decode token IDs back into text

The experiment helped connect the theoretical concepts to the actual LLM processing pipeline.

A useful mental model:

```text
Human-readable text
        ↓
     Tokenizer
        ↓
      Tokens
        ↓
    Token IDs
        ↓
 Learned representations
        ↓
 Transformer / LLM
```

### Key takeaway

> **Tokenization converts text into tokens, token IDs provide vocabulary indexes for those tokens, and embeddings provide learned numerical representations used by the model.**

---

# Day 5 — AI Engineer Core Track

## Course transition

For Day 5, I progressed with:

**AI Engineer Core Track: LLM Engineering, RAG, QLoRA, Agents**

The course feels significantly more organized and structured than the previous learning approach.

The important change is that the learning is now following a more coherent progression instead of treating LLM, RAG, agents and related concepts as isolated topics.

### Progress

Completed:

- Day 1 content
- Day 2 content
- Associated hands-on exercises

The focus remains on building strong LLM engineering fundamentals before moving deeper into RAG, QLoRA and agents.

### Why the course structure is useful

The course is helping connect:

```text
Concept
  ↓
Understanding
  ↓
Hands-on implementation
  ↓
Engineering application
```

This is much more useful than simply learning terminology.

The objective is not just to know what an LLM concept means, but to understand:

- why it exists
- how it works
- how to implement it
- where it fits in an AI engineering architecture

---

# New Concept — Knowledge Distillation

One of the new concepts encountered was **knowledge distillation**.

The basic idea is:

> A smaller student model learns from a stronger/larger teacher model.

A simplified representation:

```text
                Large Teacher Model
                         │
                         │
              Generates useful outputs
              / synthetic training data
                         │
                         ▼
                Training Dataset
                         │
                         ▼
                 Smaller Student
                      Model
```

This can allow a smaller model to learn useful capabilities from a much larger model.

### Teacher → Student

Think of the two models as:

```text
Teacher
  = larger / stronger model
  = provides knowledge or training signals

Student
  = smaller model
  = learns from the teacher-generated information
```

This is different from simply saying:

> "Train a small model using lots of data."

The important mechanism is the **transfer of useful behavior or knowledge from the teacher to the student**.

### DeepSeek example

The course discussion connected this concept with the use of large-model-generated training data and smaller models.

The simplified mental model is:

```text
Large / capable model
        ↓
Generate high-quality examples
        ↓
Synthetic training dataset
        ↓
Train smaller model
        ↓
Smaller specialized model
```

The exact training recipes used by real-world models such as DeepSeek are more complex, so the above should be treated as the conceptual model rather than a complete description of a specific model's development.

---

# Why Distillation Matters for AI Engineering

Knowledge distillation introduces an important engineering trade-off:

```text
Large Model
    │
    ├── Higher capability
    ├── Higher compute requirements
    └── Higher inference cost
             │
             ▼
       Distillation
             │
             ▼
Smaller Model
    │
    ├── Lower compute requirements
    ├── Lower inference cost
    └── Potentially easier deployment
```

For an AI/Data Architect, this is important because model selection is not only about model quality.

It also involves:

- inference cost
- latency
- infrastructure requirements
- scalability
- deployment footprint
- task specialization
- model quality vs cost trade-offs

This will become increasingly relevant when designing production AI systems.

---

# Day 4 + Day 5 Mental Model

The learning is starting to move from the basic mechanics of LLMs toward how modern AI systems are engineered.

```text
                    LLM Engineering

                         │
                         ▼
                  Text / Prompts
                         │
                         ▼
                    Tokenization
                         │
                         ▼
                    Token IDs
                         │
                         ▼
                 Model Representations
                         │
                         ▼
                     LLM Inference
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Prompt Engineering      Model Adaptation
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                    Distillation            QLoRA
                         │
                         ▼
                  Smaller / Specialized
                       Models
```

The later stages will extend this toward:

```text
LLM
 ↓
RAG
 ↓
Tools / Function Calling
 ↓
Agents
 ↓
Evaluation
 ↓
Production AI Architecture
```

---

# Important Concepts to Revisit

## Day 4

- [ ] Token
- [ ] Tokenization
- [ ] Token ID
- [ ] Token ID vs embedding
- [ ] Token counting
- [ ] Python tokenizer experiment

## Day 5

- [ ] LLM engineering fundamentals
- [ ] Course structure and learning flow
- [ ] Hands-on implementation
- [ ] Knowledge distillation
- [ ] Teacher model
- [ ] Student model
- [ ] Synthetic training data
- [ ] Model capability vs inference cost

---

# Overall Progress

The biggest improvement from these two days is the shift from simply learning **LLM terminology** toward understanding the **engineering mechanics behind modern AI models**.

Day 4 established:

> **How text becomes something an LLM can process.**

Day 5 started establishing:

> **How model capabilities can be engineered, transferred and optimized.**

That is a strong foundation for the next stages of the AI Engineer Core Track.
