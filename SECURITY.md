# Security Policy

## Scope

pathlab is a local, offline educational tool: it reads graph files you provide,
computes algorithms in memory, writes HTML/JSON only where you explicitly pass
`-o`, and makes **no network requests**. There is no server, no telemetry and
no third-party dependency (standard library only).

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | ✔ |

## Reporting a vulnerability

Open a private security advisory on this repository (not a public issue) for
anything like: file writes outside the path given to `-o`, path traversal from
graph input, unsafe deserialization, or generated HTML that can execute
unexpected content (the visualizer HTML-escapes titles/summaries and neutralizes
`</` in the JSON payload so node ids cannot inject markup).

## Notes on generated output

- `pathlab viz` writes whatever filename you pass to `-o`. Review before
  sharing generated HTML if your graph came from an untrusted source: node
  *labels* are rendered as SVG text but are also embedded in the JSON payload.
- Graph files are parsed, never evaluated: `json.loads` only, no `eval`,
  no `pickle`.

## Responsible use

Nothing here interfaces with networks or other systems, so the usual "only
test systems you own" rule does not apply — but if you publish quiz results or
visualizations of proprietary graphs, that is on you.