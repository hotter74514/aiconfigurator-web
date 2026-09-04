# ADR-003: CLI subprocess integration

## Context

AIConfigurator provides a CLI and Python SDK. The portal needs an explicit boundary around a CPU-heavy third-party computation engine.

## Options Considered

- Python SDK: structured and low process overhead, but couples the web process to SDK internals and failure behavior.
- CLI subprocess: process isolation, explicit exit status, timeout/termination control, and captured stdout/stderr; requires output parsing.

## Proposed Decision

Invoke the AIConfigurator CLI from a bounded worker subprocess and normalize its output into the portal’s result model. Keep the command construction and parser behind one adapter.

## What Would Change My Mind

Move to the SDK when it exposes a stable structured API and execution runs in dedicated worker containers where process coupling is no longer a concern.

## Status

**Proposed — architecture owner approval required.**
