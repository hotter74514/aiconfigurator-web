# ADR-015: Frontend UI refresh without a new runtime stack

## Context

The Portal already completes the assignment journey through one server-rendered
Jinja2 page with browser-native CSS and JavaScript. It submits the existing run
request, polls status, renders ranked estimates and the Pareto visualization,
loads bounded local history, and downloads allow-listed artifacts. The page is
functional, but its flat visual hierarchy and dense presentation make the main
serving decision harder to scan during the demo.

The requested refresh should use a well-adopted frontend-design skill to guide
intentional visual choices. The skill is authoring guidance, not a product
runtime requirement. Adopting it must not silently introduce a JavaScript
framework, package manager, remote asset dependency, new API contract, or a
second service. The estimate warning, failure states, accessibility semantics,
and explicit local-history limitations remain part of the product contract.

## Options Considered

### A. Apply `anthropics/skills` `frontend-design` to the existing page

Use the skill during design and implementation, record the upstream revision
used, and keep the deployed Portal as server-rendered Jinja2 with native CSS and
JavaScript. Reshape the existing page into a responsive serving-decision
console, establish a small CSS token system, and improve hierarchy, focus
states, status treatments, tables, and charts without changing their data or
behavioral contracts.

This has the lowest implementation and demo risk. Existing page-contract tests
remain useful, browser checks can cover responsive and visual behavior, and the
container has no additional runtime dependency. The main drawback is that the
single template remains relatively large; aggressively splitting or replacing
it during a visual milestone would create unrelated integration work.

### B. Adopt `ux-atelier` as a prototype and design-handoff workflow

Create the refreshed interface in Atelier's source/partial structure, use its
preview and handoff flow, then translate the approved output into the Portal.
This supports iterative designer handoff and repeatable prototype builds, but it
adds a parallel source format, hooks, generated output, and a translation step
for a one-page take-home. Prototype and production markup can drift, and the
extra workflow increases operability and demo risk without improving the Portal
runtime.

### C. Migrate to a component framework and UI system

Introduce a client framework and design system such as React with Tailwind or
shadcn, or Tonic One, and rebuild the page as components. This offers stronger
component boundaries if the Portal grows into a multi-page product. It also
adds Node tooling, dependency and asset management, a frontend build artifact,
new test seams, container integration, and client/server lifecycle complexity.
Those costs are disproportionate to the current single-page assignment and
create more ways for the offline local demo to fail.

## Proposed Decision

Choose Option A.

- Use the `frontend-design` skill only as development-time authoring guidance.
  Read the complete skill before implementation and record the upstream source
  revision in the implementation report. Do not package the skill or its tools
  in the Portal image.
- Keep FastAPI, Jinja2, browser-native CSS, and browser-native JavaScript. Do
  not add `package.json`, a frontend bundler, a component framework, a CSS
  framework, or a new static-asset pipeline for this refresh.
- Keep the existing HTTP endpoints, request and result schemas, polling
  interval, artifact paths, run-history behavior, and DOM hooks used by current
  JavaScript and tests. Presentation changes must not alter run semantics.
- Use a subject-specific "Serving Decision Console" direction: the submitted
  constraints and the highest-value result comparison form the primary visual
  structure, while the Pareto chart, ranked table, artifacts, and recent local
  history retain their current meaning. Avoid decorative card repetition or
  animation that competes with the decision data.
- Keep the page self-contained at runtime. Do not fetch fonts, icons, scripts,
  styles, or telemetry from a CDN. Prefer a deliberate system-font stack for
  this milestone; adding bundled fonts or other assets requires evidence that
  the visual benefit justifies a static-serving change.
- Preserve the prominent estimate warning and its benchmark-validation meaning
  governed by ADR-010. Do not make predicted output look like a verified
  deployment guarantee.
- Treat responsive behavior and accessibility as acceptance criteria: support
  narrow mobile through desktop layouts, contain wide-table overflow, provide
  visible keyboard focus, avoid color-only status communication, maintain
  readable contrast, and respect `prefers-reduced-motion` if motion is used.
- Verify loading, queued, running, failure, completion, empty-history, expired
  artifact, long-value, and populated-result states. Retain unit/page contract
  tests and add browser-based viewport and keyboard checks. Run the existing
  container and demo path because the page is delivered by the production
  image.

## Trade-offs and Failure Modes

- CSS-only restructuring can create mobile overflow, inaccessible focus order,
  or unreadable dense tables. Test representative viewport widths and keyboard
  traversal instead of relying only on HTML string assertions.
- A visually strong result panel can accidentally obscure the submit state,
  estimate warning, or local-retention limitation. Those messages remain
  explicit acceptance criteria and must be reviewed in every terminal state.
- Skill guidance may favor visual novelty over assignment clarity. The product
  goal, real content, accessibility, and reliable demo behavior override any
  aesthetic suggestion from the skill.
- An upstream skill can change after selection. Recording the source revision
  makes the authoring input inspectable; popularity alone is not a trust or
  architecture guarantee.
- Keeping CSS and JavaScript in the current template limits modularity. This is
  accepted for the one-page milestone to avoid introducing a new asset boundary
  during a cosmetic refresh.
- Browser-native behavior can vary slightly across platforms. The implementation
  should use progressive CSS, functional fallbacks, and no browser-specific
  feature as the only way to submit or interpret a run.

## What Would Change My Mind

Adopt a small static-asset split when repeated styles or scripts appear across
multiple server-rendered pages and the benefit outweighs the added route and
packaging checks. Adopt a component framework when the Portal gains sustained
multi-page navigation, shared interactive components, or a team-supported
frontend build pipeline. Choose Tonic One or another mandated design system
when organizational brand compliance becomes a requirement. Choose Atelier
when a recurring designer-to-engineer prototype and handoff process, rather
than a single implementation refresh, becomes part of the product workflow.

## Status

**Accepted — architecture owner approval recorded on 2026-09-08.**
