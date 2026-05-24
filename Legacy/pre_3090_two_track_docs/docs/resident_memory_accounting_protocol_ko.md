# Resident Memory Accounting Protocol

Status: implementation contract
Purpose: separate resident model memory from visual-token/KV/activation memory.

## 1. Why this matters

Foveation can reduce visual token cost but cannot reduce the memory of a backbone that is already resident on GPU.

LoRA can reduce memory when it replaces multiple full specialist backbones, but adding LoRA to a single already-resident model does not shrink that model.

Therefore, memory accounting must decompose total peak memory.

## 2. Memory decomposition

Use this conceptual model:

\[
M_{peak}
=
M_{backbone-resident}
+
M_{adapter-resident}
+
M_{visual/KV/activation}
+
M_{runtime-overhead}
+
M_{reserve}
\]

Track A targets:

\[
M_{backbone-resident} + M_{adapter-resident}
\]

Track B targets:

\[
M_{visual/KV/activation}
\]

## 3. Required fields

Every runtime trace should eventually include:

```yaml
memory:
  base_after_load_allocated_mb: null
  base_after_load_reserved_mb: null
  shared_backbone_resident_mb: null
  adapter_bank_resident_mb: null
  active_adapter_resident_mb: null
  visual_token_count: null
  visual_token_count_source: null
  kv_cache_estimate_mb: null
  kv_cache_estimate_source: null
  prefill_incremental_peak_mb: null
  decode_incremental_peak_mb: null
  visual_incremental_peak_mb: null
  total_peak_allocated_mb: null
  total_peak_reserved_mb: null
  normal_path_peak_vram_mb: null
  controlled_fallback_peak_vram_mb: null
  emergency_peak_vram_mb: null
  reserve_headroom_mb: null
```

## 4. Measurement points

### After model load

Immediately after loading the backbone and running `eval()`:

```python
base_after_load_allocated_mb = torch.cuda.memory_allocated() / MB
base_after_load_reserved_mb = torch.cuda.memory_reserved() / MB
```

This captures the resident cost of the shared backbone and static buffers.

### Before input execution

Before each candidate action:

```python
torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()
pre_action_allocated_mb = torch.cuda.memory_allocated() / MB
pre_action_reserved_mb = torch.cuda.memory_reserved() / MB
```

### After prefill/generation

After generation synchronizes:

```python
total_peak_allocated_mb = torch.cuda.max_memory_allocated() / MB
total_peak_reserved_mb = torch.cuda.max_memory_reserved() / MB
```

### Incremental peak

Compute:

```python
visual_incremental_peak_mb = total_peak_allocated_mb - base_after_load_allocated_mb
reserved_incremental_peak_mb = total_peak_reserved_mb - base_after_load_reserved_mb
```

If adapter tensors are allocated after model load, record them separately so they are not mistaken for visual-path memory.

## 5. Resident saving formula

Multiple full specialist models:

\[
M_{multi}
=
\sum_{k=1}^{K} M(W_k)
\]

Shared backbone with LoRA bank:

\[
M_{shared+LoRA}
=
M(W_0)
+
\sum_{i \in H} M(\Delta W_i)
\]

Resident saving:

\[
ResidentSaving
=
1-
\frac{M_{shared+LoRA}}{M_{multi}}
\]

If full specialist models cannot be jointly resident, report:

```yaml
resident_impossible: true
sequential_model_swap_latency_ms: measured
```

## 6. Visual evidence saving formula

Full visual context token count:

\[
T_{full}=|\phi_h(I)|
\]

Foveated visual token count:

\[
T_{fov}
=|\phi_g(I^g)|+
\sum_{r\in R}|\phi_h(Crop(I,r))|
\]

Visual token saving:

\[
VisualTokenSaving
=
1-
\frac{T_{fov}}{T_{full}}
\]

KV/cache estimate should be reported as proportional to the actual token sequence:

\[
M_{KV}\propto T_{text}+T_{vis}+T_{decode}
\]

## 7. Base-resident dominance ratio

Compute:

\[
\rho_{base}
=
\frac{M_{backbone-resident}}{M_{peak}}
\]

Interpretation:

```yaml
rho_base_high:
  condition: rho_base > 0.75
  meaning: peak memory is dominated by the resident backbone
  claim_boundary: foveation alone should not be claimed as large peak resident VRAM reduction

rho_base_low_or_moderate:
  condition: rho_base <= 0.75
  meaning: visual/KV/activation path may materially affect peak memory
```

## 8. Reporting rules

Always distinguish:

```text
resident VRAM reduction
incremental visual path reduction
normal-path peak reduction
emergency fallback peak
```

Do not write:

```text
FoveateR reduces model resident memory.
LoRA reduces visual token count.
```

Write instead:

```text
LoRA consolidation reduces duplicated specialist model residency.
FoveateR reduces visual token and KV/cache cost.
```
