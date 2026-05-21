# Budget-Conditioned Foveated Adapter Policy

부제: VRAM 제약형 피지컬 AI를 위한 중심와 기반 증거 획득 및 LoRA 상주 정책 제안서  
발표용 핵심 구문: VRAM 제약형 피지컬 AI를 위한 다중 계층 LoRA 라우팅 및 상주 최적화 프로토콜  
발표 방향: LeWM 이론 발표에서 출발해 Simula, Foveated Reasoning, HydraLoRA를 연결하고 개인 제안으로 확장  
상태: v1 본문 초안, M3 산출물, M5 발표 방향 반영  
작성일: 2026-05-04

## 1. Executive Summary

본 제안서는 피지컬 AI 환경에서 perception model이 planner, world model, verifier, orchestration LLM과 VRAM을 공유해야 한다는 조건을 출발점으로 삼는다. 이 조건에서는 비전 모델이 전체 이미지를 고해상도로 계속 처리하는 방식이 곧바로 visual token, activation memory, KV cache, latency 증가로 이어진다. 따라서 문제는 단순히 "더 작은 모델을 쓰자"가 아니라, 제한된 VRAM 안에서 어떤 시각 증거를 획득하고 어떤 local skill adapter를 잠깐 사용할지 결정하는 정책 문제로 바뀐다.

본 제안의 핵심은 **Budget-Conditioned Foveated Adapter Policy**다. 이 정책은 저해상도 전역 관측으로 전체 문맥을 유지하면서, 필요한 ROI만 고해상도로 다시 보고, 그 ROI에 필요한 LoRA 또는 HydraLoRA expert를 제한된 시간 동안 VRAM에 상주시킨다. 얻은 결과는 최종 답변으로 바로 소비되는 것이 아니라 typed evidence로 정리되어 graph memory와 다음 ROI 선택에 되먹임된다.

이 문서는 결과 논문이 아니다. 현재 산출물은 "이 구조가 성능을 향상시켰다"는 실험 주장보다, **VRAM 제약형 피지컬 AI perception layer를 어떻게 정식화하고, 어떤 실험으로 검증해야 하는지**를 제안하는 policy/protocol proposal이다. 따라서 본문에서는 가설, 제약, 측정 요구사항, 실패 방어선을 분명히 구분한다.

M5 발표에서는 이 제안서를 바로 앞에서부터 읽지 않는다. 발표의 앞부분은 LeWM/world model의 state prediction과 planning loop, JEPA/SIGReg 기반 표현 안정화, Simula의 taxonomy 기반 task 구조화를 먼저 설명한다. 그다음 이 선행 구조들이 현장 배치에서 만나는 VRAM co-residency 문제를 짚고, 본 제안을 그 문제에 대한 adapter routing/residency 확장으로 제시한다.

한 문장 요약:

```text
Foveated Reasoning이 어디를 다시 볼지 학습한다면,
본 제안은 남은 VRAM 예산 안에서 어디를 볼지, 어떤 LoRA skill을 올릴지,
언제 내릴지, 그리고 그 증거를 graph memory에 쓸지를 함께 결정한다.
```

## 2. Problem: Co-resident VRAM Bottleneck

현장 피지컬 AI는 보통 단일 VLM만 돌리는 시스템이 아니다. 장치 수리, 설비 점검, 회로도 기반 진단 같은 상황에서는 perception model 외에도 planner, verifier, world model, retrieval module, orchestration LLM이 함께 동작해야 한다. 이때 perception model이 VRAM 대부분을 점유하면 다른 모듈이 같은 장비에 안정적으로 상주하기 어렵다.

문제는 full-resolution vision inference의 비용이 여러 항으로 동시에 커진다는 점이다.

```text
full-resolution input:
  visual token 증가
  activation memory 증가
  KV cache 증가
  latency 증가
  다른 orchestration module의 VRAM reserve 감소
```

