# Project Proposal: Enterprise Customer Intelligence Agent

## 1. Project Overview

### Working title

**Enterprise Customer Intelligence Agent**

### Subtitle

> A grounded AI analytics system for natural-language exploration of customer and marketing data.

### Purpose

Build a portfolio project that demonstrates the ability to design a reliable, enterprise-oriented AI analytics system—not merely a RAG chatbot or an LLM API demo.

The project should show how modern AI can be integrated with structured data, business definitions, deterministic analytics tools, and unstructured documents while maintaining reliability, traceability, security, and reasonable cost.

The intended audience is hiring managers and technical interviewers for roles such as:

- Senior / Lead Data Scientist
- Applied Data Scientist
- AI / Data Consultant
- AI Solutions / AI Transformation
- Data & AI Product roles
- Analytics / Decision Science leadership roles

---

## 2. Why This Project

My existing CV already demonstrates substantial experience in:

- customer analytics
- predictive modelling
- marketing analytics
- machine learning
- Google Cloud / TensorFlow
- automated data pipelines
- stakeholder-facing analytics
- real-time behavioural prediction

Therefore, this project should **not** simply demonstrate another conventional ML prediction model.

The primary capability gaps this project is intended to address are:

1. Modern GenAI / LLM application development
2. Tool-using AI agents
3. RAG and grounded generation
4. Natural-language-to-SQL analytics
5. AI evaluation
6. Reliability and validation
7. Enterprise AI system design
8. Security and responsible data access
9. Cost and latency considerations

The project should strengthen the career narrative:

> **Experienced enterprise data professional → modern AI / GenAI practitioner capable of designing reliable AI-enabled analytics systems.**

---

# 3. Business Scenario

Simulate a large hospitality / retail enterprise with customer and marketing data.

The organization has both structured and unstructured information.

## Structured data

Example entities:

- Customers
- Bookings
- Transactions
- Campaigns
- Campaign contacts
- Customer segments
- Products / properties

## Unstructured data

Example documents:

- Campaign briefs
- Customer research reports
- Business reports
- Product descriptions
- Management documents
- Business definitions

Business users should be able to ask questions in natural language without writing SQL.

Examples:

> "What was hotel booking revenue in 2025?"

> "Which customer segment had the largest year-over-year decline?"

> "What contributed most to the Q2 revenue decline?"

> "What is the company's definition of a VIP customer?"

> "Did Campaign A cause revenue to increase?"

The system should determine the appropriate analytical workflow rather than blindly asking an LLM to generate an answer.

---

# 4. Core Design Principle

The fundamental architecture is:

```text
                         ┌── SQL / Database
                         │
User question → Agent ───┼── Python Analytics
                         │
                         ├── Document Retrieval
                         │
                         └── Business Metadata
                                  ↓
                           Validation Layer
                                  ↓
                         Answer + Evidence
```

The LLM should primarily perform **orchestration and reasoning**.

It should not be treated as the source of truth for numerical results or business definitions.

A core design principle is:

> **Use deterministic tools whenever deterministic computation is sufficient; use LLM reasoning only where it adds value.**

Another core principle:

> **LLM-generated results should be validated by deterministic mechanisms wherever possible.**

---

# 5. Types of Questions

The system should intentionally support several classes of questions.

## Type A — Deterministic questions

Example:

> "What was revenue in 2025?"

Expected workflow:

```text
Question
   ↓
SQL
   ↓
Database
   ↓
Result
```

No unnecessary LLM reasoning should be introduced.

---

## Type B — Analytical questions

Example:

> "Why did booking revenue decline in Q2?"

Expected workflow may include:

```text
SQL
 ↓
Segment analysis
 ↓
Time-series comparison
 ↓
Contribution analysis
 ↓
Optional statistical analysis
 ↓
LLM-generated explanation
```

The final explanation must be grounded in the computed results.

---

## Type C — Knowledge questions

Example:

> "What is the definition of a VIP customer?"

Expected workflow:

```text
Question
 ↓
Retrieval
 ↓
Business definition
 ↓
Answer + citation
```

The system should provide evidence for the definition.

---

## Type D — Questions the system should not confidently answer

Example:

> "Did Campaign A cause revenue to increase?"

If the available data is observational and there is no appropriate randomized treatment/control design, the system should not claim causality.

Expected behaviour:

> The system should distinguish association from causal effect and explain what additional data or experimental design would be required to support a causal conclusion.

This is an important demonstration of analytical judgment.

---

# 6. Synthetic Data Strategy

No confidential company data will be used.

The project should use public and/or synthetic data.

The preferred approach is to create a coherent synthetic enterprise dataset rather than a collection of unrelated CSV files.

Possible schema:

```text
customers
---------
customer_id
market
segment
signup_date
...

bookings
--------
booking_id
customer_id
booking_date
hotel
room_type
revenue
...

transactions
------------
customer_id
date
category
amount
...

campaigns
---------
campaign_id
campaign_date
channel
segment
cost
...

campaign_contacts
-----------------
customer_id
campaign_id
contacted
...
```

