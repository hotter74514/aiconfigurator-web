# ADR-002: Asynchronous job API

## Context

Sweeps are too slow and variable for a reliable synchronous browser request. The assignment requires visible status and results when complete.

## Options Considered

- Synchronous `POST`: simple response shape, but fragile timeouts and poor failure UX.
- Job ID plus polling: stateless HTTP, simple client behavior, and appropriate for this scope.
- SSE/WebSockets: richer updates, but adds connection and lifecycle complexity for little value in seconds/minutes-long jobs.

## Proposed Decision

`POST /api/runs` returns `{id, status: "queued"}`. The client polls `GET /api/runs/{id}` about every two seconds until `completed` or `failed`. Completed responses include ranked results; failures include safe error details.

## What Would Change My Mind

Use SSE or WebSockets if users need fine-grained progress events or runs become long enough that polling load is material.

## Status

**Proposed — architecture owner approval required.**
