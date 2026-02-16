#!/usr/bin/env python3
"""
Generate Markdown documentation from model architecture JSON config.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime


def generate_markdown(config: dict) -> str:
    """Generate Markdown documentation from config."""
    
    md_lines = []
    
    # Title and metadata
    md_lines.append(f"# {config['model_name']} Architecture\n")
    md_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if 'source' in config:
        md_lines.append(f"**Source:** {config['source']}\n")
    
    # Add custom metadata if available
    if 'metadata' in config:
        meta = config['metadata']
        if 'total_params' in meta:
            md_lines.append(f"**Total Parameters:** {meta['total_params']}\n")
        if 'activated_params' in meta:
            md_lines.append(f"**Activated Parameters:** {meta['activated_params']}\n")
        if 'paper' in meta:
            md_lines.append(f"**Paper:** {meta['paper']}\n")
    
    md_lines.append("\n---\n")
    
    # Table of Contents
    md_lines.append("## Table of Contents\n")
    md_lines.append("- [Architecture Overview](#architecture-overview)\n")
    md_lines.append("- [Detailed Components](#detailed-components)\n")
    if 'custom_nodes' in config and config['custom_nodes']:
        md_lines.append("- [Key Innovations](#key-innovations)\n")
    md_lines.append("- [Configuration Summary](#configuration-summary)\n")
    md_lines.append("\n---\n")
    
    # Architecture Overview
    md_lines.append("## Architecture Overview\n")
    if 'overview' in config:
        md_lines.append(f"{config['overview']}\n\n")
    else:
        # Generate basic overview from stages
        stage_names = [stage['name'] for stage in config.get('stages', [])]
        md_lines.append(f"The {config['model_name']} consists of the following stages:\n\n")
        for i, name in enumerate(stage_names, 1):
            md_lines.append(f"{i}. {name}\n")
        md_lines.append("\n")
    
    # Detailed Components
    md_lines.append("## Detailed Components\n")
    
    for stage_idx, stage in enumerate(config.get('stages', []), 1):
        md_lines.append(f"### Stage {stage_idx}: {stage['name']}\n")
        
        for block in stage.get('blocks', []):
            md_lines.append(f"#### {block['type']}\n")
            
            if 'details' in block and block['details']:
                # Split details by newlines and format as list
                details = block['details'].strip().split('\n')
                if len(details) == 1:
                    md_lines.append(f"{details[0]}\n\n")
                else:
                    for detail in details:
                        if detail.strip():
                            md_lines.append(f"- {detail.strip()}\n")
                    md_lines.append("\n")
            else:
                md_lines.append("_No additional details provided._\n\n")
        
        md_lines.append("\n")
    
    # Key Innovations
    if 'custom_nodes' in config and config['custom_nodes']:
        md_lines.append("## Key Innovations\n")
        for node in config['custom_nodes']:
            label = node.get('label', node.get('id', 'Unknown'))
            md_lines.append(f"### {label}\n")
            if 'description' in node:
                md_lines.append(f"{node['description']}\n\n")
            else:
                md_lines.append("_Innovation details to be documented._\n\n")
    
    # Configuration Summary
    md_lines.append("## Configuration Summary\n")
    md_lines.append("| Component | Specification |\n")
    md_lines.append("|-----------|---------------|\n")
    
    # Extract key metrics from stages
    total_stages = len(config.get('stages', []))
    md_lines.append(f"| Total Stages | {total_stages} |\n")
    
    # Count block types
    block_counts = {}
    for stage in config.get('stages', []):
        for block in stage.get('blocks', []):
            block_type = block['type']
            block_counts[block_type] = block_counts.get(block_type, 0) + 1
    
    for block_type, count in sorted(block_counts.items()):
        md_lines.append(f"| {block_type} | {count} |\n")
    
    # Add custom metadata to table
    if 'metadata' in config:
        for key, value in config['metadata'].items():
            if key not in ['paper', 'total_params', 'activated_params']:
                formatted_key = key.replace('_', ' ').title()
                md_lines.append(f"| {formatted_key} | {value} |\n")
    
    md_lines.append("\n")
    
    # References
    md_lines.append("## References\n")
    if 'source' in config:
        md_lines.append(f"- **Main Source:** {config['source']}\n")
    
    if 'metadata' in config and 'paper' in config['metadata']:
        md_lines.append(f"- **Paper:** {config['metadata']['paper']}\n")
    
    if 'references' in config:
        for ref in config['references']:
            md_lines.append(f"- {ref}\n")
    
    md_lines.append("\n---\n")
    md_lines.append(f"\n*Documentation generated by model-architecture-visualizer*\n")
    
    return ''.join(md_lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Markdown documentation from model architecture JSON'
    )
    parser.add_argument('config', type=Path, help='Path to JSON config file')
    parser.add_argument('-o', '--output', type=Path, 
                       help='Output Markdown file path (default: <model_name>.md)')
    
    args = parser.parse_args()
    
    # Load JSON config
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Generate Markdown
    markdown_content = generate_markdown(config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        model_name = config.get('model_name', 'model').replace(' ', '_').lower()
        output_path = args.config.parent / f"{model_name}_architecture.md"
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"✓ Markdown documentation generated: {output_path}")
    print(f"  Lines: {len(markdown_content.splitlines())}")
    print(f"  Size: {len(markdown_content)} bytes")


if __name__ == '__main__':
    main()
