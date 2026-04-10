# ADR 001: LangGraph for Workflow Orchestration

## Status
Accepted

## Context
We need a workflow orchestration framework that supports stateful multi-step execution with conditional routing, approval gates, and human-in-the-loop patterns. Options considered: Temporal, Prefect, custom state machine, LangGraph.

## Decision
Use LangGraph as the primary orchestration framework.

## Rationale
- **Stateful graphs**: Native support for typed state that flows through nodes, with conditional edges for branching logic
- **Approval gates**: Built-in support for interrupting execution and resuming after external events (human approval)
- **LLM-native**: Designed for AI agent workflows — integrates naturally with model calls, tool use, and structured output
- **Checkpointing**: Built-in state persistence for long-running workflows that survive service restarts
- **Composability**: Workflows can be composed as subgraphs, enabling reuse across different use cases

## Consequences
- Team must learn LangGraph API and state management patterns
- Vendor dependency on LangChain ecosystem (mitigated: LangGraph is relatively standalone)
- Complex workflows may need custom checkpointer implementation for Postgres persistence
