# ADR-010: Treat results as estimates

## Context

AIConfigurator predicts performance from measured primitives; it is not a substitute for representative production benchmarking.

## Proposed Decision

Show a prominent warning beside ranked results and downloaded artifacts: predictions are model-based estimates and must be validated with real benchmarks before deployment. Include the limitation in README and the demo explanation.

## Alternatives and Trade-offs

Hiding the warning makes the UI more authoritative but is misleading. A warning adds minimal implementation cost and protects user interpretation without blocking the demo.

## What Would Change My Mind

Only evidence that the upstream tool provides a stronger validated guarantee would change the wording; it would not remove the need for benchmark validation.

## Status

**Proposed — architecture owner approval required.**