LoRA만 작게 만든다고 peak VRAM 절감이 자동으로 보장되지는 않는다. LoRA adapter memory가 작아도, 전체 이미지를 고해상도로 계속 넣으면 visual token과 KV cache가 여전히 병목이 될 수 있다. 그래서 본 제안은 adapter memory와 visual token/KV cache 비용을 분리해서 다룬다.

예를 들어 장치 수리 상황을 생각할 수 있다. 시스템은 설계도, PCB 사진, 수리 매뉴얼을 함께 참고해야 한다. 설계도에서 학습한 local visual skill은 LoRA로 준비할 수 있지만, 현장에서는 모든 skill을 항상 VRAM에 올릴 필요가 없다. 저해상도 전역 루프가 "지금 이 부분에서 pin label 확인이 필요하다"고 판단하면 pin-label adapter만 잠깐 올리고, polarity ambiguity가 생기면 polarity/orientation adapter를 선택하는 식이 더 현실적이다.

따라서 본 제안의 VRAM 절감 주장은 다음처럼 제한한다.

```text
주장하지 않는 것:
  HydraLoRA만으로 전체 peak VRAM이 크게 줄어든다.

주장하는 것:
  visual-token policy와 adapter-residency policy를 함께 측정하면,
  같은 task success 근처에서 co-resident VRAM budget을 더 잘 관리할 수 있는지 검증할 수 있다.
```

## 3. Design Principle: VRAM as a Constraint

기존 초안의 직관적 loss는 task reward, routing loss, memory penalty를 선형 결합하는 방식이었다. 이는 구현하기 쉽고 coldstart training에는 충분히 자연스럽다. 그러나 현장 배포에서는 VRAM 상한을 넘지 않는 것이 "취향 가중치"가 아니라 hard deployment constraint에 가깝다.

따라서 본 제안은 상위 정책을 constrained optimization 문제로 둔다.

$$
\max_{\pi_\theta}
\mathbb{E}_{\tau \sim \pi_\theta}
\left[
R_{\mathrm{task}}(\tau)
+ R_{\mathrm{evidence}}(\tau)
+ R_{\mathrm{graph}}(\tau)
\right]
$$

subject to:

$$
\Pr\left(\max_t M_t > B_M\right) \le \delta_M,
\quad
\mathbb{E}[C_T(\tau)] \le B_T,
\quad
\mathbb{E}[C_A(\tau)] \le B_A,
\quad
\mathbb{E}[C_S(\tau)] \le B_S.
$$

여기서 `M_t`는 시점 `t`의 total allocated VRAM이고, `C_M(\tau)=\max_t M_t`는 trajectory 전체의 peak VRAM이다. `C_T`는 visual token과 latency 관련 비용, `C_A`는 adapter resident memory와 swap 비용, `C_S`는 orchestration module과 함께 상주하지 못하게 만드는 reserve violation cost다. `t`는 물리 시간이 아니라 inspection/reasoning step이다.

제약을 학습 과정에 넣기 위해 다음 Lagrangian view를 사용한다.

$$
\mathcal{L}(\theta,\lambda)
=
\mathbb{E}_{\tau \sim \pi_\theta}
\left[
R(\tau)
- \lambda_M \left(C_M(\tau)-B_M\right)
- \lambda_T \left(C_T(\tau)-B_T\right)
- \lambda_A \left(C_A(\tau)-B_A\right)
- \lambda_S \left(C_S(\tau)-B_S\right)
\right].
$$

여기서 `lambda`는 사람이 손으로 고른 취향값이 아니라, 제약 위반에 따라 조정되는 resource price로 해석한다. VRAM이 부족해질수록 `lambda_M`이 커지고, 정책은 같은 정확도 이득이라도 VRAM을 많이 쓰는 foveation이나 adapter load를 덜 선택하게 된다.

단, 전체 neural policy 학습은 비볼록이다. 따라서 본 제안은 "라그랑주 dual로 전역 최적해를 보장한다"고 주장하지 않는다. 안전한 표현은 다음과 같다.

