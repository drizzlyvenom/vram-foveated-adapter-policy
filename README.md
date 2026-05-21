# VRAM-Constrained Foveated Adapter Policy

이 프로젝트는 제한된 VRAM 환경에서 피지컬 AI의 perception, world model, planner, verifier가 함께 상주할 수 있도록 하는
`Budget-Conditioned Foveated Adapter Policy` 설계와 발표/실험 제안 자료를 정리한 작업 폴더입니다.

핵심 아이디어는 다음 세 축으로 정리합니다.

- `Simula`: offline taxonomy와 synthetic/replay curriculum을 이용해 adapter tag와 router supervision을 준비하는 단계
- `HydraLoRA`: 계층형 LoRA adapter bank와 resident set을 관리하는 물리적 adapter 구조
- `Runtime policy`: VRAM budget, token cost, adapter residency, orchestration reserve를 조건으로 ROI와 adapter를 선택하는 정책

## 주요 산출물

- 정책 제안서: `output/policy/budget_conditioned_foveated_adapter_policy_proposal_ko.md`
- 실험 제안서: `output/experiment/experiment_proposal_ko.md`
- 발표 자료: `output/presentation/foveated_hydralora_policy_talk_ko_v2.pptx`
- 발표 대본 최종본: `output/presentation/m5_user_script_final_ko.docx`
- 소논문 초안: `output/paper/foveated_hydralora_arxiv.tex`
- arXiv PDF 초안: `output/paper/foveated_hydralora_arxiv.pdf`
- 한국어 소논문 PDF: `output/paper/foveated_hydralora_korean.pdf`

## 폴더 구조

```text
output/
  experiment/   실험 제안서와 pilot 관련 산출물
  paper/        논문 형식 초안, 한국어 초안, 빌드된 PDF
  policy/       최종 정책 제안서
  presentation/ 발표 자료, 최종 대본, 이미지 asset
    assets/     발표용 생성 이미지
```

## 현재 후속 방향

발표 준비 단계는 마무리되었고, 다음 단계는 RTX 3090에서 검증 가능한 pilot을 먼저 닫은 뒤 더 큰 장비로 확장하는 것입니다.
Stage 0은 기존 3090 cost simulation 결과를 replay해 logging contract를 검증하고, Stage 1은 실제 VLM profiler로 foveation-only validation을 진행합니다.

실험은 최고 정확도 경쟁보다 다음 항목을 분해 측정하는 방향으로 둡니다.

- peak allocated VRAM
- adapter resident memory
- p95 latency
- orchestration reserve pass/fail
- adapter routing hit/miss와 fallback 빈도

## Verification Pilot

- 검증 ladder: `docs/verification_ladder.md`
- 측정/로그 계약: `docs/measurement_and_logging.md`
- 실패 분석 playbook: `docs/failure_analysis_playbook.md`
- Stage 0 설정: `configs/pilot_minimal.yaml`
- Stage 1 데이터셋 후보: `docs/stage1_dataset_shortlist_ko.md`

Stage 0은 기존 RTX 3090 cost simulation 결과를 새 logging contract로 replay하는 단계입니다. 실제 VLM profiler 측정은 Stage 1부터 진행합니다.

Stage 0 재현:

```powershell
python -m pip install -r requirements.txt
python scripts\run_pilot.py --config configs\pilot_minimal.yaml
```
