# Day 7 — How LLMs Learn, Parameters, Scaling & Tokens

## 1. Core Learning: How Neural Networks Learn

A neural network is a collection of mathematical computation units (often called neurons) arranged in layers and containing learned parameters such as weights and biases.

A simplified neuron:

```text
Inputs
  │
  ├── x1 ── × w1 ──┐
  ├── x2 ── × w2 ──┤
  ├── x3 ── × w3 ──┤──► weighted sum + bias
  └── ...          │
                   ▼
              activation
                   ▼
                 output
```

Mathematically:

```text
z = w1*x1 + w2*x2 + ... + b
output = activation(z)
```

### Important terminology

| Concept | Meaning |
|---|---|
| Neuron | A small mathematical computation unit |
| Weight | A learned parameter |
| Bias | Another learned parameter |
| Activation function | Introduces non-linearity into the network |
| Layer | Collection of computation units |
| Neural network | Multiple layers of interconnected computation units |
| Parameter | Numerical value learned during training |
| Algorithm | A procedure used to perform a task, such as optimization |

A neuron is **not itself an algorithm**. It is a mathematical computation unit.

---

# 2. What Are Model Parameters?

Parameters are numerical values that the model learns during training.

They are not manually configured.

A model might contain billions or even trillions of parameters.

Do not think of parameters as explicit facts:

```text
parameter_1 = "Paris is the capital of France"
parameter_2 = "Python uses indentation"
```

Instead, parameters are numerical values contained in large matrices/tensors.

For example:

```text
W =
[
  0.21  -0.73
  0.44   0.18
]
```

Individual parameters generally do not have a human-readable meaning.

The useful behavior emerges from the **configuration of many parameters working together**.

---

# 3. Are Initial Parameter Values Random?

Yes, approximately.

When a neural network is first created, its parameters are initialized using carefully chosen random distributions.

They are not simply assigned completely arbitrary numbers.

Initialization methods are designed to keep activations and gradients numerically stable.

Examples include:

- Xavier / Glorot initialization
- He initialization

Conceptually:

```text
Initial parameters
      ↓
mostly random values
      ↓
Training
      ↓
parameters gradually adjusted
      ↓
useful representations and capabilities
```

Nobody manually decides what each parameter should become.

---

# 4. How Are Parameters Automatically Updated?

This is the central training loop.

```text
Training data
      ↓
Forward pass
      ↓
Prediction
      ↓
Loss calculation
      ↓
Backpropagation
      ↓
Gradients
      ↓
Optimizer
      ↓
Parameter update
      ↓
Next training batch
```

This process is repeated many millions/billions of times during large-scale model training.

---

# 5. Loss Function

The **loss function** measures how wrong the model's prediction was.

For a language model, the training objective is fundamentally next-token prediction.

Example:

```text
Input:
"The capital of France is"

Expected next token:
"Paris"
```

If the model assigns:

```text
Paris  → 12%
London → 35%
Berlin → 8%
...
```

the model receives a relatively high loss because its probability for the correct token was too low.

The loss is therefore a numerical signal representing prediction error.

---

# 6. Backpropagation

Backpropagation is the process used to calculate how the loss changes with respect to the model's parameters.

It uses the **chain rule of calculus**.

Conceptually:

```text
Loss
  ↑
Layer 3
  ↑
Layer 2
  ↑
Layer 1
```

For every parameter, the system calculates something like:

```text
∂Loss / ∂Parameter
```

This tells us how sensitive the loss is to that parameter.

---

# 7. What Is a Gradient?

A gradient is **not an algorithm**.

It is a mathematical quantity representing the direction and magnitude of change in the loss with respect to parameters.

For example:

```text
parameter w = 5

Loss = (w - 3)^2

dLoss/dw = 2(w - 3)

At w = 5:

gradient = 4
```

The gradient tells the optimizer which direction to move the parameter to reduce the loss.

So:

```text
Loss function
     ↓
calculates loss

Backpropagation
     ↓
calculates gradients

Optimizer
     ↓
uses gradients to update parameters
```

---

# 8. Optimizer

The optimizer is the algorithm that uses gradients to update parameters.

A simplified gradient descent update:

```text
new_parameter =
    old_parameter - learning_rate × gradient
```

Example:

