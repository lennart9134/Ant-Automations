# ADR 005: Phi-4-reasoning-vision-15B as Vision Model

## Status
Accepted

## Context
The platform needs vision capabilities for document classification, form extraction, and visual content understanding in enterprise workflows.

## Decision
Use Phi-4-reasoning-vision-15B as the vision model.

## Rationale
- **Compact**: 15B parameters fits on a single A10G or RTX 4090, reducing deployment cost
- **Reasoning**: Strong chain-of-thought performance on document understanding tasks
- **Enterprise documents**: Good performance on forms, tables, diagrams, and scanned documents
- **Open-weight**: MIT license, deployable in air-gapped environments

## Consequences
- May need larger model for complex document layouts (upgrade path: larger Phi or Qwen-VL variants)
- Vision inference is slower than text-only — budget for additional latency in workflows
- Must validate accuracy on customer-specific document types during pilot
