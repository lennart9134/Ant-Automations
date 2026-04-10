# ADR 004: Qwen3-30B-A3B as Planner Model

## Status
Accepted

## Context
The planner service needs a language model for action planning, tool selection, and structured output generation in enterprise workflows.

## Decision
Use Qwen3-30B-A3B as the primary planner model.

## Rationale
- **MoE architecture**: 30B total parameters but only 3B active per token — enables deployment on moderate GPU hardware (A100 40GB) while maintaining strong reasoning capability
- **Tool use**: Strong structured output and function-calling performance on enterprise benchmarks
- **Open-weight**: Apache 2.0 license, deployable in air-gapped environments without API dependencies
- **Multilingual**: Strong DACH/Benelux language support (German, Dutch, French) for our target market

## Consequences
- Requires A100 40GB minimum for full-precision inference
- Model updates require re-evaluation and potential prompt engineering changes
- Must benchmark against newer models quarterly