```text
old parameter = 5
gradient      = 4
learning rate = 0.1

new parameter = 5 - (0.1 × 4)
              = 4.6
```

Modern LLM training commonly uses optimizers such as Adam/AdamW rather than plain gradient descent.

---

# 9. The Complete Learning Loop

```text
                TRAINING
                   │
                   ▼
        Training dataset / batch
                   │
                   ▼
             Forward pass
                   │
                   ▼
              Prediction
                   │
                   ▼
             Loss function
                   │
                   ▼
             Backpropagation
                   │
                   ▼
                Gradients
                   │
                   ▼
               Optimizer
                   │
                   ▼
          Updated parameters
                   │
                   └──────────────► next batch
```

The critical insight:

> The parameters are not manually tuned. Mathematical optimization automatically adjusts them to reduce the training loss.

---

# 10. Why Do More Parameters Often Mean More Capability?

"More parameters = more intelligence" is an oversimplification.

A better statement is:

> More parameters give a model greater capacity to represent complex functions and patterns, provided the model is trained with sufficient data and compute.

Think of parameters as adjustable capacity.

A very small model has limited ability to represent complex relationships.

A larger model can potentially represent:

- syntax
- grammar
- semantics
- relationships between concepts
- code patterns
- statistical relationships
- more complex transformations

However:

```text
More parameters
≠
Automatically better model
```

The model also needs:

```text
model capacity
+
training data
+
training compute
+
appropriate architecture
+
effective optimization
```

There are also diminishing returns and efficiency improvements.

---

# 11. Where Are the Parameters in a Transformer?

A Transformer contains many large matrices/tensors.

A simplified Transformer layer:

```text
                 Transformer Layer
                       │
          ┌────────────┴────────────┐
          │                         │
      Attention               Feed Forward
          │                         │
      Q / K / V                  W1 / W2
```

### Embeddings

A model has a vocabulary and an embedding dimension.

For example, if:

```text
Vocabulary = 100,000 tokens
Embedding dimension = 12,288
```

then an embedding matrix contains:

```text
100,000 × 12,288
= 1.2288 billion parameters
```

Conceptually:

```text
"cat"      → [0.12, -0.43, 0.77, ...]
"dog"      → [0.18, -0.39, 0.71, ...]
"database" → [-0.21, 0.83, 0.11, ...]
```

These vectors are learned during training.

### Attention

The model uses learned matrices for:

```text
Q = Query
K = Key
V = Value
```

Conceptually:

```text
Q = X × WQ
K = X × WK
V = X × WV
```

`WQ`, `WK` and `WV` are learned parameter matrices.

### Feed-forward network

A simplified feed-forward component:

```text
X
 ↓
X × W1
 ↓
activation
 ↓
X × W2
 ↓
output
```

These matrices can contain a very large number of parameters.

A large Transformer is therefore essentially a huge collection of learned tensors.

---

# 12. Parameters Do Not Equal Explicit Memories

This is an important mental model.

The model does not normally store:

```text
parameter #123456 = "France's capital is Paris"
```

Instead, training changes many parameters across many layers.

The learned behavior is distributed across the network.

Therefore:

> Knowledge in an LLM is generally represented as distributed numerical patterns rather than one parameter per fact.

This is also why fine-tuning changes model behavior by modifying parameters rather than manually inserting individual facts.

---

# 13. Token IDs vs Embeddings

A token ID is simply an identifier.

Example:

```text
"The" → 791
```

The number `791` does not inherently mean anything.

The model uses the token ID to retrieve a learned embedding:

```text
Token ID
   791
    ↓
Embedding lookup
    ↓
[0.021, -0.183, 0.442, ...]
    ↓
Transformer
```

Important distinction:

```text
Token ID
    =
identifier

Embedding
    =
learned numerical representation
```

---

# 14. LLM: Generative + Pre-trained

A useful simplified definition:

### Generative

Input:

```text
tokens / prompt
```

Output:

```text
prediction of the next token
```

The model generates text one token at a time.

### Pre-trained

Before being used as a chatbot, the model has been trained on a very large corpus of data.

During pre-training:

```text
training data
    ↓
next-token prediction
    ↓
loss
    ↓
backpropagation
    ↓
gradient
    ↓
parameter update
```

