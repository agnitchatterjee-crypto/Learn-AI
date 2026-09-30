# Day 6 — LLM Model Types & Transformer Architecture

## Overview

Today I focused on understanding the different types of LLMs, how modern models differ in their behavior, and the Transformer architecture that forms the foundation of most modern LLMs.

The main areas covered were:

- Base models
- Chat / Instruct models
- Reasoning / Thinking models
- Hybrid models
- Reasoning effort / reasoning budget
- Foundation models
- Major LLM families
- GPT and Transformer
- Attention and self-attention
- The "Attention Is All You Need" paper
- Why Transformers were important for scaling LLMs

---

## 1. Different Flavours of LLMs

LLMs can broadly be thought of as having different training objectives and behavioral characteristics.

### 1.1 Base Models

A base model is primarily trained to perform **next-token prediction**.

For example:

```text
Input:

"The capital of France is"

Prediction:

"Paris"
```

The model is actually predicting the next **token**, not necessarily the next word.

A simplified representation:

```text
Training Text
      ↓
Tokenization
      ↓
Token IDs
      ↓
Transformer
      ↓
Predict next token
      ↓
Compare with actual token
      ↓
Update model weights
```

Base models are useful as a foundation for further training.

They can be used for:

- Fine-tuning
- Domain adaptation
- Teaching specialized skills
- Continued pretraining

### Key takeaway

> A base model learns the statistical patterns of language primarily through next-token prediction. It is not necessarily optimized to follow user instructions or behave like a conversational assistant.

---

# 2. Chat / Instruct Models

Chat or instruction-tuned models are generally built from pretrained models and then undergo additional **post-training** to make them better at following instructions and interacting with users.

A simplified pipeline is:

```text
Pretraining
    ↓
Base Model
    ↓
Instruction Tuning
    ↓
Preference / Alignment Training
    ↓
Chat / Instruct Model
```

One important technique historically used for this is:

**RLHF — Reinforcement Learning from Human Feedback**

However:

> Chat/Instruct models should not be equated with RLHF.

Modern models can use multiple post-training and preference-optimization techniques.

### Why are Chat/Instruct models useful?

They are optimized for tasks such as:

- Conversational interaction
- Following instructions
- Question answering
- Summarization
- Content generation
- Coding assistance
- Tool interaction

---

# 3. Reasoning / Thinking Models

Reasoning-oriented models are designed to spend additional computation on difficult problems before producing the final answer.

A simplified representation:

```text
Problem
   ↓
Additional reasoning / computation
   ↓
Solution
   ↓
Final response
```

They are particularly useful for tasks involving:

- Mathematics
- Complex coding
- Multi-step reasoning
- Planning
- Complex analysis
- Problems where a quick response may not be sufficient

### Important distinction

A reasoning model does **not necessarily expose its actual internal chain-of-thought** to the user.

Therefore:

> Reasoning model ≠ model that simply prints its thinking steps before the answer.

The important concept is the **additional computation performed during inference**.

---

# 4. Chat vs Reasoning Models

A useful high-level comparison is:

| Model Type | Typical Strength |
|---|---|
| Base | Starting point for additional training |
| Chat / Instruct | Interactive applications and instruction following |
| Reasoning | Complex multi-step problem solving |

There are trade-offs.

Reasoning-oriented inference can require more computation, which can increase:

- Latency
- Cost
- Compute consumption

Chat-oriented models may be preferable when fast interactive responses are more important.

The appropriate model therefore depends on the workload rather than one model type always being better.

---

# 5. Hybrid Models

Modern LLMs increasingly blur the boundaries between traditional chat and reasoning models.

A hybrid model can support:

```text
User
  ↓
Model
  ├── Direct response
  │
  └── Deeper reasoning when required
```

This allows the system to balance:

- Response speed
- Reasoning depth
- Cost
- Problem complexity

The important architectural concept is that **model behavior is no longer simply "chat model vs reasoning model."**

---

# 6. Reasoning Effort / Reasoning Budget

Some modern reasoning systems allow different amounts of inference-time computation.

This can be thought of as a **reasoning budget** or **reasoning effort**.

Conceptually:

```text
Lower reasoning effort
        ↓
Less computation
        ↓
Faster / potentially cheaper


Higher reasoning effort
        ↓
More computation
        ↓
Slower / potentially more expensive
        ↓
More opportunity to solve complex problems
```

This is an example of **inference-time compute**.

### Important idea

Traditionally, improving model capability often focused heavily on:

```text
More training data
        +
Larger model
        +
More training compute
```

Modern reasoning approaches also explore:

```text
More compute at inference time
```

This is an important concept to understand before moving deeper into reasoning models and agentic AI.

---

# 7. Foundation Models vs Large Models

These terms are related but not identical.

### Large Model

Generally describes the **scale** of a model.

### Foundation Model

Describes a model trained on broad data at scale that can serve as a foundation for many downstream applications and tasks.

Therefore:

> A foundation model can be large, but "large model" and "foundation model" are not synonyms.

---

# 8. Major LLM Families

Some major model families include:

| Organization | Model Family |
|---|---|
| OpenAI | GPT |
| Anthropic | Claude |
| Google | Gemini |
| xAI | Grok |
| DeepSeek AI | DeepSeek |
| Alibaba | Qwen |

These organizations may offer multiple models within their respective families, with different trade-offs around:

- Capability
- Speed
- Cost
- Context window
- Reasoning
- Multimodal capabilities
- Deployment options

---

# 9. What does GPT mean?

GPT stands for:

> **Generative Pre-trained Transformer**