```text
Coldstart supervision에는 안정적인 weighted loss를 사용하고,
budget-conditioned routing과 adapter residency 최적화에는
primal-dual style constrained policy optimization을 적용한다.
```

## 4. Related Recipe: Foveated Reasoning

Foveated Reasoning은 저해상도 전역 관측에서 시작해, 필요할 때만 고해상도 영역을 다시 보고, 그 evidence를 같은 reasoning trajectory에 주입하는 stateful visual focusing recipe로 볼 수 있다. 이 관점은 본 제안에 매우 중요하다. 왜냐하면 foveation을 단순 crop 전처리가 아니라, 현재 reasoning state가 선택하는 action으로 다루기 때문이다.

본 제안은 이 recipe를 그대로 경쟁 대상으로 두지 않는다. 오히려 Foveated Reasoning이 제공하는 학습 레시피를 Simula 기반 offline forge 안으로 가져온다.

```text
Foveated Reasoning:
  언제, 어디를 고해상도로 다시 볼지 결정한다.

본 제안:
  언제, 어디를 다시 볼지 결정한다.
  어떤 local adapter를 올릴지 결정한다.
  adapter를 keep/load/unload할지 결정한다.
  얻은 증거를 graph memory에 쓸지 결정한다.
  이 모든 결정을 co-resident VRAM budget 안에서 수행한다.
```

따라서 차별점은 high-resolution ROI action 자체가 아니라 action space의 확장에 있다. 기존 foveation action이 `where to look`에 초점을 둔다면, 본 제안은 `where to look`, `which skill to activate`, `how long to keep it resident`, `whether to write evidence`를 함께 다룬다.

## 5. Proposal: Budget-Conditioned Foveated Adapter Policy

정책 상태는 세 부분으로 둔다.

$$
s_t = (h_t, b_t, \mu_t)
$$

각 항의 의미는 다음과 같다.

```text
h_t:
  메인 모델의 reasoning hidden state

b_t:
  현재 자원 상태
  예: 남은 VRAM, 올라간 adapter, KV cache 크기, latency budget

mu_t:
  graph memory 또는 세계 상태에 대한 belief
```

행동은 하나의 단일 action이 아니라 결합 action이다.

$$
a_t = (m_t, r_t, z_t, \rho_t, g_t)
$$

각 항:

```text
m_t:
  token 생성, foveate, answer, stop 같은 행동 모드

r_t:
  관찰할 ROI box 또는 region index

z_t:
  선택할 LoRA adapter 또는 HydraLoRA expert subset

rho_t:
  load, keep, unload 같은 adapter residency action

g_t:
  graph memory write 또는 abstain decision
```

정책은 순차 조건부로 factorization한다.

$$
\pi_\theta(a_t \mid s_t)
=
\pi_\theta(m_t \mid s_t)
\pi_\theta(r_t \mid s_t, m_t)
\pi_\theta(z_t \mid s_t, m_t, r_t)
\pi_\theta(\rho_t \mid s_t, m_t, r_t, z_t)
\pi_\theta(g_t \mid s_t, m_t, r_t, z_t, \rho_t).
$$

이 factorization은 ROI 선택과 LoRA 선택을 독립으로 가정하지 않는다. 먼저 "더 볼 것인가"를 결정하고, 본다면 "어디를 볼 것인가"를 고른다. 그다음 그 ROI에 필요한 local skill을 고르고, 그 adapter를 VRAM에 올릴 가치가 있는지 판단한다. 마지막으로 얻은 evidence가 graph memory에 쓸 만큼 믿을 만한지 결정한다.

전체 시스템은 online runtime과 offline forge로 분리한다.

```text
Online Physical AI Runtime:
  low-res global state 유지
  high-recall ROI proposal
  high-res ROI crop
  adapter load/keep/unload
  typed evidence extraction
  graph belief update

Offline Simula Skill Forge:
  failure residual mining
  taxonomy update
  pseudo foveation trajectory generation
  adapter/router training
  certification and registry update
```

