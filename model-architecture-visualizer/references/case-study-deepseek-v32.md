# Case Study: DeepSeek-V3.2 Architecture Analysis

This document records the complete process of analyzing DeepSeek-V3.2, including mistakes made and lessons learned.

---

## Initial Request

**User:** "分析一下DeepSeek-V3.2的模型结构并进行可视化"

**Initial Mistake:** Analyzed DeepSeek-V3 instead of V3.2 (wrong version!)

**Lesson:** Always confirm the exact model version/variant requested.

---

## Iteration 1: Version Correction

**Problem:** User pointed out the version error

**Action:** Searched for DeepSeek-V3.2 specifically
- Found arXiv paper: https://arxiv.org/abs/2512.02556
- Found GitHub: https://github.com/deepseek-ai/DeepSeek-V3.2-Exp
- Found HuggingFace: https://huggingface.co/deepseek-ai/DeepSeek-V3.2-Exp

**Key Finding:** V3.2's main innovation is **DeepSeek Sparse Attention (DSA)**

**Deliverables:**
- Architecture diagram (had encoding issues with Chinese characters)
- Basic documentation

**Lesson:** Read carefully before starting work.

---

## Iteration 2: Too Coarse-Grained

**User Feedback:** "你这个太粗粒度了，DSA和MoE里面具体有哪些component你要说清楚，而且图里还有乱码字符"

**Problems Identified:**
1. DSA shown as a single block (no internal components)
2. MoE shown without detailed breakdown
3. Encoding issues in diagram (Chinese text corruption)

**Action:**
- Searched for more technical details
- Attempted to decompose DSA into sub-components
- Rewrote DOT file with ASCII-only text

**Attempted Breakdown:**
```
DSA Components (first attempt):
1. KV Down-Projection
2. Q Down-Projection
3. Indexer Module (sparse pattern)
4. KV/Q Up-Projection
5. RoPE (interleaved)
6. Sparse Attention Compute
7. Output Projection
```

**MoE Components:**
```
1. MoE Router (Sigmoid, Top-8)
2. Shared Expert (always active)
3. Routed Experts (256 total, select 8)
4. Load Balancing (aux-loss-free)
5. Expert Output Combine
```

**Deliverables:**
- `deepseek_v32_detailed.png` - Component-level diagram
- `DeepSeek-V3.2_Detailed_Components.md` - Written breakdown

**Lesson:** When user says "too coarse", they want **every sub-component** detailed, not just high-level modules.

---

## Iteration 3: Logical Errors

**User Feedback:** "你这里面还有一些逻辑性错误，例如rope并不是作用在Q_c，K_c然后生成Q_r，K_r，而是只作用于Q_r和K_r。你有没有什么办法可以测试自己写的网络结构是否是对的？"

**Critical Error Identified:**

**❌ My Initial Understanding:**
```
q_c, k_c -> RoPE -> q_r, k_r
```

**✅ Correct (from code):**
```
q_nope, q_pe = split(q)
q_pe -> RoPE -> q_pe_rotated
q_final = [q_nope ; q_pe_rotated]
```

**The "_pe" suffix means "positional encoding part", not "after RoPE"!**

**Lesson:** Papers and descriptions can be ambiguous. **Always verify with official code.**

---

## Verification Method: Code Analysis

**Step 1: Clone Official Repo**
```bash
git clone --depth 1 https://github.com/deepseek-ai/DeepSeek-V3.2-Exp.git
```

**Step 2: Locate Model Code**
```bash
find . -name "model*.py"
# Found: inference/model.py
```

**Step 3: Read Forward Pass**

**MLA Forward Pass (line-by-line):**
```python
# Line ~400
qr = self.q_norm(self.wq_a(x))           # Down-projection
q = self.wq_b(qr)                         # Up-projection
q = q.view(bsz, seqlen, self.n_local_heads, self.qk_head_dim)
q_nope, q_pe = torch.split(q, [self.qk_nope_head_dim, self.qk_rope_head_dim], dim=-1)
q_pe = apply_rotary_emb(q_pe, freqs_cis)  # RoPE ONLY on q_pe!
```

**Key Code Section:**
```python
def apply_rotary_emb(x: torch.Tensor, freqs_cis: torch.Tensor, interleaved: bool = True):
    # Default interleaved=True for MLA
    # interleaved=False for Indexer
    ...
```

