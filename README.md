# Tools, Facts, and Checks

POSTECH CSED490E (대학원 자연어처리) 5조 프로젝트.

LLM은 수학 문제를 풀 때 프로그램을 짜서 실행하곤 합니다(예: 계산기하, OR-Tools 최적화). 그런데 이 프로그램은 오류 없이
틀린 답을 낼 수 있습니다. 이 프로젝트는 **언제 틀리고, 가장 싸게 고치는 방법은 무엇인지** 연구합니다.

| 실수 | 가장 싼 해결책 | 결과 |
|---|---|---|
| 라이브러리 함수를 모름 | 정확한 사용법 5줄 제공 | 최적해 23% → 77–90% (더 오래 생각하기: 3%) |
| 불필요한 도구에 끌려감 | 도구 있는/없는 프로그램을 비교, 답이 다를 때만 생각 | 99% (항상 생각 98%), 토큰 27% 절약 |
| 문제가 어려움 | 예제를 틀릴 때만 더 생각 | 같은 66%, 토큰 18% 절약 |
| 같은 문제가 반복됨 | 검증한 프로그램 하나를 재사용 | 유효 94% (매번 새로 짜기 7%) |

자세한 내용: `PROPOSAL_ko.md`(제안서), `PROPOSAL_slides.pptx`(발표 자료), `docs/README.md`(실험 목록).

## 폴더

```
PROPOSAL*.md, PROPOSAL_slides.pptx   제안서, 발표 자료
docs/       연구 기록(FINDINGS.md), 실험별 사전 등록·결과(prereg/), 메모(notes/)
poc/        코드: run_*.py 실험, analyze_*.py 분석, queues/ 실제 실행 명령
results/    벤치마크 입력과 참조 해 (모델 출력 *.jsonl, 로그는 git 제외)
figs/       그림
```

## 실행

```bash
pip install -r poc/requirements.txt sympy math-verify pandas
bash poc/start_server.sh <모델 폴더> 8041 <GPU> 0.88 <태그>   # vLLM 서버 (OpenAI 호환)
export POC_BASE_URL=http://127.0.0.1:8041/v1
export POC_REASONING_EFFORT=medium                            # gpt-oss만: low | medium | high
python poc/sanity_check.py                                    # 모델 없이 하네스 점검
```

| 실험 | 명령 예시 |
|---|---|
| 기하 + 불필요한 도구 (슬라이드 7) | `python poc/run_geo_cross.py --model_tag S2_N10_geo_k8_s1 --distract 8 --seed 1 --temperature 0.7` |
| 최적화 + 문서 (슬라이드 6) | `python poc/run_co.py --model_tag S2_N10_co_snippet_s1 --arms solver --api_doc --api_doc_task --seed 1 --temperature 0.7` |
| 대회 기하 문제 (슬라이드 8) | `CC_SET=full python poc/run_cc.py run oss120_medium 1 --max_tokens 16000` |
| 프로그램 재사용 (슬라이드 9) | `POC_REASONING_EFFORT=low python poc/run_solomon.py run oss120_low_plain 1` → `REUSE_SEEDS=1 python poc/analyze_reuse_curve.py oss120_low_plain` |
| 잡숍 / 경시 수학 / 최적화 모델링 / Lean | `poc/run_jssp.py`, `run_math.py`, `run_nlopt.py`, `run_lean.py` (사용법은 각 파일 맨 위 설명) |

각 실험의 전체 명령은 `poc/queues/queue_s2_<id>.sh`, 결과는 `results/`에 저장됩니다.

**참고:** 스크립트에 경로 `/NAS/SJ/POSTECH/nlp`가 고정되어 있으니 다른 머신에서는 바꿔 주세요. GPU는 공유하므로
`nvidia-smi`로 빈 GPU와 포트를 확인하세요. 결과는 시드 3개에서 성립할 때만 주장합니다.
