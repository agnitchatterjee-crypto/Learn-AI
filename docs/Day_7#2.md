# Day 7 — What Makes LLMs Work?

## Overview

Day 7 focused on the evolution of language models, the fundamentals of neural networks and LLMs, why Transformers replaced recurrent architectures for large-scale language modeling, scaling, tokens, emergent capabilities, and agentic AI.

---

## 1. Before Transformers — RNNs and LSTMs

Before Transformers, **Recurrent Neural Networks (RNNs)** were widely used for sequence-based problems such as language modeling.

### LSTM — Long Short-Term Memory

LSTM is a type of RNN designed to handle longer-term dependencies in sequences.

It uses gates to control:

- What information to retain
- What information to forget
- What new information to add

### Why Transformers replaced LSTMs for large-scale language modeling

It is not accurate to say that LSTMs were simply "more powerful" than Transformers.

The key limitation was **sequential computation**.

An RNN/LSTM processes tokens sequentially:

```text
Token 1 → Token 2 → Token 3 → Token 4 → ...
```

This makes it difficult to fully parallelize training.

Transformers introduced **attention**, allowing many tokens to be processed in parallel during training.

This made Transformers much easier to scale with modern GPU/TPU hardware.

### Key takeaway

> LSTMs were powerful sequence models, but their sequential nature limited parallelization and large-scale training. Transformers enabled much greater parallelism and became the dominant architecture for modern LLMs.

---

## 2. Machine Learning

Machine learning means that instead of explicitly programming every rule, we allow a model to **learn patterns from data**.

A simplified training loop:

```text
Training Data
     ↓
   Model
     ↓
 Prediction
     ↓
    Loss
     ↓
Backpropagation
     ↓
  Gradients
     ↓
Parameter Updates
     ↓
 Repeat
```

The objective is to find parameter values that minimize the loss.

### Parameters

Parameters can be thought of as the model's learned **"sliders"**.

During training:

```text
Parameters → adjusted repeatedly
```

During inference:

```text
Parameters → generally fixed
New input  → prediction
```

---

## 3. Neural Networks

A neural network can be thought of as many parameterized transformations stacked together.

Conceptually:

```text
Input
  ↓
Linear Transformation
  ↓
Activation Function
  ↓
Linear Transformation
  ↓
Activation Function
  ↓
...
  ↓
Output
```

Deep neural networks simply contain many layers of these transformations.

### Activation Functions / Non-Linearity

Activation functions introduce **non-linearity** into the network.

Without non-linear activation functions, stacking linear transformations would effectively still result in a linear transformation.

Non-linearity allows neural networks to learn much more complex relationships.

---

## 4. What Is an LLM?

LLM = **Large Language Model**

At a high level, an autoregressive LLM:

```text
Input
  ↓
Tokens
  ↓
Transformer
  ↓
Probability distribution
  ↓
Next token
  ↓
Append token to context
  ↓
Predict next token again
  ↓
Repeat
```

For example:

```text
"The capital of France is"
```

The model may assign a high probability to:

```text
Paris
```

The resulting context becomes:

```text
"The capital of France is Paris"
```

The model then predicts the next token.

### Important idea

The fundamental training objective is often:

> **Predict the next token.**

Despite the simplicity of this objective, sufficiently large models can learn surprisingly rich patterns from the training data.

---

## 5. Generative Models

A generative language model takes text represented as tokens and generates new tokens.

```text
Prompt
  ↓
Tokenization
  ↓
LLM
  ↓
Next-token prediction
  ↓
Generated token
  ↓
Repeat
```

This is why LLMs are called **generative** models.

They generate new sequences rather than simply classifying an existing input.

---

## 6. Pre-Training

A pre-trained language model is trained on very large datasets containing text.

During pre-training:

```text
Large Dataset
     ↓
Tokenization
     ↓
Model
     ↓
Next-token prediction
     ↓
Loss
     ↓
Backpropagation
     ↓
Parameter updates
```

The model repeatedly adjusts its parameters so that its predictions become better.

The resulting model has learned statistical patterns and representations from the training data.

---

## 7. Transformer Architecture

A **Transformer is a neural-network architecture**.

It is not synonymous with LLM.

Think of the relationship as:

```text
Transformer = Architecture

GPT = Model family

LLM = Large Language Model
```

Many modern LLMs are based on Transformer architectures.

### The key innovation: Attention

Attention allows the model to determine which parts of the context are relevant to the representation of a token.

For example:

```text
"The animal didn't cross the road because it was tired."
```

The model needs to understand what **"it"** refers to.

Attention allows information from relevant tokens to influence the representation of other tokens.

---

## 8. Why Transformers Scale So Well

The major practical advantage is **parallelization during training**.

### RNN / LSTM

```text
Token 1
   ↓
Token 2
   ↓
Token 3
   ↓
Token 4
```

### Transformer

Conceptually, multiple tokens can be processed together:

```text
Token 1 ─┐
Token 2 ─┤
Token 3 ─┼──→ Transformer
Token 4 ─┘
```

Attention then allows relationships between tokens to be modeled.

This architecture aligned extremely well with modern accelerator hardware and large-scale distributed training.

---

## 9. Scaling

A major development in modern AI has been the ability to scale:

- Number of parameters
- Training data
- Training compute
- Model architecture
- Inference compute

Conceptually:

```text
More Data
    +
More Compute
    +
More Parameters
    ↓
Larger / More Capable Models
```

The relationship is not simply "bigger is always better," but scaling has been a major driver of improvements in model capabilities.

---

## 10. Emergent Capabilities