The exact schema will be finalized during project specification.

---

# 7. Business Semantic Layer

A key component of the project should be a business semantic / metadata layer.

The LLM should not be expected to infer business definitions.

For example:

### active_customer

A customer with at least one qualifying transaction during the preceding 90 days.

### high_value_customer

A customer whose trailing-12-month contribution exceeds a defined threshold.

### booking_revenue

Gross booking revenue excluding cancellations.

Definitions should be explicit and accessible to the agent.

This component is important because enterprise analytics often depends as much on consistent business definitions as on SQL generation.

---

# 8. Proposed Architecture

Initial architecture:

```text
                         ┌──────────────────────┐
                         │        User          │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │    LLM / Agent       │
                         │    Orchestration     │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ↓                     ↓                     ↓
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │  SQL Tool   │       │ Python Tool │       │  RAG Tool   │
       └──────┬──────┘       └──────┬──────┘       └──────┬──────┘
              ↓                     ↓                     ↓
       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
       │  Database   │       │  Analytics  │       │  Documents  │
       └─────────────┘       └─────────────┘       └─────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Validation / Guardrail│
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ Answer + Evidence   │
                         └──────────────────────┘
```

The first version should use a **single well-designed agent**.

Multi-agent architecture should not be introduced unless experimentation demonstrates a clear benefit.

---

# 9. Validation and Reliability

Validation is one of the central features of the project.

## SQL validation

Before execution, validate:

- SQL syntax
- table existence
- column existence
- permitted operations
- permission scope
- query size / resource limits
- dangerous SQL operations

The system should initially restrict database access to read-only operations.

---

## Numerical validation

If the LLM produces:

> "Revenue increased by 23%."

The system should be capable of independently verifying:

```text
current revenue = 12.3M
previous revenue = 10.0M

growth = (12.3 - 10.0) / 10.0
       = 23%
```

The LLM should not be trusted to perform arithmetic when deterministic computation is available.

---

## Evidence validation

Claims in the final answer should be traceable to:

- database results
- calculations
- retrieved documents

The system should avoid unsupported claims.

---

# 10. Security and Responsible AI

Because the project is explicitly positioned as an enterprise system, basic security concerns must be addressed.

## Prompt injection

Retrieved documents may contain malicious or irrelevant instructions.

The agent must treat retrieved content as data, not as system-level instructions.

---

## SQL safety

The system should prevent destructive queries such as:

```text
DROP
DELETE
UPDATE
INSERT
ALTER
```

unless there is a deliberate future requirement to support them.

Initial scope should be read-only.

---

## Data access

The system should not expose unnecessary customer-level information.

For example, a business question such as:

> "How many VIP customers do we have?"

should not require passing every customer record to the LLM.

The architecture should favor aggregation and data minimization.

---

## Unsupported requests

The agent should refuse or redirect requests when:

- data does not exist
- the question cannot be answered reliably
- required permissions are unavailable
- the evidence does not support the claim

---

# 11. Evaluation Framework

Evaluation is a mandatory component.

The project should build a benchmark containing approximately **50–100 business questions**.

Questions should cover several categories:

### Simple SQL

> "What was revenue in 2025?"

### Analytical

> "Which market contributed most to the decline?"

### Multi-step

> "Which customer segment experienced the largest decline and what products drove it?"

### Knowledge retrieval

> "What is the definition of VIP?"

### Causal reasoning

> "Did Campaign A cause revenue to increase?"

### Adversarial / unsupported

> "Give me customer information that isn't in the database."

---

# 12. Evaluation Metrics

Potential metrics include:

## SQL correctness

Percentage of generated SQL queries that are semantically correct.

## Numerical correctness

Percentage of final numerical answers that match independently calculated results.

## Retrieval accuracy

Whether the correct supporting document appears in the top-k retrieved documents.

## Groundedness

Whether claims in the answer are supported by retrieved documents or computed results.

## Refusal accuracy

Whether the system correctly refuses questions that cannot be reliably answered.

## Latency

Measure:

- total response time
- SQL execution time
- retrieval time
- LLM generation time

## Cost

Track:

- input/output tokens
- estimated LLM cost
- cost per question

Exact target metrics should be established only after the baseline is implemented.

---

# 13. Baseline Comparison

The project should include at least one baseline.

## Baseline

A simple RAG / LLM approach with minimal tool use.

## Proposed system

Tool-using analytics agent with:

- SQL
- Python analytics
- semantic layer
- RAG
- validation
- guardrails

Compare both systems using the benchmark.

Potential evaluation table:

| Metric | Baseline | Proposed |
|---|---:|---:|
| SQL correctness | TBD | TBD |
| Numerical correctness | TBD | TBD |
| Retrieval accuracy | TBD | TBD |
| Groundedness | TBD | TBD |
| Correct refusal | TBD | TBD |
| Median latency | TBD | TBD |
| Estimated cost/query | TBD | TBD |

**Results must be measured rather than predetermined.**

---

# 14. Cost and Latency Optimization

The project should investigate whether every question needs the same level of LLM reasoning.