이 분리가 LoRA 학습 비용 질문을 방어하는 핵심이다. LoRA 학습은 offline forge에서 비용을 쓸 수 있다. 현장 runtime의 목표는 학습 비용을 없애는 것이 아니라, 검증된 작은 bundle만 사용해 co-resident VRAM 점유를 낮게 유지하는 것이다.

## 6. Offline Simula Adapter Tagging Compiler

Simula는 이 제안에서 runtime reasoner가 아니다. 또한 단순 합성 데이터 생성기도 아니다. 본 제안에서 Simula의 역할은 **adapter tag compiler**다.

Simula는 실패 residual, graph conflict, low-confidence ROI, router uncertainty를 받아 taxonomy node로 정리한다. 그리고 각 node에 대해 synthetic 또는 replay sample을 만들 때 final answer만 생성하지 않는다. runtime router가 바로 쓸 수 있는 adapter tag와 supervision을 함께 만든다.

각 sample은 최소한 다음 정보를 가져야 한다.

```text
sample:
  global_view
  instruction
  ROI trajectory
  required_evidence_type
  required_adapter_tags
  expected_graph_update
  abstain_or_fallback_label
  critic_result
  real/synthetic/quarantine split
```

이 구조의 목표는 runtime에서 "이 ROI에는 어떤 LoRA가 필요할까?"를 긴 자연어 reasoning token으로 매번 설명하지 않게 하는 것이다. Offline Simula가 adapter tag card와 routing embedding을 미리 컴파일해두면, runtime은 hidden state 기반 compact query로 registry를 조회한다.

$$
q_t = f_\psi(h_t,\mu_t,r_t,b_t)
$$

adapter 후보 utility는 다음처럼 둘 수 있다.

$$
u_{t,i}
=
q_t^\top e_i
+ \beta_1 \mathrm{match}(\ell_i, \hat{\ell}_t)
+ \beta_2 q_i
- \lambda_M m_i^{\mathrm{vram}}
- \lambda_T m_i^{\mathrm{latency}}.
$$

여기서 `e_i`는 adapter tag embedding, `ell_i`는 discrete tag set, `q_i`는 certification score와 calibration metadata, `m_i`는 memory/latency cost다. 이 routing은 language token 생성이 아니라 typed side-channel action이다.

Synthetic data에는 위험도 있다. taxonomy label이 visual style에 새어 들어가거나, synthetic shortcut이 real evaluation에서 무너질 수 있다. 따라서 Simula output은 항상 다음 split으로 관리한다.

```text
synthetic_train:
  Simula taxonomy로 만든 학습용 sample

real_holdout:
  synthetic 생성과 완전히 분리된 실제 이미지 검증 set

ood_branch:
  학습 taxonomy에 없거나 조합이 다른 branch

hard_negative:
  shortcut, pseudo marker, label leakage를 잡기 위한 반례 set

quarantine:
  critic 충돌, 낮은 confidence, 이상한 routing gain을 보인 sample
```

## 7. HydraLoRA Slot Hierarchy and Certified Registry

HydraLoRA는 본 제안에서 "이미 검증된 vision 해법"이 아니라 검증할 압축 가설이다. 원전의 shared-A/multi-B 관찰은 LLM fine-tuning 맥락에서 제시되었으므로, vision/VLM local skill에서도 그대로 성립한다고 단정하지 않는다. 본 제안은 이를 local visual skill bank를 조직하기 위한 후보 구조로 사용하고, 실험에서는 independent LoRA bank와 직접 비교한다.

역할 분리는 다음처럼 둔다.

```text
HydraLoRA:
  adapter parameter를 어떻게 공유하고 쪼갤지 정한다.
  shared-A / multi-B / top-k expert routing / slot composition을 담당한다.

Simula taxonomy:
  어떤 skill node가 필요한지 정한다.
  어떤 실패 유형을 어떤 adapter tag로 보낼지 정한다.
  router supervision과 registry metadata의 주소 체계를 만든다.
```

