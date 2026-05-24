# LoRA Compatibility Certification

Status: core safety plan
Purpose: prevent model collapse from fine-grained or multi-LoRA control.

## 1. Why compatibility certification is needed

The project wants to make LoRA modules fine-grained and resident-efficient. Fine-grained modules are useful, but arbitrary combinations can interfere.

Risk examples:

```text
- wrong LoRA lowers accuracy
- wrong LoRA increases confidence while wrong
- two LoRAs push hidden states in conflicting directions
- adapter mixture is slower than expected due to routing/kernel fragmentation
- a bad route contaminates verifier or graph memory
```

Therefore, runtime should not freely compose adapters.

## 2. Simula's narrowed role

Simula should be treated as an offline certification compiler:

```text
online traces + hard negatives + adapter cards + probe results
  -> taxonomy calibration
  -> compatibility matrix
  -> certified bundles
  -> quarantine list
```

Simula should not be the main runtime world model in the first core version.

## 3. Adapter compatibility graph

Represent adapters as nodes:

```yaml
node:
  adapter_id: string
  taxonomy_vector: vector
  capability_probe: dict
  memory_cost: float
  latency_cost: float
  certification_status: experimental|certified|quarantined
```

Represent pairwise compatibility as edges:

```yaml
edge:
  adapter_i: string
  adapter_j: string
  param_overlap: float
  b_space_overlap: float
  behavioral_synergy: float
  collapse_risk: float
  latency_pair_cost: float
  certified: bool
```

## 4. Parameter compatibility

For two LoRA updates:

\[
\Delta W_i = B_i A_i,
\quad
\Delta W_j = B_j A_j
\]

A simple overlap measure:

\[
C^{\Delta}_{ij}
=
\frac{
\langle \Delta W_i, \Delta W_j \rangle
}{
\|\Delta W_i\|_F\|\Delta W_j\|_F
}
\]

If available, also measure output-side subspace overlap:

\[
C^B_{ij}
=
\frac{\|{U_i^B}^{\top}U_j^B\|_F^2}{r}
\]

where \(U_i^B\) is a basis for the column subspace of \(B_i\).

## 5. Behavioral compatibility

Let \(Q(\cdot)\) be task score or verifier-approved quality.

Individual gains:

\[
G_i = Q(f_{A_i}) - Q(f_0)
\]

Pair gain:

\[
G_{ij}=Q(f_{A_i+A_j})-Q(f_0)
\]

Synergy:

\[
Syn_{ij}=G_{ij}-(G_i+G_j)
\]

Negative synergy indicates interference.

## 6. Collapse risk

Measure confidence-increasing wrong answers:

\[
C^{collapse}_{ij}
=
\mathbb{E}
\left[
\mathbf{1}(\hat{y}_{ij}\ne y)
\cdot
\max(0, conf_{ij}-conf_0)
\right]
\]

This is more important than accuracy alone.

## 7. Edge risk score

Use a combined risk score:

\[
\Omega_{ij}
=
\lambda_\Delta C^\Delta_{ij}
+
\lambda_B C^B_{ij}
-
\lambda_S Syn_{ij}
+
\lambda_C C^{collapse}_{ij}
+
\lambda_L L_{ij}
\]

Lower is safer.

## 8. Certified bundle rule

For adapter bundle \(Z\):

\[
\Omega(Z)=\sum_{i<j, i,j\in Z}\Omega_{ij}+\lambda_{|Z|}|Z|
\]

Bundle certification:

\[
Z\in\mathcal{B}_{cert}
\iff
\Omega(Z)\le\tau_\Omega
\quad\text{and}\quad
Q(Z)\ge\tau_Q
\]

Runtime must only use:

\[
Z_t\in\mathcal{B}_{cert}
\]

## 9. Runtime restrictions

Default runtime rules:

```yaml
runtime_rules:
  active_adapters: "top-1 first, top-2 only if certified"
  token_level_switching: false
  arbitrary_adapter_mixture: false
  uncertified_bundle_loading: false
  wrong_adapter_damage_test: required before certification
```

## 10. Quarantine rules

Quarantine adapter or bundle when:

```yaml
quarantine_if:
  - wrong_adapter_confidence_gain > threshold
  - verifier_false_pass occurs
  - adapter_conflict repeats
  - graph_false_commit risk is detected
  - latency or memory cost exceeds certification envelope
```

Do not quarantine merely because the full model could not answer a hard sample. That should be `reject`, `unresolved`, or `terminal_model_error`, not adapter quarantine.