A useful term is **emergent capabilities** rather than simply "emergent intelligence."

As models become sufficiently capable, they can demonstrate abilities such as:

- Few-shot learning
- Instruction following
- Coding
- Translation
- Mathematical problem solving
- Reasoning-like behavior
- Generalization to tasks not explicitly programmed as rules

There is ongoing research and debate around how to define and measure emergence. Some apparent capability jumps can depend strongly on the evaluation method.

### Key idea

> The model was not explicitly programmed with a separate rule for every capability. These behaviors can arise from learning complex patterns from large-scale data.

---

## 11. Memory Illusion / Context

An LLM does not necessarily have human-like memory.

During generation, previous tokens are included in the model's context.

Conceptually:

```text
User: My name is Bob.
        ↓
Assistant: Nice to meet you.
        ↓
User: What is my name?
        ↓
Previous conversation + new question
        ↓
LLM
        ↓
"Bob"
```

The model can use the previous tokens available in its context.

This creates the **appearance of memory**, but context, persistent memory, and model parameters are different concepts.

---

## 12. Training-Time vs Inference-Time Scaling

### Training-time scaling

More computation is spent during model training.

```text
More training compute
       ↓
Model learns more
```

This can involve increasing:

- Model size
- Dataset size
- Training tokens
- Training steps
- Compute

### Inference-time scaling

More computation is spent **while solving an individual problem**.

```text
User Question
     ↓
Reasoning / additional computation
     ↓
Final Answer
```

This is particularly important for modern reasoning-oriented models.

### Simple distinction

```text
Training-time scaling
→ Make the model better

Inference-time scaling
→ Give the model more compute when solving a problem
```

---

## 13. Tokens

LLMs operate on **tokens**, not directly on words or characters.

A token may represent:

- A complete word
- Part of a word
- Punctuation
- Whitespace
- Other frequently occurring text patterns

### Rules of thumb for English

```text
1 token ≈ 4 characters
1 token ≈ 0.75 words

1,000 tokens ≈ 750 English words
```

These are only approximations.

Token counts vary based on the tokenizer and content.

Token usage can be significantly different for:

- Code
- Mathematics
- URLs
- Rare words
- Non-English languages
- Technical terminology

### Why tokens matter

Tokens affect:

- Context-window usage
- API cost
- Latency
- RAG chunking
- Prompt design
- Model throughput

---

## 14. Agentic AI

Agentic AI goes beyond simply asking an LLM for a response.

An agentic system allows an LLM to participate in controlling a workflow.

A simplified architecture:

```text
                ┌───────────┐
                │    LLM    │
                └─────┬─────┘
                      │
                Decide action
                      │
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
      Search         SQL           API
        │             │             │
        └─────────────┼─────────────┘
                      ↓
                    Result
                      ↓
                     LLM
                      ↓
                Next action
```

An agent may:

1. Understand a goal
2. Decide what action to take
3. Use a tool
4. Observe the result
5. Decide what to do next
6. Continue until the goal is completed

This leads naturally into:

- Tool calling
- RAG
- LangChain
- LangGraph
- MCP
- Agent architectures

---

# Day 7 Mental Model

The evolution can be summarized as:

```text
RNN
 ↓
LSTM
 ↓
Transformer
 ↓
Large-scale Transformer
 ↓
LLM
 ↓
Reasoning Models
 ↓
Tool-using Systems
 ↓
Agentic AI
```

And the broader architecture:

```text
                 TRAINING
                    │
             Huge amounts of data
                    │
                    ↓
            Learn parameters
                    │
                    ↓
          ┌───────────────────┐
          │    Transformer    │
          │    Architecture   │
          │                   │
          │ Attention +       │
          │ Neural Networks   │
          └─────────┬─────────┘
                    │
                    ↓
                   LLM
                    │
             Predict next token
                    │
                    ↓
              Generate output
                    │
          ┌─────────┴─────────┐
          ↓                   ↓
         RAG                Tools
          │                   │
          └─────────┬─────────┘
                    ↓
               Agentic AI
```

---

# Key Takeaways

1. **LSTM** solved many problems with traditional RNNs but remained difficult to parallelize.
2. **Transformers** changed the game through attention and large-scale parallel training.
3. **Neural networks** learn parameters from data rather than relying entirely on explicitly programmed rules.
4. **Activation functions** introduce non-linearity and allow networks to learn complex relationships.
5. **LLMs** are trained to predict tokens and can generate text autoregressively.
6. **Pre-training** teaches the model statistical patterns and representations from massive datasets.
7. **Scaling** model size, data, and compute has been a major driver of modern AI capabilities.
8. **Emergent capabilities** describe abilities that become observable as models become sufficiently capable, although the exact nature of emergence is an active research topic.
9. **Inference-time scaling** means spending additional compute during problem solving rather than only during training.
10. **Tokens** are the fundamental units processed by LLMs and directly affect cost, context, latency, and throughput.
11. **Agentic AI** extends LLMs by giving them the ability to participate in multi-step workflows and use tools.

---

# Architecture Perspective

As a data engineer / architect, the important shift is to think beyond:

> "How do I call an LLM?"

toward:

> "How does the model work, where does the data flow, where does computation happen, and how do I architect a reliable system around it?"

That naturally leads into the next layer:

```text
LLM
 ↓
Prompt Engineering
 ↓
Embeddings
 ↓
Vector Search
 ↓
RAG
 ↓
Tool Calling
 ↓
Agents
 ↓
Evaluation
 ↓
Production AI Architecture
```

This is where AI engineering starts connecting directly with data engineering and architecture.
