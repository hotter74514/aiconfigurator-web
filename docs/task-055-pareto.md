# BONUS-001 Pareto Frontier Visualization

## Scope

The completed results view now includes a browser-rendered SVG scatter plot.
Each candidate is plotted using predicted request latency on the x-axis and
predicted throughput on the y-axis. A candidate is on the Pareto frontier when
no other candidate is at least as fast and at least as high-throughput, with
one strict improvement. Frontier points and the connecting line are blue;
dominated candidates are gray.

The existing ranked table remains the authoritative display for SLA status,
ranking, backend, system, and the full candidate set. The visualization is an
explanation aid only: AIConfigurator values are still estimates and must be
validated with representative benchmarks before deployment.

## Implementation

- No new runtime or frontend dependency was added.
- The chart is rendered with native SVG and DOM APIs in `templates/form.html`.
- Point titles, ARIA labels, axis labels, a legend, and a text frontier summary
  provide keyboard and assistive-technology context.
- Invalid or empty plot data is rejected by the existing completed-run error
  handling, and a new submission clears the previous chart.

## Verification

```sh
sed -n '/<script>/,/<\\/script>/p' templates/form.html | sed '1d;$d' | node --check
uv run pytest
make check
git diff --check
```

The focused page contract test covers the chart, legend, frontier summary, and
rendering function. The full suite passes with 47 tests. A live browser smoke
check was attempted but no browser backend was available in this environment;
the inline script was still validated with `node --check`.