Breaking this down:

### Generative

The model generates new output.

### Pre-trained

The model is trained on large datasets before being adapted for specific behaviors or applications.

### Transformer

The model uses the Transformer neural network architecture.

```text
GPT
 │
 ├── Generative
 ├── Pre-trained
 └── Transformer
```

---

# 10. What is a Transformer?

The Transformer is a neural network architecture introduced in the 2017 research paper:

> **"Attention Is All You Need"**

The paper was authored by researchers at Google and the University of Toronto.

The Transformer architecture introduced a powerful way of processing sequences using **attention mechanisms**, particularly **self-attention**.

---

# 11. Before Transformers

Before Transformers, sequence-processing systems commonly relied on architectures such as:

- RNNs — Recurrent Neural Networks
- LSTMs — Long Short-Term Memory networks
- GRUs — Gated Recurrent Units

A simplified view of recurrent processing:

```text
Token 1
   ↓
Token 2
   ↓
Token 3
   ↓
Token 4
```

This sequential nature made it harder to efficiently process very long sequences and take advantage of large-scale parallel computation.

---

# 12. Attention

The key idea behind attention is:

> **Which parts of the input should the model pay attention to when processing a particular token?**

Consider:

```text
"The animal didn't cross the road because it was tired."
```

When processing the word:

```text
"it"
```

the model needs to understand relationships between different parts of the sentence.

Attention allows the model to assign different levels of importance to different tokens.

---

# 13. Self-Attention

Self-attention allows tokens within the same sequence to interact with one another.

Conceptually:

```text
Input sequence

Token 1 ───────┐
Token 2 ───────┤
Token 3 ───────┼──→ Self-Attention
Token 4 ───────┤
Token 5 ───────┘
```

Instead of processing each token completely independently, the model can determine how strongly different tokens relate to each other.

A simplified question the model is effectively answering is:

> "Given the token I am processing, which other tokens in the sequence are relevant?"

---

# 14. Transformer Architecture

A simplified Transformer block can be represented as:

```text
Input Tokens
     ↓
Token Embeddings
     ↓
Positional Information
     ↓
Self-Attention
     ↓
Feed Forward Network
     ↓
Output
```

Modern LLMs contain many Transformer layers stacked together.

```text
Input
  ↓
Transformer Layer
  ↓
Transformer Layer
  ↓
Transformer Layer
  ↓
...
  ↓
Transformer Layer
  ↓
Output
```

Each layer progressively transforms the representation of the input.

---

# 15. Why Transformers Were Important

The Transformer was not simply an optimization of an existing model.

It was a **new neural network architecture based heavily on attention** that provided important advantages for sequence modeling.

One major advantage was improved ability to take advantage of **parallel computation during training** compared with recurrent architectures.

This helped make it practical to train increasingly large models on increasingly large datasets.

A simplified evolution is:

```text
Neural Networks
       ↓
Deep Learning
       ↓
Sequence Models
       ↓
Attention
       ↓
Transformer
       ↓
Large-scale Pretraining
       ↓
Foundation Models
       ↓
Instruction / Preference Post-training
       ↓
Chat + Reasoning Models
```

---

# 16. Important Architectural Distinction

One of the most important things I learned today is that several concepts that are often mixed together are actually different layers of the AI stack.

```text
                    AI MODEL STACK

┌─────────────────────────────────────┐
│ Application / Agent                 │
├─────────────────────────────────────┤
│ Chat / Reasoning Behavior           │
├─────────────────────────────────────┤
│ Post-training / Alignment           │
├─────────────────────────────────────┤
│ Pretraining                         │
├─────────────────────────────────────┤
│ Transformer Architecture            │
├─────────────────────────────────────┤
│ Neural Network                      │
└─────────────────────────────────────┘
```

For example:

**Transformer** is an architecture.

**Pretraining** is a training stage.

**RLHF / preference optimization** are post-training approaches.

**Chat** describes a model's interaction behavior.

**Reasoning** describes a model's ability/strategy to perform additional computation for difficult problems.

These concepts should not be treated as interchangeable.

---

# 17. Key Takeaways

### 1. Base model

> Primarily trained for next-token prediction and can serve as a starting point for further training.

### 2. Chat / Instruct model

> A pretrained model that has undergone additional post-training to improve instruction following and interaction.

### 3. Reasoning model

> A model designed to use additional computation to improve performance on complex problems.

### 4. Reasoning budget

> The amount of inference-time computation allocated to reasoning.

### 5. Foundation model

> A broadly trained model that can serve as a foundation for many downstream applications.

### 6. Transformer

> A neural network architecture based heavily on attention and self-attention that became foundational to modern LLMs.

### 7. GPT

> Generative Pre-trained Transformer.

---

# 18. My Current Mental Model

My current understanding can be summarized as:

```text
                     LLM
                      │
          ┌───────────┴───────────┐
          │                       │
    Transformer              Training
    Architecture                │
          │             ┌────────┴────────┐
          │             │                 │
          │        Pretraining       Post-training
          │             │                 │
          │          Base model      Instruct / Chat
          │                               │
          │                          Reasoning /
          │                           Hybrid
          │
          └──────────────┬────────────────┘
                         │
                  AI Applications
                         │
              ┌──────────┼──────────┐
              │          │          │
             RAG       Agents     Copilots
```

The biggest takeaway from Day 6 is that an LLM is not just "a chatbot."

There is a stack underneath it:

**architecture → pretraining → post-training → inference strategy → application.**

Understanding these layers will be important as I move into fine-tuning, RAG, agents and eventually AI system architecture.
