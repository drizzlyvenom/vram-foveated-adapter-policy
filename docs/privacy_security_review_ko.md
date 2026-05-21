# Privacy and Security Review

Status: passed
Date: 2026-05-21
Scope: Stage 1 smoke validation changes

## 1. 검토 범위

검토 대상:

```text
README.md
requirements.txt
configs/
docs/
schemas/
scripts/
src/
```

로컬 산출물과 다운로드 데이터는 검토하되 git에는 포함하지 않는다.

```text
runs/
data/
hf_cache/
vfa_verification_guidelines/
```

## 2. 개인정보/민감정보 확인

다음 패턴을 커밋 후보에서 검색했다.

```text
로컬 절대 경로
사용자 홈 경로
API key / token / secret / password
private key
내부 호칭 또는 회의용 표현
```

결과:

```text
민감정보 발견 없음
하드코딩된 개인 로컬 경로 발견 없음
API key/token/secret/password 발견 없음
다운로드 이미지와 manifest는 data/ 아래에 있으며 gitignore 적용됨
실행 결과 JSONL/CSV는 runs/ 아래에 있으며 gitignore 적용됨
```

## 3. 보안 확인

Python 스크립트 기준으로 확인한 사항:

```text
shell=True 사용 없음
eval/exec 사용 없음
pickle 사용 없음
yaml.load 대신 yaml.safe_load 사용
subprocess는 git commit hash 조회에만 사용하며 shell을 거치지 않음
```

다운로드 스크립트 보강:

```text
scripts/prepare_stage1_dataset.py
- 이미지 다운로드 URL을 https://datasets-server.huggingface.co/assets/... 로 제한
- config의 manifest/image 경로가 repo 밖으로 나가면 거부
```

Stage 1 실행 스크립트 보강:

```text
scripts/run_stage1_foveation.py
- manifest와 image_path가 repo 밖으로 나가면 거부
```

## 4. 남은 주의점

이번 Stage 1은 공개 Hugging Face 데이터셋의 이미지를 로컬에 다운로드한다. 해당 원본 이미지는 공개 데이터셋 샘플이지만, repo에는 포함하지 않는다.

Stage 1 결과 문서에는 정답 텍스트나 이미지 원본을 싣지 않고 aggregate metric만 기록했다.

## 5. 결론

현재 커밋 후보는 공개 저장소에 올려도 되는 상태로 판단한다.