즉, HydraLoRA는 LoRA bank의 물리적 구조이고, Simula taxonomy는 의미적 주소 체계다.

Runtime에서는 adapter를 무제한 조합하지 않는다. V/X/L slot을 두고, 각 slot에서 0개 또는 1개 certified adapter bundle만 선택한다.

```text
V_slot:
  vision encoder 또는 visual feature adapter
  예: circuit_symbol_lora, document_visual_lora, ocr_visual_prior

X_slot:
  projector 또는 cross-modal grounding adapter
  예: text_grounding_lora, topology_grounding_lora, roi_grounding_lora

L_slot:
  language reasoning 또는 answer format adapter
  예: structured_answer_lora, verification_style_lora, stepwise_reasoning_lora
```

slot 내부는 shared-A/multi-B expert로 구성할 수 있다.

$$
\Delta W_t
=
\Delta W^V_t
+ \Delta W^X_t
+ \Delta W^L_t.
$$

Runtime rule:

```text
허용:
  certified bundle selection
  top-k active expert loading
  registry-defined scale 사용

금지:
  runtime LoRA training
  runtime pairwise compatibility search
  runtime scale sweep
  uncertified bundle loading
```

이 제한은 성능을 조금 보수적으로 만들 수 있지만, 현장 시스템에서는 예측 가능한 VRAM과 latency가 더 중요하다.

## 8. Runtime Controller, Fallback, and Graph Governance

ROI selector는 precision보다 recall을 우선한다. 중요한 ROI를 놓치면 local adapter가 아무리 좋아도 evidence acquisition loop 전체가 실패한다. 따라서 정책에는 fallback action을 둔다.

```text
fallback candidates:
  larger crop
  second scout
  emergency full-resolution pass under strict budget
  human/operator review
  graph-conflict reinspection
```

Adapter residency에는 hysteresis를 둔다. adapter를 매 step load/unload하면 VRAM은 아낄 수 있지만 latency가 튈 수 있다. 따라서 keep threshold와 evict threshold를 다르게 두어 불필요한 thrashing을 줄인다.

$$
\rho_{t,i}
=
\begin{cases}
\mathrm{keep}, & u_{t,i} - \lambda_A m_i > \tau_{\mathrm{keep}},\\
\mathrm{evict}, & u_{t,i} - \lambda_A m_i < \tau_{\mathrm{evict}},\\
\mathrm{hold}, & \text{otherwise},
\end{cases}
\quad
\tau_{\mathrm{keep}} > \tau_{\mathrm{evict}}.
$$

Graph memory는 최종 판정기가 아니라 belief accumulator다. Evidence가 들어왔다고 바로 확정 edge로 쓰지 않는다. 먼저 confidence calibration, conflict check, tentative update를 거친다.

```text
graph write flow:
  evidence extraction
  confidence calibration
  conflict check
  tentative graph update
  verifier 또는 추가 ROI로 확인
  commit / rollback / quarantine
```

상충하는 evidence는 버리지 않고 quarantine buffer에 둔다. 이후 정책은 그 conflict를 해소하기 위해 추가 ROI를 선택할 수 있다. 이 구조 덕분에 본 제안은 단순 crop/OCR pipeline이 아니라, local observation이 다음 observation policy를 바꾸는 closed evidence acquisition loop로 설명될 수 있다.

## 9. Evaluation Requirements

본 제안의 실험은 "최고 정확도 모델 찾기"가 아니라 "VRAM 절감 주장을 분해 측정하기"를 목표로 한다. 따라서 성능 지표와 serving 지표를 분리해야 한다.

최소 비교군:

```text
B0. base VLM, low-res only
B1. base VLM, full high-res
B2. low-res global + K ROI crops, no LoRA
B3. ROI crops + monolithic LoRA
B4. ROI crops + independent LoRA bank
B5. ROI crops + HydraLoRA shared-A bank
B6. HydraLoRA + Simula taxonomy router
B7. HydraLoRA + budget-conditioned top-k routing
```

