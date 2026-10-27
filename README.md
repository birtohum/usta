# Usta — a Turkish coding agent that proves its own work

> **TR:** Usta'ya Türkçe bir yazılım görevi verirsiniz (yazıyla ya da sesle). Açık ağırlıklı **Muse Glimmer** kodu ağı
> kapalı bir sandbox'ta yazar ve çalıştırır; **Muse Spark** ise görev metninden, ajanın kodunu görmeden, bağımsız kabul
> testleri yazar. Testler kalırsa hata çıktısı Glimmer'a geri verilir; sonuç ekranı hangi testlerin kaç turda geçtiğini
> gösterir. "Bitti" demek yetmez — Usta kanıt gösterir.

Built for the Meta Global AI Developer Hackathon (Indie track, theme *Build for Your World*).
All code in this repository was written during the hackathon (27 Oct – 4 Nov 2026); see the git history.

## Why

Turkish-speaking developers and small businesses have few agents that work in their language, and agents in general
say "done" without showing that the result actually works. We measured untrained Muse Glimmer 30B on our Turkish coding
exam before the hackathon (88%): the capability is there. What is missing is **reliability** — a loop that checks the
work independently and shows the evidence.

## How it works

```
 Turkish task (text, or voice → Muse Voice Transcribe)
        │
        ▼
 Muse Spark ── writes an interface contract (file / function names, signatures, error behaviour)
        │                         │
        │                         └──(in parallel)── Muse Spark writes acceptance tests + a reference solution
        ▼                                            the tests are run against the reference in a separate sandbox;
 Muse Glimmer 30B (open weights, vLLM on Modal H100)     tests the reference also fails are dropped as faulty
   native tool calls: Write / Read / Edit / Bash / Done
   inside a Modal Sandbox with networking disabled
        │
        ▼
 acceptance tests run ── pass → result screen with evidence
        │ fail
        ▼
 Muse Spark arbiter: does the task text clearly require this? ── unclear / faulty → not enforced, shown in report
        │ clearly required
        └──► failing output goes back to Glimmer (up to 3 rounds)
```

- **Writer ≠ verifier.** Glimmer sees the contract, never the acceptance tests while working. Spark never sees
  Glimmer's code. The test file is rewritten before every run, so the agent cannot "fix" the tests.
