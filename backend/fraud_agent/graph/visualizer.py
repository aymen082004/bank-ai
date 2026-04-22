"""Graph visualization helper using vis-network (browser-side).

Produces a standalone HTML string rendering nodes/edges using vis-network CDN.
This avoids extra Python dependencies and can be embedded in notebooks or web UIs.
"""
import json
from typing import Dict, Any


VIS_NETWORK_CDN = "https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"


def render_visjs_html(subgraph: Dict[str, Any], height: int = 480) -> str:
    """Return an HTML string rendering the given subgraph with vis-network.

    Expects subgraph: {"nodes": [{"id": str, "label": str, "type": str, "title": str}],
                        "edges": [{"source": str, "target": str, "label": str}]}

    The returned HTML can be written to a file or embedded in an iframe/Gradio/Notebook.
    """
    nodes = subgraph.get("nodes", [])
    edges = subgraph.get("edges", [])

    # Compute degree (simple measure of importance) to size nodes
    degree = {}
    for e in edges:
        s = e.get("source")
        t = e.get("target")
        if s:
            degree[s] = degree.get(s, 0) + 1
        if t:
            degree[t] = degree.get(t, 0) + 1

    # Color and shape maps for known node types
    color_map = {
        "Client": "#1f78b4",
        "Account": "#33a02c",
        "Card": "#e31a1c",
        "Merchant": "#ff7f00",
    }

    shape_map = {
        "Client": "dot",
        "Account": "ellipse",
        "Card": "box",
        "Merchant": "triangle",
    }

    vis_nodes = []
    for n in nodes:
        nid = n.get("id")
        ntype = n.get("type") or n.get("label") or "Node"
        label = n.get("label") or str(nid)
        title = n.get("title") or label
        deg = degree.get(nid, 0)
        size = 14 + min(deg * 6, 36)
        color = color_map.get(ntype, "#6a3d9a")
        shape = shape_map.get(ntype, "dot")

        vis_nodes.append({
            "id": nid,
            "label": label,
            "title": title,
            "group": ntype,
            "size": size,
            "color": {"background": color, "border": "#222"},
            "font": {"size": 13, "face": "Arial", "color": "#222"},
            "shape": shape,
            "shadow": True,
        })

    vis_edges = []
    for e in edges:
      cnt = e.get("count", 1) or 1
      # width scales with count but is clamped
      width = 1 + min(int(cnt * 1.8), 10)
      color_intensity = 120 + min(int(cnt * 20), 120)
      edge_color = f"rgb({color_intensity},{color_intensity},{color_intensity})"
      vis_edges.append({
        "from": e.get("source"),
        "to": e.get("target"),
        "label": e.get("label") if e.get("label") else None,
        "arrows": "to",
        "color": {"color": edge_color, "highlight": "#333"},
        "width": width,
        "smooth": {"enabled": True, "type": "dynamic"},
      })

    data_js = {
        "nodes": vis_nodes,
        "edges": vis_edges,
    }

    # Small legend for the node groups
    legend_html = """
    <div id="legend" style="margin-bottom:8px; display:flex; gap:12px; align-items:center; flex-wrap:wrap">
      <div style="display:flex; gap:6px; align-items:center"><div style="width:12px;height:12px;background:#1f78b4;border-radius:50%"></div><div>Client</div></div>
      <div style="display:flex; gap:6px; align-items:center"><div style="width:12px;height:8px;background:#33a02c;border-radius:3px"></div><div>Account</div></div>
      <div style="display:flex; gap:6px; align-items:center"><div style="width:12px;height:12px;background:#e31a1c;clip-path:polygon(50% 0, 100% 100%, 0 100%)"></div><div>Card</div></div>
      <div style="display:flex; gap:6px; align-items:center"><div style="width:12px;height:12px;background:#ff7f00;border-radius:3px"></div><div>Merchant</div></div>
    </div>
    """

    html = f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Graph Visualization</title>
    <style>
      #network {{ width: 100%; height: {height}px; border: 1px solid #ddd; border-radius:6px; }}
      body {{ font-family: Arial, sans-serif; margin: 0; padding: 8px; color: #111 }}
      .vis-tooltip {{ font-size: 12px; }}
    </style>
  </head>
  <body>
    {legend_html}
    <div id="network"></div>
    <script src="{VIS_NETWORK_CDN}"></script>
    <script>
      const data = {json.dumps(data_js)};
      const container = document.getElementById('network');
      const options = {{
        nodes: {{
          borderWidthSelected: 3,
        }},
        edges: {{
          color: {{ inherit: false }},
          arrows: {{ to: {{ enabled: true, scaleFactor: 0.6 }} }},
        }},
        groups: {{
          Client: {{ shape: 'dot' }},
          Account: {{ shape: 'ellipse' }},
          Card: {{ shape: 'box' }},
          Merchant: {{ shape: 'triangle' }},
        }},
        interaction: {{ hover: true, navigationButtons: true, multiselect: false, tooltipDelay: 100 }},
        physics: {{
          enabled: true,
          stabilization: {{ enabled: true, iterations: 200 }},
          barnesHut: {{ gravitationalConstant: -8000, springLength: 120, springConstant: 0.001 }},
        }},
      }};
      const network = new vis.Network(container, data, options);
      // Improve hover cursor for nodes and edges
      network.on('hoverNode', function(params) {{ container.style.cursor = 'pointer'; }});
      network.on('blurNode', function(params) {{ container.style.cursor = 'default'; }});
      network.on('hoverEdge', function(params) {{ container.style.cursor = 'pointer'; }});
      network.on('blurEdge', function(params) {{ container.style.cursor = 'default'; }});
    </script>
  </body>
</html>
"""

    return html
