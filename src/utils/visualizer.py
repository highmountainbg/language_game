import html
import json
import os

from loguru import logger

from src.utils.path_manager import data_dir
from src.sampler import reconstruct_game_sampler_for_display


def create_html_tree(game_name, sampler_id):
    # Get the tree data
    sampler_path = os.path.join(data_dir, game_name, sampler_id)
    tree = reconstruct_game_sampler_for_display(sampler_path)

    # Convert the tree to a JSON format compatible with D3.js
    tree_data = node_to_json(tree.root)

    # Create the HTML file with embedded JavaScript
    html_content = generate_html(tree_data, game_name, sampler_id)

    # Write to file
    output_file = os.path.join(sampler_path, "visualizer.html")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Visualization created at: {output_file}")

    return output_file


def node_to_json(game_node):
    """Convert the game tree node to a format suitable for D3.js visualization"""
    node_data = {
        "id": game_node.id,
        "display": {},
        "children": []
    }
    for key, val in game_node.display.items():
        k = html.escape(key)
        if isinstance(val, dict) or isinstance(val, list):
            v = html.escape(json.dumps(val, ensure_ascii=False))
        elif isinstance(val, str):
            v = html.escape(val)
        elif val is None:
            v = ""
        else:
            v = html.escape(str(val))
        node_data["display"][k] = v

    for child in game_node.children:
        node_data["children"].append(node_to_json(child))

    return node_data


def generate_html(tree_data, game_name, sampler_id):
    """
    Generate HTML with embedded D3.js visualization
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Sampler Visualization of {game_name} {sampler_id}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
        }}
        #tree-container {{
            flex: 2;
            overflow: auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        #content-panel {{
            flex: 1;
            padding: 20px;
            border-left: 1px solid #ddd;
            overflow: auto;
            min-width: 300px;
            max-width: 500px;
        }}
        .node {{
            cursor: pointer;
        }}
        .node circle {{
            fill: #fff;
            stroke: steelblue;
            stroke-width: 2px;
        }}
        .node text {{
            font: 12px sans-serif;
        }}
        .link {{
            fill: none;
            stroke: #ccc;
            stroke-width: 2px;
        }}
        .controls {{
            position: fixed;
            top: 10px;
            left: 10px;
            background: white;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            z-index: 100;
        }}
        button {{
            margin: 0 5px;
            padding: 5px 10px;
            cursor: pointer;
        }}
        #search-box {{
            padding: 5px;
            margin-left: 10px;
            width: 200px;
        }}
        .highlight circle {{
            fill: yellow;
            stroke: red;
            stroke-width: 3px;
        }}
        .selected circle {{
            fill: #d1f0ff;
            stroke: #0066cc;
            stroke-width: 3px;
        }}
    </style>
</head>
<body>
    <div id="tree-container"></div>
    <div id="content-panel">
        <div id="node-details">
            <p>Click on a node to view details</p>
        </div>
    </div>
    <div class="controls">
        <button id="zoom-in">Zoom In</button>
        <button id="zoom-out">Zoom Out</button>
        <button id="reset">Reset View</button>
        <input type="text" id="search-box" placeholder="Search nodes...">
    </div>

    <script>
    // Tree data
    const treeData = {json.dumps(tree_data)};
    
    // Set up dimensions and margins
    const margin = {{top: 40, right: 120, bottom: 40, left: 120}};
    const width = 1000;
    const height = 800;
    
    // Initialize D3.js tree layout
    const tree = d3.tree().size([height, width]);
    
    // Create a hierarchy from the data
    const root = d3.hierarchy(treeData);
    
    // Set up the SVG container
    const svg = d3.select("#tree-container")
        .append("svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", [0, 0, width + margin.left + margin.right, height + margin.top + margin.bottom])
        .call(d3.zoom().on("zoom", (event) => {{
            g.attr("transform", event.transform);
        }}))
        .append("g")
        .attr("transform", `translate(${{margin.left}},${{margin.top}})`);
    
    const g = svg.append("g");
    
    // Compute the tree layout
    tree(root);
    
    // Create the links between nodes
    const link = g.selectAll(".link")
        .data(root.links())
        .enter().append("path")
        .attr("class", "link")
        .attr("d", d3.linkVertical()
            .x(d => d.x)
            .y(d => d.y));
    
    // Create nodes
    const node = g.selectAll(".node")
        .data(root.descendants())
        .enter().append("g")
        .attr("class", "node")
        .attr("transform", d => `translate(${{d.x}},${{d.y}})`)
        .on("click", (event, d) => {{
            // Remove previous selection
            d3.selectAll(".node").classed("selected", false);
            
            // Add selected class to clicked node
            d3.select(event.currentTarget).classed("selected", true);
            
            // Display node details in the panel
            showNodeDetails(d.data);
        }});
    
    // Add circles for the nodes
    node.append("circle")
        .attr("r", 10);
    
    // Add labels for the nodes
    // node.append("text")
    //     .attr("dy", ".35em")
    //     .attr("x", d => d.children ? -13 : 13)
    //     .style("text-anchor", d => d.children ? "end" : "start")
    //     .text(d => "");
    
    // Function to display node details
    function showNodeDetails(nodeData) {{
        let details = `<h3>node_id</h3><pre>${{nodeData.id}}</pre>`;
        
        for (const [key, value] of Object.entries(nodeData.display)) {{
            details += `<h3>${{key}}</h3><pre style="white-space: pre-wrap;">${{value}}</pre>`;
        }}
        
        document.getElementById("node-details").innerHTML = details;
    }}
    
    // Set up controls
    document.getElementById("zoom-in").addEventListener("click", () => {{
        svg.transition()
            .call(d3.zoom().transform, d3.zoomTransform(svg.node()).scale(1.2));
    }});
    
    document.getElementById("zoom-out").addEventListener("click", () => {{
        svg.transition()
            .call(d3.zoom().transform, d3.zoomTransform(svg.node()).scale(0.8));
    }});
    
    document.getElementById("reset").addEventListener("click", () => {{
        svg.transition()
            .call(d3.zoom().transform, d3.zoomIdentity.translate(margin.left, margin.top));
    }});

    // Search functionality
    document.getElementById("search-box").addEventListener("input", (e) => {{
        const searchTerm = e.target.value.toLowerCase();
        
        // Remove previous highlights
        d3.selectAll(".node").classed("highlight", false);
        
        if (searchTerm.length > 0) {{
            // Search through nodes
            d3.selectAll(".node").each(function(d) {{
                const nodeText = JSON.stringify(d.data).toLowerCase();
                if (nodeText.includes(searchTerm)) {{
                    d3.select(this).classed("highlight", true);
                }}
            }});
        }}
    }});
    
    // Initialize the view to show the entire tree
    svg.call(d3.zoom().transform, d3.zoomIdentity.translate(margin.left, margin.top));
    </script>
</body>
</html>
    """


def newest_entry(directory_path):
    # Get all entries in the directory excluding hidden files
    entries = [x for x in os.scandir(directory_path) if x.name[0] != '.']
    # Sort by creation time, newest first
    entries.sort(key=lambda x: os.path.getctime(x), reverse=True)

    return entries[0].name if entries else None