Possible routing:

```text
Simple SQL question
        ↓
Low-cost / deterministic path

Complex analytical question
        ↓
Stronger reasoning + Python

Knowledge question
        ↓
Retrieval-focused path
```

The objective is not simply maximum model capability.

The objective is:

> **appropriate capability at acceptable cost and latency.**

---

# 15. Failure Analysis

A dedicated section of the project should document what does not work.

Examples of questions to investigate:

- Does RAG actually improve structured analytics?
- Does multi-agent architecture improve accuracy enough to justify its complexity?
- Does a larger LLM materially improve results?
- How often does the agent generate semantically valid but business-invalid SQL?
- When does the agent hallucinate?
- When does it fail to refuse unsupported questions?
- What happens when data is missing?
- What happens when business definitions conflict?

The project should document:

1. observed failure
2. root cause
3. mitigation
4. residual limitation

This section is deliberately important because it demonstrates engineering judgment rather than only successful demos.

---

# 16. Project Deliverables

## GitHub repository

A clean, reproducible repository containing:

- source code
- configuration
- data generation / preparation
- evaluation framework
- tests
- documentation

---

## Architecture diagram

A clear system architecture showing:

- user
- agent
- tools
- database
- retrieval
- analytics
- validation
- output

---

## Evaluation report

Include:

- benchmark design
- metrics
- baseline
- results
- error analysis
- limitations

---

## Technical write-up

Target approximately 1,500–2,000 words.

Possible title:

> **Building a Reliable AI Analytics Agent for Enterprise Data**

Topics:

- problem framing
- architecture
- tool selection
- semantic layer
- retrieval
- validation
- security
- evaluation
- trade-offs
- lessons learned

---

## Demo

A 2–5 minute demonstration showing a realistic question progressing through:

```text
Question
   ↓
Agent reasoning / tool selection
   ↓
SQL
   ↓
Analytics
   ↓
Validation
   ↓
Answer
   ↓
Evidence
```

The demo should emphasize system behaviour rather than UI polish.

---

# 17. Scope Management

The project should be implemented in three stages.

## V1 — Working Prototype

Target: approximately 2–3 weeks.

Must include:

- synthetic enterprise dataset
- SQL tool
- basic RAG
- basic agent orchestration
- several representative questions
- basic answer generation

Goal:

> Demonstrate that the end-to-end concept works.

---

## V2 — Reliability

Target: approximately 2–3 weeks.

Add:

- business semantic layer
- evaluation benchmark
- SQL validation
- numerical validation
- grounded answers
- refusal behaviour
- failure analysis
- baseline comparison

Goal:

> Demonstrate that the system is reliable enough to be taken seriously.

---

## V3 — Production-oriented polish

Target: approximately 1–2 weeks.

Add:

- API
- Docker
- automated tests
- CI
- logging
- latency measurement
- cost tracking
- security controls
- improved documentation
- demo

Goal:

> Demonstrate production-oriented engineering judgment.

---

# 18. Explicit Non-Goals

To prevent scope creep, the first version will **not** attempt to build:

- a general-purpose autonomous agent
- a multi-agent framework without demonstrated need
- a full enterprise data warehouse
- a production-grade IAM system
- Kubernetes infrastructure
- dozens of microservices
- a highly polished frontend
- a general-purpose ChatGPT clone

Technical complexity should be introduced only when it supports a clearly demonstrated requirement.

---

# 19. What This Project Should Prove

At the end of the project, a hiring manager should be able to conclude:

> This candidate understands business analytics and machine learning, but is not limited to traditional predictive modelling.

> He understands how LLMs can interact with structured enterprise data and unstructured knowledge.

> He understands that LLM outputs cannot simply be trusted.

> He knows when deterministic computation is preferable to generative reasoning.

> He understands evaluation, failure modes, security, cost, and latency.

> He can build a coherent AI system rather than just a notebook or chatbot.

This is the intended value of the project.

---

# 20. Career Positioning

This project should support the following professional narrative:

> **Senior Applied Data Scientist with deep enterprise experience in customer analytics, predictive modelling and business decision-making, now extending that experience into modern AI systems and production-oriented GenAI applications.**

The project is therefore **not** intended to prove that I am an AI researcher.

It is intended to demonstrate that I can operate at the intersection of:

```text
Business
   +
Data Science
   +
Machine Learning
   +
Modern AI
   +
Enterprise Engineering
```

This positioning is more consistent with my existing experience and target roles.

---

# 21. Immediate Next Steps

Before writing significant production code, finalize the following:

1. Define the exact business scenario.
2. Define the synthetic data schema.
3. Define 10–15 representative user questions.
4. Categorize each question as:
   - SQL
   - analytical
   - RAG
   - multi-tool
   - unsupported / refusal
5. Define the minimum V1 architecture.
6. Select the technology stack.
7. Create the repository structure.
8. Implement the simplest end-to-end baseline.
9. Establish the evaluation benchmark.
10. Iterate toward V2 and V3 based on measured failures.

**The scope should be locked before implementation begins.**
