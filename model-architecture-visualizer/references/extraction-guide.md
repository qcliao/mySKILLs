# Architecture Information Sources

This guide outlines how to extract model architecture information from various sources.

## Source Priority

1. **Official GitHub Repository** - Most reliable, contains actual implementation code
2. **Official Paper (arXiv/conference)** - Detailed architectural descriptions
3. **Model Card on Hugging Face** - Configuration files and documentation
4. **Blog Posts / Technical Reports** - Additional insights and diagrams

## Extraction Strategies

### From GitHub Repository

**Look for:**
- `config.json` or `model_config.py` - Configuration details
- `modeling_*.py` files - Architecture implementation
- `README.md` - Architecture overview and diagrams
- `architecture.png` or similar diagrams in `/docs` or root

**Key information to extract:**
- Number of layers/stages
- Hidden dimensions
- Attention mechanisms (multi-head, grouped-query, etc.)
- Activation functions
- Normalization layers
- Special components (Mamba blocks, MoE, etc.)

**Example search patterns:**
```python
# Search for layer definitions
grep -r "class.*Layer" --include="*.py"
grep -r "num_layers\|n_layers" --include="*.py"
grep -r "hidden_size\|d_model" --include="*.py"

# Find attention mechanisms
grep -r "Attention" --include="*.py"

# Look for stage/block structures
grep -r "Stage\|Block" --include="*.py"
```

### From Research Papers (arXiv)

**Sections to focus on:**
- Abstract - High-level architecture description
- Section 2-3 (usually "Model Architecture" or "Method")
- Figures showing architecture diagrams
- Appendix - Detailed hyperparameters

**Key patterns to identify:**
- "We use X layers of..."
- "Our model consists of..."
- Architecture diagrams (Figure 1, Figure 2, etc.)
- Tables with hyperparameters

**Example queries:**
```
site:arxiv.org "model name" architecture
site:arxiv.org "model name" pdf
```

### From Hugging Face

**Files to check:**
- `config.json` - Complete model configuration
- Model card README - Architecture description
- `modeling_*.py` in the Files tab - Implementation details

**API queries:**
```python
from transformers import AutoConfig

config = AutoConfig.from_pretrained("model-name")
print(config)
```

### From Technical Blogs

**Reliable sources:**
- Official company blogs (OpenAI, Anthropic, Google AI, Meta AI)
- Hugging Face blog
- Papers with Code

**Look for:**
- Architecture comparison tables
- Simplified diagrams
- Key innovations highlighted

## Architecture JSON Schema

After extracting information, structure it as:

```json
{
  "model_name": "string",
  "title": "Model Architecture Diagram",
  "source": "GitHub/Paper/HuggingFace",
  "stages": [
    {
      "name": "Stage 1",
      "blocks": [
        {
          "type": "Block Type",
          "details": "Additional info"
        }
      ]
    }
  ],
  "custom_nodes": [
    {
      "id": "input",
      "label": "Input Embeddings",
      "color": "lightgray"
    }
  ],
  "custom_edges": [
    {
      "from": "input",
      "to": "stage_0"
    }
  ]
}
```

## Block Type Color Convention

- **Attention blocks** → lightgreen
- **Mamba/SSM blocks** → lightcoral  
- **MLP/FFN blocks** → lightyellow
- **Normalization** → lightblue
- **Embedding/Input** → lightgray
- **Output/Head** → wheat

## Common Model Patterns

### Transformer-based
- Embedding → N × (Attention + FFN) → Output Head
- Each layer: LayerNorm + Multi-Head Attention + LayerNorm + FFN

### Hybrid Models (like MiniMax-2.5)
- Stage 1: Mamba/SSM blocks
- Stage 2+: Attention blocks
- Gradual complexity increase

### MoE (Mixture of Experts)
- Expert routing layer
- Multiple expert FFNs
- Gating mechanism

## Verification Checklist

Before finalizing architecture:
- [ ] Layer count matches official documentation
- [ ] Key components identified (attention type, activation, etc.)
- [ ] Architecture flow makes logical sense
- [ ] Special features noted (MoE, sliding window, etc.)
- [ ] Sources cited for verification
