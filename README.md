# Usta — a Turkish coding agent that proves its own work

> **TR:** Usta'ya Türkçe bir yazılım görevi verirsiniz (yazıyla ya da sesle). Bir yürütücü model (açık ağırlıklı
> **Muse Glimmer** ya da **Muse Spark**) kodu araçlarla yazar ve çalıştırır; **Muse Spark** ise ayrı çağrılarda, ajanın
> kodunu görmeden, görev metninden bağımsız kabul testleri yazar. Testler kalırsa hata çıktısı ajana geri verilir; sonuç
> ekranı hangi testlerin kaç turda geçtiğini gösterir. Ölçümlerimiz, bu döngünün en güçlü tek-başına koşudan daha yüksek
> başarı sağlamadığını da gösteriyor; sayılar aşağıda.

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
 Muse Spark ── naming contract only if the task leaves file / function names open
        │                         │
        │                         └──(in parallel)── Muse Spark writes requirement-by-requirement acceptance tests
        ▼                                            + a reference solution; tests the reference fails are dropped
 Executor: Muse Glimmer 30B (open weights, vLLM on Modal H100)  or  Muse Spark (Meta Model API)
   native tool calls: Write / Read / Edit / Bash / Done, in a fresh workspace
        │
        ▼
 acceptance tests run ── pass → result screen with evidence
        │ fail
        ▼
 Muse Spark arbiter: does the task text clearly require this? ── unclear / faulty → not enforced, shown in report
        │ clearly required
        └──► failing output goes back to the executor (up to 3 rounds);
             a round that breaks a previously passing test is rolled back
