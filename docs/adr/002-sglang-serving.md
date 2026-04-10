# ADR 002: SGLang for Model Serving

## Status
Accepted

## Context
We need a high-performance inference runtime for serving open-weight models (Qwen3-30B-A3B, Phi-4-reasoning-vision-15B) with low latency and high throughput in enterprise deployments.

## Decision
Use SGLang as the model serving runtime.

## Rationale
- **Prefix caching**: Reduces latency for repeated prompt patterns (common in structured workflow outputs)
- **Continuous batching**: Maximizes GPU utilization across concurrent workflow executions
- **Multi-model support**: Serves both language and vision models from the same runtime
- **Performance**: Benchmarks show 2-5x throughput improvement over vLLM for structured generation tasks
- **Open-source**: No vendor lock-in, deployable in air-gapped environments

## Consequences
- Requires GPU infrastructure (minimum A100 40GB for Qwen3-30B-A3B)
- SGLang is newer and has a smaller community than alternatives
- Must maintain compatibility with SGLang API updates