**Indexer Forward Pass:**
```python
# Line ~350
q_pe, q_nope = torch.split(q, [self.rope_head_dim, ...], dim=-1)
q_pe = apply_rotary_emb(q_pe, freqs_cis, False)  # Non-interleaved!
q = torch.cat([q_pe, q_nope], dim=-1)
q = rotate_activation(q)  # Hadamard transform
```

**Step 4: Extract Dimensions**
```python
# ModelArgs dataclass (line ~20)
dim: int = 7168
q_lora_rank: int = 1536
kv_lora_rank: int = 512
qk_nope_head_dim: int = 128
qk_rope_head_dim: int = 64
index_n_heads: int = 64
index_head_dim: int = 128
index_topk: int = 2048
```

**Step 5: Document Correct Flow**

**MLA Data Flow (verified):**
```
x (7168)
├─> wq_a (7168 -> 1536) -> q_norm -> wq_b (1536 -> 128*192)
│   -> split -> [q_nope (128*128), q_pe (128*64)]
│   -> q_pe: apply_rotary_emb (interleaved=True)
│   -> concat: Q = [q_nope ; q_pe_rotated]
│
└─> wkv_a (7168 -> 576) -> split -> [kv_latent (512), k_pe (64)]
    ├─> kv_latent -> kv_norm -> wkv_b (512 -> 128*256)
    │   -> split -> [k_nope (128*128), v (128*128)]
    └─> k_pe: apply_rotary_emb (interleaved=True)
    -> concat: K = [k_nope ; k_pe_rotated]
```

**Indexer Data Flow (verified):**
```
qr (1536) -> wq_b (1536 -> 64*128)
  -> split -> [q_pe (64*64), q_nope (64*64)]
  -> q_pe: apply_rotary_emb (interleaved=False)
  -> concat: [q_pe_rot ; q_nope]
  -> rotate_activation (Hadamard)
  -> q_indexer

x (7168) -> wk (7168 -> 128) -> k_norm
  -> split -> [k_pe, k_nope]
  -> k_pe: apply_rotary_emb (interleaved=False)
  -> concat: [k_pe_rot ; k_nope]
  -> rotate_activation (Hadamard)
  -> k_indexer

x (7168) -> weights_proj (7168 -> 64)
  -> weights (for scoring)

fp8_index(q_indexer, weights, k_cache) -> index_score
  -> topk(2048) -> topk_indices (sparse mask)
```

---

## Final Correct Architecture

**Corrected Components:**

### DSA (DeepSeek Sparse Attention) - 7 sub-components

1. **Q Down-Projection**
   - `wq_a`: 7168 → 1536 (q_lora_rank)
   - Purpose: Compress query

2. **Q Normalization**
   - `q_norm`: RMSNorm on compressed query

3. **Q Up-Projection**
   - `wq_b`: 1536 → 128*192 (n_heads * qk_head_dim)
   - Split into: `q_nope` (128*128) and `q_pe` (128*64)

4. **KV Down-Projection**
   - `wkv_a`: 7168 → 576 (kv_lora_rank + qk_rope_head_dim)
   - Split into: `kv_latent` (512) and `k_pe` (64)

5. **KV Normalization & Up-Projection**
   - `kv_norm`: RMSNorm on kv_latent
   - `wkv_b`: 512 → 128*256
   - Split into: `k_nope` (128*128) and `v` (128*128)

6. **RoPE Application**
   - Apply to `q_pe` (interleaved layout)
   - Apply to `k_pe` (interleaved layout)
   - **NOT** creating new tensors, just rotating existing ones!

7. **Sparse Attention Compute**
   - Concatenate: `Q = [q_nope ; q_pe_rotated]`
   - Concatenate: `K = [k_nope ; k_pe_rotated]`
   - Scores = `(Q · K^T) / sqrt(d)`
   - Apply sparse mask from Indexer
   - Softmax + Attention·V

### Indexer Module - 5 sub-components

1. **Indexer Q Projection**
   - Uses `qr` from MLA
   - `wq_b`: 1536 → 64*128
   - Split, RoPE (**non-interleaved**), concat