- **Faulty-test filter.** An LLM-written test can itself be wrong (in development Spark asserted an IBAN as valid
  whose mod-97 checksum is actually invalid; Glimmer's correct code failed 3 tests for 3 rounds). Spark therefore also
  writes a reference solution; tests that the reference fails are deselected. This catches wrong expectations that
  the reference computes correctly; it cannot catch a mistake Spark makes consistently in both.
- **Isolation.** Each task gets its own Modal Sandbox (`block_network=True` — not even DNS resolves; verified), working
  directory `/work`. Paths outside the workspace and network / privilege / package-install commands are rejected
  before execution, commands time out after 60 s and output is truncated.
- **Authenticated model endpoint.** The Glimmer server (`sunucu/glimmer_modal.py`) runs Meta's
  `vllm/vllm-openai:muse-glimmer` image with `--api-key`; unauthenticated requests get 401. It scales to zero after
  5 idle minutes.

## Meta tools used

| Tool | Role |
|---|---|
| **Muse Glimmer 30B** (open weights, Apache 2.0) | The executor agent; native tool calling via vLLM's `muse_glimmer` parser (verified: returns `tool_calls`) |
| **Muse Spark 1.3** (Meta Model API) | Interface contract, independent acceptance tests, reference solution; also generated the evaluation sets |
| **Muse Voice Transcribe 1.0** | Spoken Turkish task → text (realtime WebSocket API) |

## Measurement

**Result (hard set, 27–28 Oct 2026): the expected ordering (c) > (b) > (a) did not hold.** Glimmer alone was best.

Tasks g07–g40 (34 tasks not looked at while tuning the method):

| Mode | All hidden tests pass | Hidden tests passed | Avg. Glimmer steps | Avg. Glimmer tokens | Spark cost |
|---|---|---|---|---|---|
| (a) Glimmer alone | **20/34 (59%; 95% CI 42–74)** | 94% | 13.2 | 81k | – |
| (b) Glimmer + own tests | 14/34 (41%; 26–58) | 89% | 8.5 | 58k | – |
| (c) Usta | 18/34 (53%; 37–69) | 92% | 9.6 | 66k | $0.08 total |

Paired, same task: c vs a — only c passed 0, only a passed 2 (difference −5.9 points, 95% task-bootstrap CI −14.7 … 0.0).
c vs b — only c passed 5, only b passed 1 (+11.8 points, CI 0.0 … +26.5). Intervals are Wilson (single rates) and task-level bootstrap (paired).
All 40 tasks: a 25/40, b 19/40, c 23/40. Raw per-run records: [`sonuclar/`](sonuclar/).

What we read from this (single run per task and mode, so differences of 1–3 tasks are noise):
- Asking Glimmer to write and pass its own tests (b) made it stop earlier (8.5 vs 13.2 steps) and pass fewer tasks.
  Glimmer's own tests share its misreadings of the task, so "my tests pass" became a premature stop signal.
- Usta's independent tests recovered most of that loss (c vs b: +5 / −1) but did not beat letting Glimmer work
  without the testing instruction. The verification loop's value here is **evidence and catching premature
  "done"**, not a higher pass rate than the strongest baseline.
- Two failure modes we found and fixed during development, both visible in the history: (1) Spark's interface
  contract invented behaviour rules not in the task, and the acceptance tests enforced them, so Glimmer broke correct
  code — the contract is now naming-only; (2) when the task text admits two readings, the acceptance test and the
  hidden test can pick different ones — a Spark **arbiter** now only enforces failing tests the task clearly requires.
- Total Muse Spark spend for all of this (contracts, tests, arbiter, generating both task sets): **$0.38**.

Setup: (a) Glimmer alone, (b) Glimmer instructed to write and pass its own tests, (c) Usta (independent Spark tests +
repair loop). Every task runs in a fresh sandbox; afterwards **hidden tests** — never shown to the agent or to Usta's
test writer — are run. Tasks and hidden tests were generated by Muse Spark, not hand-written; a task entered the set
only if Spark's reference solution passed all of its hidden tests in the sandbox.

Honest caveats:
- On the first ("easy") set, a 6-task pilot gave 100% for all three modes — the tasks were too easy to separate them.
  We therefore generated a harder set (≥6 explicit requirements per task, 12–20 hidden tests).
- The hidden tests and Usta's acceptance tests are written by the same model (Spark), in separate calls without
  access to each other. Their errors may be correlated.
- N=40, one run per task and mode; differences of a few tasks are within noise.
- g01–g06 were used while tuning the method (contract, arbiter); the headline table excludes them.

## Run it

Requirements: Python 3.12, a Modal account, a Meta Model API key.

```bash
pip install -r requirements.txt
python -c "import secrets;print('USTA_GLIMMER_TOKEN='+secrets.token_urlsafe(32))" > .env
modal deploy sunucu/glimmer_modal.py          # Glimmer on an H100; first start ~3 min
export META_MODEL_API_KEY=...                 # or put it in ~/.pflow-anahtarlar.env
python calistir.py                            # web UI at http://127.0.0.1:8765
modal app stop -y usta-glimmer                # stop the GPU when done
```

Evaluation:

```bash
python betikler/set_uret.py --zorluk zor --cikis veri/zor.jsonl    # generate a task set (Spark)
python betikler/degerlendir.py --set zor --kipler a b c --paralel 12
python betikler/degerlendir.py --set zor --ozet
```

Privacy: requests to `muse-spark-1.3-contributor` may be used by Meta for product development, and voice recordings
are sent to Meta for transcription. Do not send personal data.

## Repository

| Path | What |
|---|---|
| `sunucu/glimmer_modal.py` | Authenticated vLLM server for Muse Glimmer on Modal |
| `usta/ajan.py` | Agent loop (Glimmer tool calls → sandbox → results) |
| `usta/arac.py` | Tools and isolated runners (Modal Sandbox; local mode for development only) |
| `usta/dogrulayici.py` | Spark contract, acceptance tests, reference-solution filter |
| `usta/surec.py` | End-to-end pipeline and the a/b/c modes |
| `usta/spark.py` | Muse Spark client with a spending counter (stops at a set limit) |
| `usta/ses.py` | Muse Voice Transcribe client |
| `usta/web.py`, `usta/statik/` | Web UI (live steps over SSE, test badges, files) |
| `betikler/` | Evaluation-set generation, a/b/c evaluation, end-to-end check |
| `veri/` | Generated evaluation sets (tasks + hidden tests) |
| `sonuclar/` | Raw evaluation records and summary |
| `DEMO.md` | 3-minute demo script |

License: Apache 2.0.
