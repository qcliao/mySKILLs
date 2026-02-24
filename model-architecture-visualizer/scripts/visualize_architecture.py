#!/usr/bin/env python3
"""
Model Architecture Visualizer
Generates visual diagrams of neural network architectures using Graphviz.
"""

import json
import sys
import argparse
from pathlib import Path

def generate_graphviz(config: dict, output_path: str) -> str:
    """
    Generate a Graphviz DOT file from architecture configuration.
    
    Args:
        config: Architecture configuration dict
        output_path: Path to save the .dot file
    
    Returns:
        Path to the generated .dot file
    """
    dot_content = ["digraph ModelArchitecture {"]
    dot_content.append('    rankdir=TB;')
    dot_content.append('    node [shape=box, style="rounded,filled", fillcolor=lightblue];')
    dot_content.append('    edge [color=gray, penwidth=2];')
    dot_content.append('')
    
    # Title
    if "title" in config:
        dot_content.append(f'    labelloc="t";')
        dot_content.append(f'    label="{config["title"]}";')
        dot_content.append(f'    fontsize=20;')
        dot_content.append('')
    
    # Process stages
    if "stages" in config:
        for idx, stage in enumerate(config["stages"]):
            stage_name = stage.get("name", f"Stage {idx+1}")
            stage_id = f"stage_{idx}"
            
            # Stage node
            dot_content.append(f'    {stage_id} [label="{stage_name}", fillcolor=lightyellow];')
            
            # Blocks within stage
            if "blocks" in stage:
                for block_idx, block in enumerate(stage["blocks"]):
                    block_id = f"{stage_id}_block_{block_idx}"
                    block_type = block.get("type", "Block")
                    block_details = block.get("details", "")
                    
                    # Choose color based on block type
                    color = "lightblue"
                    if "attention" in block_type.lower():
                        color = "lightgreen"
                    elif "mamba" in block_type.lower():
                        color = "lightcoral"
                    elif "mlp" in block_type.lower() or "ffn" in block_type.lower():
                        color = "lightyellow"
                    
                    label = block_type
                    if block_details:
                        label += f"\\n{block_details}"
                    
                    dot_content.append(f'    {block_id} [label="{label}", fillcolor={color}];')
                    
                    # Connect stage to first block
                    if block_idx == 0:
                        dot_content.append(f'    {stage_id} -> {block_id};')
                    else:
                        prev_block_id = f"{stage_id}_block_{block_idx-1}"
                        dot_content.append(f'    {prev_block_id} -> {block_id};')
            
            # Connect stages
            if idx > 0:
                prev_stage_id = f"stage_{idx-1}"
                # Find last block of previous stage
                prev_stage = config["stages"][idx-1]
                if "blocks" in prev_stage and len(prev_stage["blocks"]) > 0:
                    last_block_id = f"{prev_stage_id}_block_{len(prev_stage['blocks'])-1}"
                    dot_content.append(f'    {last_block_id} -> {stage_id};')
                else:
                    dot_content.append(f'    {prev_stage_id} -> {stage_id};')
            
            dot_content.append('')
    
    # Custom nodes
    if "custom_nodes" in config:
        for node in config["custom_nodes"]:
            node_id = node.get("id")
            label = node.get("label", node_id)
            color = node.get("color", "lightgray")
            dot_content.append(f'    {node_id} [label="{label}", fillcolor={color}];')
    
    # Custom edges
    if "custom_edges" in config:
        for edge in config["custom_edges"]:
            from_node = edge.get("from")
            to_node = edge.get("to")
            label = edge.get("label", "")
            if label:
                dot_content.append(f'    {from_node} -> {to_node} [label="{label}"];')
            else:
                dot_content.append(f'    {from_node} -> {to_node};')
    
    dot_content.append('}')
    
    # Write to file
    dot_path = Path(output_path).with_suffix('.dot')
    dot_path.write_text('\n'.join(dot_content))
    
    return str(dot_path)


def render_diagram(dot_path: str, output_format: str = "png") -> str:
    """
    Render the DOT file to an image using Graphviz.
    
    Args:
        dot_path: Path to the .dot file
        output_format: Output format (png, svg, pdf)
    
    Returns:
        Path to the rendered image
    """
    import subprocess
    
    output_path = Path(dot_path).with_suffix(f'.{output_format}')
    
    try:
        subprocess.run(
            ['dot', f'-T{output_format}', str(dot_path), '-o', str(output_path)],
            check=True,
            capture_output=True,
            text=True
        )
        return str(output_path)
    except subprocess.CalledProcessError as e:
        print(f"Error rendering diagram: {e.stderr}", file=sys.stderr)
        raise
    except FileNotFoundError:
        print("Error: Graphviz 'dot' command not found. Please install Graphviz.", file=sys.stderr)
        print("Install with: brew install graphviz (macOS) or apt-get install graphviz (Linux)", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description='Visualize neural network architectures')
    parser.add_argument('config', help='Path to architecture config JSON file')
    parser.add_argument('-o', '--output', required=True, help='Output file path (without extension)')
    parser.add_argument('-f', '--format', default='png', choices=['png', 'svg', 'pdf'],
                        help='Output format (default: png)')
    parser.add_argument('--dot-only', action='store_true',
                        help='Only generate DOT file without rendering')
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Generate DOT file
    dot_path = generate_graphviz(config, args.output)
    print(f"Generated DOT file: {dot_path}")
    
    # Render diagram
    if not args.dot_only:
        output_path = render_diagram(dot_path, args.format)
        print(f"Generated diagram: {output_path}")
        return output_path
    
    return dot_path


if __name__ == '__main__':
    main()
