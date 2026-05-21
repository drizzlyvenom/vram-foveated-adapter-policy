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
  paper/        arXiv 형식 초안, 한국어 초안, 빌드된 PDF
  policy/       최종 정책 제안서
  presentation/ 발표 자료, 최종 대본, 이미지 asset
    assets/     발표용 생성 이미지
local_workbench/ 푸시하지 않는 로컬 작업 메모, 중간 초안, 참고 PDF
trashbin/       삭제 대신 보류한 레거시/임시 산출물
```

## 현재 후속 방향

발표 준비 단계는 마무리되었고, 다음 단계는 실험 환경을 확인한 뒤 작은 pilot으로 넘어가는 것입니다.
Mac mini 또는 다른 테스트 머신을 사용할 경우, chip family, unified memory, macOS, storage, MPS/MLX/llama.cpp/Ollama 사용 가능 여부를 먼저 확인한 뒤 실험 범위를 좁힙니다.

실험은 최고 정확도 경쟁보다 다음 항목을 분해 측정하는 방향으로 둡니다.

- peak allocated VRAM
- adapter resident memory
- p95 latency
- orchestration reserve pass/fail
- adapter routing hit/miss와 fallback 빈도

## Git 주의점

`output/experiment/3090_pilot_costsim/`은 별도 Git 저장소로 관리된 pilot repo입니다.
상위 프로젝트에 실수로 embedded git repo 또는 submodule처럼 섞이지 않도록 기본 `.gitignore`에서 제외합니다.

`local_workbench/`에는 발표 준비 중 만든 체크리스트, 중간 초안, 검토 메모, 원본 참고 PDF처럼 푸시하지 않을 작업 편의 자료를 둡니다.