2. **Indexer K Projection**
   - `wk`: 7168 → 128
   - `k_norm`: LayerNorm
   - Split, RoPE (**non-interleaved**), concat

3. **Hadamard Transform**
   - `rotate_activation(q)` and `rotate_activation(k)`
   - Special transform for indexer

4. **Weights Projection**
   - `weights_proj`: 7168 → 64
   - Used for scoring importance

5. **Sparse Mask Generation**
   - `fp8_index(q, weights, k_cache)` → scores
   - `topk(2048)` → sparse attention mask

---

## Key Discoveries

### 1. RoPE Misconception

**Common Mistake:** Thinking RoPE generates new tensors (`q_r`, `k_r`)

**Reality:** RoPE **modifies** the positional encoding part in-place:
```python
q_pe = apply_rotary_emb(q_pe, freqs_cis)  # Modifies q_pe
```

The naming convention `_pe` means "positional encoding part", not "rotary embedding output".

### 2. Layout Difference is Critical

**MLA:** `interleaved=True` (default)
```
[x0, y0, x1, y1, x2, y2, ...]
```

**Indexer:** `interleaved=False`
```
[x0, x1, x2, ..., y0, y1, y2, ...]
```

**Impact:** Using wrong layout causes performance degradation (noted in Nov 17, 2025 update).

### 3. Indexer is Separate

The Indexer has **independent projections** from MLA:
- Own Q projection (different dimensions: 64*128 vs 128*192)
- Own K projection (single head: 128)
- Additional Hadamard transform
- FP8 computation for efficiency

It's not just a mask generator - it's a parallel attention mechanism!

### 4. Compression Strategy

**Q path:** 7168 → 1536 → 128*192 (down then up)
**KV path:** 7168 → 512 → 128*256 (down then up)

The bottleneck reduces KV cache size substantially while maintaining quality.

---

## Lessons for Future Architecture Analysis

### 1. Start with Code, Not Papers

Papers can be:
- Ambiguous in notation
- High-level (hiding implementation details)
- Using non-standard naming conventions

Code is:
- Definitive (it's what actually runs)
- Shows exact dimensions
- Reveals implementation quirks

### 2. Trace Forward Pass Line-by-Line

```python
# For each tensor transformation:
print(f"tensor.shape: {tensor.shape}")
```

Follow every:
- Linear projection
- Split operation
- Concatenation
- Normalization
- Activation function

### 3. Document Dimensions Everywhere

```
x: (bsz, seqlen, 7168)
qr: (bsz, seqlen, 1536)
q: (bsz, seqlen, 128, 192)
q_nope: (bsz, seqlen, 128, 128)
q_pe: (bsz, seqlen, 128, 64)
```

Dimensions help catch errors (e.g., if split sizes don't add up).

### 4. Check for Special Flags/Layouts

Look for boolean parameters:
- `interleaved=True/False`
- `use_cache=True/False`
- `training=True/False`

These can change behavior significantly!

### 5. Create Verification Checklist

Before finalizing:
- [ ] Traced forward pass in code
- [ ] All tensor splits/concats identified
- [ ] RoPE application points confirmed
- [ ] Dimensions verified at each step
- [ ] Special flags/parameters documented
- [ ] Custom kernels identified
- [ ] Compared with paper description

---

## Final Deliverables

1. **deepseek_v32_corrected.png**
   - Full architecture with all sub-components
   - Color-coded by module type
   - Dimensions labeled on each node
   - Critical differences highlighted (interleaved vs non-interleaved)

2. **DeepSeek-V3.2_Architecture_Verification.md**
   - Complete code analysis
   - Corrected data flows
   - Dimensional analysis
   - Critical implementation details

3. **DeepSeek-V3.2_Detailed_Components.md**
   - Component-by-component breakdown
   - Mathematical formulations
   - Code snippets for each module

---

## Takeaways

1. **Always verify with code** - papers are guides, code is truth
2. **Decompose to sub-components** - users want details, not abstractions
3. **Check every dimension** - math errors show up in shapes
4. **Document special cases** - layouts, flags, custom kernels matter
5. **Iterate based on feedback** - users know when something is wrong

**Bottom line:** Architecture visualization is not about drawing boxes. It's about **understanding and accurately representing every transformation** the data goes through.
