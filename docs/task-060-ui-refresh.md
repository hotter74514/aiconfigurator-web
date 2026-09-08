# TASK-060: Serving-decision UI refresh

## Scope

TASK-023 implements the accepted ADR-015 decision. The existing server-rendered
Jinja2 page now uses a responsive serving-decision console layout with a dark
constraint panel, an output guide, clearer estimate warnings, stronger result
hierarchy, and improved focus/contrast treatment. The Pareto chart, mode
comparison, artifacts, local history, polling, API payload, DOM hooks, and
estimate wording remain unchanged in meaning.

The refresh keeps all CSS and JavaScript self-contained in `templates/form.html`.
It adds no frontend framework, package manifest, bundler, CDN request, static
asset route, or production dependency.

## Verification

```sh
.venv/bin/python -m pytest -q
node -e 'const fs=require("fs"), vm=require("vm"); const html=fs.readFileSync("templates/form.html","utf8"); const start=html.indexOf("<script>"), end=html.lastIndexOf("</script>"); new vm.Script(html.slice(start + 8, end)); console.log("inline JavaScript syntax: ok");'
.venv/bin/python - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.duplicate_ids = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            if values["id"] in self.ids:
                self.duplicate_ids.append(values["id"])
            self.ids.append(values["id"])

parser = Parser()
parser.feed(Path("templates/form.html").read_text())
assert not parser.duplicate_ids, parser.duplicate_ids
required = {"run-form", "submit-status", "history-panel", "results-panel", "pareto-chart", "comparison-panel", "artifact-list"}
assert required.issubset(parser.ids), required.difference(parser.ids)
print(f"HTML id contract: ok ({len(parser.ids)} ids)")
PY
make docs
make check
make k8s-render
make container-check
git diff --check
```

The full Python suite passed with 60 tests. The inline JavaScript syntax and
HTML ID contract checks passed. `make check`, `make k8s-render`, and
`make container-check` passed; the container check verified the Linux/amd64
runtime image's `/live`, `/ready`, and `/metrics` endpoints. The local Browser
runtime was unavailable in this environment (no browser instances were
returned), so interactive viewport screenshots and keyboard traversal remain a
follow-up verification when a browser instance is available. Existing
Docker/Minikube demo evidence remains valid because this change does not alter
the runtime or API path.

## Known limitation

The page remains a single template by design. A shared static CSS/JavaScript
boundary or component framework should be reconsidered only when the Portal has
multiple pages or repeated interactive components, as described in ADR-015.