측정 지표:

```text
task quality:
  accuracy
  macro F1
  OCR accuracy
  graph-edge F1
  conflict resolution rate
  OOD accuracy

memory and serving:
  visual token count
  peak allocated VRAM
  average VRAM
  reserved VRAM
  adapter resident memory
  KV cache estimate
  p50/p95 latency
  adapter load/unload count
  orchestration reserve pass/fail

routing:
  router accuracy
  top-k hit rate
  gate entropy
  expert utilization
  collapse rate
  abstention rate
  fallback success rate

graph governance:
  calibration error
  Brier score
  rollback rate
  quarantine rate
```

가장 중요한 결과표는 다음 질문에 답해야 한다.

```text
같은 task success 근처에서,
얼마나 적은 peak VRAM과 adapter resident memory로
planner/world model/verifier가 같이 뜰 공간을 남겼는가?
```

구체적인 dataset, split, seed, hardware, annotation schema, confidence interval은 M4 실험 제안서에서 확정한다.

## 10. Known Risks and Mitigations

첫째, HydraLoRA의 shared-A 가정이 vision/VLM local skill에서도 유지된다는 보장은 없다. 따라서 이를 전제하지 않고, independent LoRA bank, monolithic LoRA, HydraLoRA shared-A bank를 same-backbone 조건에서 비교한다.

둘째, ROI selector가 중요한 패치를 놓칠 수 있다. 이를 막기 위해 ROI 단계는 high precision보다 high recall을 우선하고, fallback과 missed-critical-evidence audit을 실험에 포함한다.

셋째, Simula synthetic curriculum은 shortcut, leakage, feedback loop를 만들 수 있다. Synthetic data는 real data를 대체하지 않고, residual taxonomy node를 보강하는 용도로 제한한다. Real-only holdout, OOD branch, hard negative set, quarantine gate를 필수 조건으로 둔다.

넷째, graph belief update는 calibration 가정에 민감하다. Graph memory를 최종 판정기가 아니라 belief accumulator로 제한하고, calibration error, conflict rate, rollback rate를 함께 측정한다.

다섯째, LoRA routing 자체가 runtime overhead를 만들 수 있다. 따라서 routing은 자연어 reasoning token이 아니라 compact registry query와 side-channel action으로 처리한다. 이 overhead도 router latency와 adapter load time으로 따로 측정한다.

마지막으로, 본 제안은 범용성을 아직 주장하지 않는다. 1차 검증 도메인은 회로도/PCB처럼 작은 local evidence가 전체 해석을 바꾸는 환경이다. Document extraction과 chart reading은 보조 전이 실험으로만 둔다.

## 11. Deliverables

이 제안서에서 파생될 산출물은 세 가지다.

```text
1. 발표 자료 v2
   이론 조사와 선행 연구 연결을 중심으로 구조와 방어 논리를 설명한다.

2. 실험 제안서 v1
   dataset, split, metric, ablation, logging을 포함한 pilot protocol을 별도 문서로 보존한다.
   발표 본문에서는 핵심 검증 방향만 요약하고, 세부는 Q&A 대응 자료로 사용한다.

3. Q&A 방어 대본
   LoRA 학습 비용, VRAM 실효성, crop pipeline, synthetic shortcut,
   graph calibration 질문에 대한 짧은 답변을 준비한다.
```

M5 발표에서는 이 문서의 구조를 그대로 읽지 않는다. 발표 본문은 LeWM/world model을 출발점으로 삼아, Simula의 taxonomy/curriculum 구조, Foveated Reasoning의 ROI action, LoRA routing, HydraLoRA의 계층적 adapter bank를 차례로 설명한다. 그 위에 budget-conditioned policy를 개인 제안으로 얹고, 실험 제안서는 "어떻게 검증할 것인가"에 대한 후속 카드로 사용한다.