```

- **Writer ≠ verifier.** The executor never sees the acceptance tests while working; the test writer never sees the
  code. The test file is rewritten before every run, so the agent cannot "fix" the tests. When Spark is also the
  executor, writer and verifier are separate calls of the same model — independent in context, not in training.
- **Faulty-test filter.** An LLM-written test can itself be wrong (in development Spark asserted an IBAN as valid
  whose mod-97 checksum is actually invalid; Glimmer's correct code failed 3 tests for 3 rounds). Spark therefore also
  writes a reference solution; tests that the reference fails are deselected. It cannot catch a mistake Spark makes
  consistently in both.
- **Workspaces.** Two runners share the same tool layer (path checks, command deny-list, 60 s timeout, output
  truncation, minimal environment without API keys):
  - `ModalCalisma`: a Modal Sandbox per task with `block_network=True` (verified: not even DNS resolves). Used for the
    Glimmer measurements.
  - `YerelCalisma`: a temporary folder on the local machine, run through Git Bash. **There is no OS-level isolation and
    no network restriction in this mode** — only the checks above. The deny-list can be bypassed (e.g. `c''url`); it
    is a guard rail, not a sandbox. Used for the Spark measurements and the current demo, because our Modal credit ran
    out. (A bug we found here: on Windows the `bash` on PATH is WSL, which ran commands in the Linux home directory
    instead of the workspace — Usta now accepts only Git Bash and checks `pwd` before running anything.)
- **Authenticated model endpoint.** The Glimmer server (`sunucu/glimmer_modal.py`) runs Meta's
  `vllm/vllm-openai:muse-glimmer` image with `--api-key`; unauthenticated requests get 401. It scales to zero after
  5 idle minutes.

## Meta tools used

| Tool | Role |
|---|---|
| **Muse Glimmer 30B** (open weights, Apache 2.0) | Executor; native tool calling via vLLM's `muse_glimmer` parser (verified: returns `tool_calls`). Measured on Modal H100. |
| **Muse Spark 1.3** (Meta Model API, `muse-spark-1.3-contributor`) | Verifier (naming contract, acceptance tests, reference solution, arbiter), evaluation-set generator, and — since the GPU budget ran out — alternative executor with native tool calls |
| **Muse Voice Transcribe 1.0** | Spoken Turkish task → text (realtime WebSocket API) |

## Measurement

Setup: (a) executor alone, (b) executor instructed to write and pass its own tests, (c) Usta (independent Spark tests
+ arbiter + repair loop). Every task runs in a fresh workspace; afterwards **hidden tests** — never shown to the agent
or to Usta's test writer — are run. The 40 hard tasks (≥6 explicit requirements each, 12–20 hidden tests) and their
hidden tests were generated by Muse Spark; a task entered the set only if Spark's reference solution passed all of its
hidden tests. g01–g06 were used while tuning the method and are excluded from the headline numbers. One run per task
and mode.

**Result: the expected ordering (c) > (b) > (a) did not hold with either executor.** The executor alone was best or
statistically tied.

Tasks g07–g40 (34 tasks), share of tasks where *all* hidden tests pass (95% Wilson interval):

| Mode | Glimmer 30B executor (Modal Sandbox, 27–28 Oct) | Spark executor (local runner, 28 Oct) |
|---|---|---|
| (a) executor alone | **20/34 (59%; 42–74)** | **30/34 (88%; 73–95)** |
| (b) + own tests | 14/34 (41%; 26–58) | 28/34 (82%; 66–92) |
| (c) Usta | 18/34 (53%; 37–69) | 29/34 (85%; 70–94) |
| c vs a, paired (task bootstrap 95% CI) | −5.9 points (−14.7 … 0.0) | −2.9 points (−11.8 … +5.9) |
| c vs b, paired | +11.8 points (0.0 … +26.5) | +2.9 points (−8.8 … +17.6) |
| Usta said "tests pass" but hidden tests failed | 15 of 33 | 5 of 34 |

Between the two runs we changed the method based on the Glimmer analysis (requirement-by-requirement acceptance tests,
12–20 instead of ~12; rollback on regression), so the two columns differ in executor, runner *and* method version.
Raw records: [`sonuclar/`](sonuclar/); task-by-task analysis of the Glimmer run:
[`sonuclar/analiz_c_vs_a.md`](sonuclar/analiz_c_vs_a.md).

What we read from this:
- **The loop is limited by test coverage.** In 12 of the 16 Glimmer tasks Usta failed, its acceptance tests passed and
  the hidden tests failed on the *same* requirements as the executor alone — the bug was never detected, so the repair
  loop never ran. With the Spark executor the acceptance tests passed in the first round on all 34 tasks: the repair
  loop never triggered at all, and c vs a is run-to-run noise.
- **Self-testing can hurt.** Telling Glimmer to write and pass its own tests (b) made it stop earlier (8.5 vs 13.2
  steps) and pass fewer tasks; its tests share its misreadings. Usta's independent tests recovered most of that loss.
- **Correlated judges.** With the Spark executor, the code, the acceptance tests and the hidden tests all come from the
  same model family, so they share interpretations — this likely inflates the Spark column and explains why the
  verifier rarely disagrees with the executor.
- Failure modes found and fixed along the way (all in the git history): an interface contract that invented
  behaviour (now naming-only); ambiguous task text read differently by acceptance and hidden tests (Spark arbiter);
  a repair round that broke previously working code (rollback); faulty LLM tests (reference filter).
- What Usta does deliver: a visible, reproducible record of what was checked, which tests passed in which round, and
  which were not enforced and why. It does not, in our measurements, raise the pass rate over the best baseline.

Before the hackathon (separate project, not part of this repository) untrained Muse Glimmer 30B scored 88% on our
Turkish coding exam. On a first "easy" set, a 6-task pilot gave 100% for all three modes, which is why we built the
hard set. Total Meta API spend for everything in this repository so far: about $1.6.

## Run it

Requirements: Python 3.12, Git Bash on Windows (or bash elsewhere), a Meta Model API key. Modal is only needed for the
Glimmer executor and the network-isolated sandbox.

```bash
pip install -r requirements.txt
export META_MODEL_API_KEY=...                 # or put it in ~/.pflow-anahtarlar.env
python calistir.py                            # web UI at http://127.0.0.1:8765 (Spark executor, local runner)
```

With Glimmer on Modal (H100, ~$4/h):

```bash
python -c "import secrets;print('USTA_GLIMMER_TOKEN='+secrets.token_urlsafe(32))" > .env
modal deploy sunucu/glimmer_modal.py          # first start ~3 min
USTA_CALISMA=modal python calistir.py         # pick "Muse Glimmer" in the UI
modal app stop -y usta-glimmer                # stop the GPU when done
```

Evaluation:

```bash
python betikler/degerlendir.py --set zor --yurutucu spark --kipler a b c --paralel 10
python betikler/degerlendir.py --set zor --yurutucu spark --ozet
python betikler/set_uret.py --zorluk zor --cikis veri/zor.jsonl    # generate a new task set (Spark)
```

Privacy: requests to `muse-spark-1.3-contributor` may be used by Meta for product development, and voice recordings
are sent to Meta for transcription. Do not send personal data.

## Repository

| Path | What |
|---|---|
| `sunucu/glimmer_modal.py` | Authenticated vLLM server for Muse Glimmer on Modal |
| `usta/ajan.py` | Agent loop (executor tool calls → workspace → results); Glimmer or Spark executor |
| `usta/arac.py` | Tools and runners (Modal Sandbox; local Git Bash runner without network isolation) |
| `usta/dogrulayici.py` | Spark naming contract, acceptance tests, reference-solution filter, arbiter |
| `usta/surec.py` | End-to-end pipeline and the a/b/c modes |
| `usta/spark.py` | Muse Spark client with a spending counter (stops at a set limit) |
| `usta/ses.py` | Muse Voice Transcribe client |
| `usta/web.py`, `usta/statik/` | Web UI (live steps over SSE, test badges, files) |
| `betikler/` | Evaluation-set generation, a/b/c evaluation, end-to-end check |
| `veri/` | Generated evaluation sets (tasks + hidden tests) |
| `sonuclar/` | Raw evaluation records and summary |
| `DEMO.md` | 3-minute demo script |

License: Apache 2.0.