The parameters are gradually tuned until the model becomes very good at predicting the statistical patterns in language and other training data.

---

# 15. Training-Time Scaling vs Inference-Time Scaling

## Training-time scaling

Training is about **learning the parameters**.

Important dimensions include:

- model size / parameter count
- number of training tokens
- training steps
- training compute
- architecture
- optimization

Conceptually:

```text
Training data
      +
Model capacity
      +
Compute
      ↓
Optimization
      ↓
Learned model
```

The expensive training loop repeatedly performs:

```text
forward pass
     ↓
loss
     ↓
backpropagation
     ↓
gradient calculation
     ↓
parameter update
```

---

## Inference-time scaling

Inference happens after training.

The parameters are normally fixed.

```text
User prompt
     ↓
Tokenization
     ↓
Embeddings
     ↓
Transformer
     ↓
Next-token probabilities
     ↓
Selected next token
     ↓
Token added to context
     ↓
Repeat
```

Inference therefore consumes compute to **use** the learned parameters rather than update them.

---

# 16. Inference-Time Compute

Inference-time scaling can also mean deliberately spending more computation during inference.

For example, reasoning-oriented models may use additional computation to work through a difficult problem before producing the final answer.

Conceptually:

```text
Normal inference:

Prompt
  ↓
Computation
  ↓
Answer


More inference-time compute:

Prompt
  ↓
More internal computation
  ↓
Evaluate / refine
  ↓
Answer
```

This is an important modern LLM concept because performance improvements don't have to come only from making the model larger.

---

# 17. Token Counting

Useful rule of thumb for typical English prose:

```text
1 token ≈ 4 characters
1 token ≈ 0.75 words
1 word ≈ 1.3 tokens
1,000 tokens ≈ 750 words
```

These are approximations, not fixed conversions.

Token count can be significantly higher for:

- source code
- mathematics
- scientific terminology
- URLs
- unusual names
- numbers
- punctuation-heavy text
- some non-English languages

For example:

```text
1,000 tokens of English prose
```

can represent substantially more human-readable content than:

```text
1,000 tokens of Python/code
```

---

# 18. Important Mental Model

The overall picture:

```text
                     TRAINING
                        │
                        ▼
                 Training tokens
                        │
                        ▼
                  Transformer
                        │
                        ▼
                   Prediction
                        │
                        ▼
                      Loss
                        │
                        ▼
                 Backpropagation
                        │
                        ▼
                    Gradients
                        │
                        ▼
                    Optimizer
                        │
                        ▼
              Updated parameters
                        │
                        ▼
                 Trained LLM
                        │
                        │
                        ▼
                    INFERENCE
                        │
                        ▼
                    User prompt
                        │
                        ▼
                     Tokens
                        │
                        ▼
                  Transformer
                        │
                        ▼
                Next-token distribution
                        │
                        ▼
                  Next token
                        │
                        └──────► repeat
```

## Key takeaways from Day 7

1. **Parameters are learned numerical values, not manually configured settings.**
2. **Initial parameters are typically randomly initialized using controlled initialization schemes.**
3. **The loss function measures prediction error.**
4. **Backpropagation calculates gradients using the chain rule.**
5. **A gradient is a mathematical quantity, not an algorithm.**
6. **An optimizer uses gradients to update parameters.**
7. **More parameters provide greater representational capacity, but more parameters alone do not guarantee better intelligence.**
8. **Transformer parameters live primarily in large learned matrices/tensors such as embeddings, attention projections and feed-forward layers.**
9. **Knowledge is distributed across many parameters rather than stored as one explicit fact per parameter.**
10. **Training changes parameters; inference normally does not.**
11. **Token IDs are identifiers; embeddings are learned vector representations.**
12. **Token count is a practical measure of LLM input/output and compute requirements.**
13. **Training-time scaling and inference-time scaling are different concepts.**
14. **Modern reasoning models can use additional inference-time computation to improve performance on difficult tasks.**

## Questions to Carry Forward

- How exactly does backpropagation use the chain rule?
- What is a derivative and how does it become a gradient?
- How does attention actually calculate relationships between tokens?
- What exactly are Query, Key and Value?
- Why does self-attention work better for Transformers than sequential recurrence?
- How does a Transformer process an entire sequence in parallel?
- How does the model convert the final representation into probabilities for the next token?
