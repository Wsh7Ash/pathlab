"""Build a single self-contained HTML file that animates a trace.

No external scripts, fonts or styles are referenced: everything the browser
needs is inlined, so the file works from ``file://`` with no network.
"""

from __future__ import annotations

import html
import json

from .algorithms import TraceResult
from .graph import Graph

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#0f1420;--panel:#161d2e;--line:#2a3550;--fg:#dce4f5;--muted:#8b98b8;
--acc:#4cc38a;--front:#e8b04c;--cur:#ff6b6b;--edge:#55628a;--goal:#e86aa0;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.45 system-ui,"Segoe UI",sans-serif}
header{padding:14px 18px;border-bottom:1px solid var(--line)}
h1{font-size:16px;margin:0 0 4px}
.sub{color:var(--muted);font-size:12px}
main{display:flex;gap:14px;padding:14px 18px;flex-wrap:wrap}
#stage{flex:1 1 520px;background:var(--panel);border:1px solid var(--line);
border-radius:10px;padding:8px;min-width:460px}
svg{width:100%;height:auto;display:block}
.edge line{stroke:var(--edge);stroke-width:2}
.edge.directed line{marker-end:url(#arrow)}
.edge text{fill:var(--muted);font-size:10px;text-anchor:middle}
.edge.active line{stroke:var(--cur);stroke-width:3}
.edge.active text{fill:var(--cur);font-weight:700}
.node circle{fill:#1d2740;stroke:#5c6b96;stroke-width:2}
.node text.id{fill:var(--fg);font-size:11px;text-anchor:middle}
.node text.dist{fill:var(--front);font-size:10px;text-anchor:middle}
.node.settled circle{fill:var(--acc);stroke:#0f1420}
.node.settled text.id{fill:#08130d;font-weight:700}
.node.settled text.dist{fill:#08130d}
.node.frontier circle{stroke:var(--front);stroke-dasharray:4 3}
.node.is-start circle{stroke:var(--acc);stroke-width:3}
.node.is-goal circle{stroke:var(--goal);stroke-width:3}
.node.current circle{stroke:var(--cur);stroke-width:3;stroke-dasharray:none}
.node.cycle circle{stroke:var(--cur);stroke-width:3;stroke-dasharray:3 2}
#pathlayer polyline{fill:none;stroke:var(--acc);stroke-width:4;
stroke-opacity:.65;stroke-linecap:round;stroke-linejoin:round}
#side{flex:1 1 300px;max-width:430px;background:var(--panel);
border:1px solid var(--line);border-radius:10px;padding:12px}
.badge{display:inline-block;padding:2px 10px;border-radius:999px;
background:#26304a;color:#7fb8ff;font-size:12px;font-weight:700}
#text{margin:10px 0;min-height:3.2em}
.ctl{display:flex;gap:8px;align-items:center;margin:8px 0}
button{background:#232e4a;border:1px solid var(--line);color:var(--fg);
border-radius:8px;padding:6px 11px;cursor:pointer}
button:hover{background:#2c3a5e}
input[type=range]{flex:1;accent-color:#4cc38a}
.snap{font-family:ui-monospace,Consolas,monospace;font-size:12px;
white-space:pre-wrap;color:var(--muted);background:#101828;
border:1px solid var(--line);border-radius:8px;padding:8px;
max-height:250px;overflow:auto}
.keys{color:var(--muted);font-size:12px;padding-left:18px;margin:10px 0 0}
</style>
</head>
<body>
<header><h1>__TITLE__</h1><div class="sub" id="sum">__SUMMARY__</div></header>
<main>
<div id="stage"><svg id="svg" viewBox="0 0 660 460" role="img"
 aria-label="graph animation">
<defs>
<marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="7"
 markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="#55628a"></path>
</marker>
</defs>
<g id="edges"></g><g id="pathlayer"></g><g id="nodes"></g>
</svg></div>
<div id="side">
<div><span class="badge" id="action">init</span>
 <span class="sub" id="counter">step 0 / 0</span></div>
<div id="text"></div>
<div class="ctl">
<button id="first" title="first step">&#9198;</button>
<button id="prev" title="previous step">&#9664;</button>
<input type="range" id="scrub" min="0" max="0" value="0" aria-label="step">
<button id="next" title="next step">&#9654;</button>
<button id="last" title="last step">&#9197;</button>
</div>
<div class="snap" id="snap"></div>
<ul class="keys">
<li>green = settled, dashed amber = frontier, red ring = current node</li>
<li>green polyline = final path (appears on the last step)</li>
<li>arrow keys navigate; numbers under nodes are their distances</li>
</ul>
</div>
</main>
<script>
const P = __PAYLOAD__;
const W = 660, H = 460, PAD = 52;
const SVGNS = "http://www.w3.org/2000/svg";
const nodes = P.graph.nodes, edges = P.graph.edges, steps = P.steps;
const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
const idSet = new Set(nodes.map(n => n.id));
const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
const minX = Math.min(...xs), maxX = Math.max(...xs);
const minY = Math.min(...ys), maxY = Math.max(...ys);
const scale = Math.min(
  (W - 2*PAD) / Math.max(maxX - minX, 1e-9),
  (H - 2*PAD) / Math.max(maxY - minY, 1e-9));
const offX = PAD + ((W - 2*PAD) - (maxX - minX) * scale) / 2;
const offY = PAD + ((H - 2*PAD) - (maxY - minY) * scale) / 2;
const PX = n => offX + (n.x - minX) * scale;
const PY = n => offY + (n.y - minY) * scale;
const fmt = v => { if (v == null) return "\\u221e";
  const n = Number(v); return Number.isInteger(n) ? String(n)
    : String(+n.toFixed(3)); };

const edgeLayer = document.getElementById("edges");
const nodeLayer = document.getElementById("nodes");
const pathLayer = document.getElementById("pathlayer");

const edgeEls = {};
for (const e of edges) {
  const a = byId[e.from], b = byId[e.to];
  if (!a || !b) continue;
  const g = document.createElementNS(SVGNS, "g");
  g.setAttribute("class", "edge" + (P.graph.directed ? " directed" : ""));
  const line = document.createElementNS(SVGNS, "line");
  line.setAttribute("x1", PX(a)); line.setAttribute("y1", PY(a));
  line.setAttribute("x2", PX(b)); line.setAttribute("y2", PY(b));
  const midX = (PX(a) + PX(b)) / 2, midY = (PY(a) + PY(b)) / 2;
  const halo = document.createElementNS(SVGNS, "circle");
  halo.setAttribute("cx", midX); halo.setAttribute("cy", midY);
  halo.setAttribute("r", 9); halo.setAttribute("fill", "#161d2e");
  const label = document.createElementNS(SVGNS, "text");
  label.setAttribute("x", midX); label.setAttribute("y", midY + 3);
  label.textContent = fmt(e.w);
  g.appendChild(line); g.appendChild(halo); g.appendChild(label);
  edgeLayer.appendChild(g);
  edgeEls[e.from + "\\u0000" + e.to] = g;
}

const nodeEls = {};
for (const n of nodes) {
  const g = document.createElementNS(SVGNS, "g");
  g.setAttribute("class", "node"
    + (n.id === P.start ? " is-start" : "")
    + (n.id === P.goal ? " is-goal" : "")
    + ((P.cycle || []).includes(n.id) ? " cycle" : ""));
  const c = document.createElementNS(SVGNS, "circle");
  c.setAttribute("cx", PX(n)); c.setAttribute("cy", PY(n)); c.setAttribute("r", 17);
  const idT = document.createElementNS(SVGNS, "text");
  idT.setAttribute("class", "id");
  idT.setAttribute("x", PX(n)); idT.setAttribute("y", PY(n) + 4);
  idT.textContent = n.id;
  const dT = document.createElementNS(SVGNS, "text");
  dT.setAttribute("class", "dist");
  dT.setAttribute("x", PX(n)); dT.setAttribute("y", PY(n) + 30);
  dT.textContent = "";
  g.appendChild(c); g.appendChild(idT); g.appendChild(dT);
  nodeLayer.appendChild(g);
  nodeEls[n.id] = { g, dist: dT };
}

let pathLine = null;
if (P.path && P.path.length > 1) {
  const poly = document.createElementNS(SVGNS, "polyline");
  poly.setAttribute("points", P.path.map(id => {
    const n = byId[id]; return n ? PX(n) + "," + PY(n) : "";
  }).filter(Boolean).join(" "));
  poly.style.display = "none";
  pathLayer.appendChild(poly);
  pathLine = poly;
}

// dist snapshots are keyed by node id for single-pair algorithms;
// Floyd-Warshall uses "u->v" keys instead, so labels are hidden there.
const distOk = steps.every(s =>
  Object.keys(s.dist || {}).every(k => idSet.has(k)));

let idx = 0;
const els = {
  action: document.getElementById("action"),
  counter: document.getElementById("counter"),
  text: document.getElementById("text"),
  snap: document.getElementById("snap"),
  scrub: document.getElementById("scrub"),
};
els.scrub.max = String(Math.max(steps.length - 1, 0));

function apply(i) {
  idx = Math.max(0, Math.min(i, steps.length - 1));
  const s = steps[idx];
  const settled = new Set(s.settled || []);
  const frontier = new Set(s.frontier || []);
  for (const n of nodes) {
    const e = nodeEls[n.id];
    e.g.classList.toggle("settled", settled.has(n.id));
    e.g.classList.toggle("frontier", frontier.has(n.id));
    e.g.classList.toggle("current", s.current === n.id);
    if (distOk) e.dist.textContent =
      s.dist && s.dist[n.id] !== undefined ? fmt(s.dist[n.id])
        : (settled.has(n.id) ? "\\u221e" : "");
    else e.dist.textContent = "";
  }
  for (const k in edgeEls) edgeEls[k].classList.remove("active");
  if (s.edge) {
    const k = s.edge[0] + "\\u0000" + s.edge[1];
    if (edgeEls[k]) edgeEls[k].classList.add("active");
    else if (!P.graph.directed) {
      const alt = s.edge[1] + "\\u0000" + s.edge[0];
      if (edgeEls[alt]) edgeEls[alt].classList.add("active");
    }
  }
  els.action.textContent = s.action;
  els.counter.textContent = "step " + (idx + 1) + " / " + steps.length;
  els.text.textContent = s.text;
  const lines = [];
  if ((s.settled || []).length && s.action !== "init")
    lines.push("settled:  " + s.settled.join(", "));
  if ((s.frontier || []).length)
    lines.push("frontier: " + s.frontier.join(", "));
  if (distOk && Object.keys(s.dist || {}).length)
    lines.push("dist:     " + Object.entries(s.dist)
      .map(([k, v]) => k + "=" + fmt(v)).join("  "));
  els.snap.textContent = lines.join("\\n") || "\\u2014";
  els.scrub.value = String(idx);
  if (pathLine) pathLine.style.display =
    idx === steps.length - 1 ? "block" : "none";
}

document.getElementById("first").onclick = () => apply(0);
document.getElementById("prev").onclick = () => apply(idx - 1);
document.getElementById("next").onclick = () => apply(idx + 1);
document.getElementById("last").onclick = () => apply(steps.length - 1);
els.scrub.addEventListener("input", e => apply(Number(e.target.value)));
document.addEventListener("keydown", e => {
  if (e.target && e.target.tagName === "INPUT") return;
  if (e.key === "ArrowRight" || e.key === " ") { apply(idx + 1); e.preventDefault(); }
  else if (e.key === "ArrowLeft") { apply(idx - 1); e.preventDefault(); }
  else if (e.key === "Home") apply(0);
  else if (e.key === "End") apply(steps.length - 1);
});
apply(0);
</script>
</body>
</html>
"""


def build_html(graph: Graph, result: TraceResult, title: str | None = None) -> str:
    payload = {
        "graph": graph.to_dict(),
        "steps": [s.to_dict() for s in result.steps],
        "start": result.start,
        "goal": result.goal,
        "path": result.path,
        "cycle": result.negative_cycle,
        "algo": result.algo,
    }
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    doc_title = title or f"pathlab — {result.algo}"
    html_doc = _TEMPLATE
    html_doc = html_doc.replace("__TITLE__", html.escape(doc_title))
    html_doc = html_doc.replace("__SUMMARY__", html.escape(result.summary()))
    html_doc = html_doc.replace("__PAYLOAD__", data)
    return html_doc


def write_html(graph: Graph, result: TraceResult, path: str,
               title: str | None = None) -> int:
    text = build_html(graph, result, title=title)
    data = text.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)   # byte length, matching what landed on disk