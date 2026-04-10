# ADR 003: NATS as Default Event Bus

## Status
Accepted

## Context
We need an event bus for decoupled communication between services (workflow events, connector responses, audit events). Options considered: Kafka, NATS, RabbitMQ, Redis Streams.

## Decision
Use NATS with JetStream as the default event bus.

## Rationale
- **Operational simplicity**: Single binary, no ZooKeeper/KRaft dependency (unlike Kafka)
- **JetStream**: Provides at-least-once delivery, message persistence, and consumer groups
- **Low latency**: Sub-millisecond publish latency for real-time workflow step coordination
- **Lightweight**: Minimal resource footprint for on-premises deployments
- **Kafka fallback**: For customers requiring Kafka (compliance, existing infrastructure), we support Kafka as an alternative event bus via adapter pattern

## Consequences
- Less ecosystem tooling than Kafka (monitoring, schema registry)
- Team must learn NATS JetStream consumer patterns
- Need to maintain Kafka adapter for enterprise customers who require it
