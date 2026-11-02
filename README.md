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
  - `WslCalisma` (default): a dedicated WSL distribution (`usta-kum`) with no access to Windows files (automount and
    interop off); code runs as an unprivileged user and every command in a network-less namespace (`unshare --net`).
    Used for the 157-task run. Limits (shared WSL2 kernel, `/mnt/wsl`) are documented in `tests/GUVENLIK.md`.
  - `YerelCalisma` (only with `USTA_CALISMA=yerel`, prints a warning): a temporary folder on the local machine, run
    through Git Bash. **There is no OS-level isolation and
    no network restriction in this mode** — only the checks above. The deny-list can be bypassed (e.g. `c''url`); it
    is a guard rail, not a sandbox. Used for the 34-task Spark run before `WslCalisma` existed — the security review then showed the model
    could read local key files through obfuscated paths, which is why it is no longer the default. (A bug we found here: on Windows the `bash` on PATH is WSL, which ran commands in the Linux home directory
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

Modes: (a) executor alone, (b) executor instructed to write and pass its own tests, (c) Usta (independent Spark
acceptance tests + arbiter + repair loop with rollback), (d) c + evidence-gated code review: once the acceptance tests
pass, Spark reads the task *and the code* and writes tests for suspected violations; only tests that fail on the
agent's code **and** pass on Spark's hidden reference solution are enforced. (In d the verifier sees the code, so it is
less independent than c.)

Every task runs in a fresh workspace; afterwards **hidden tests** — never shown to the agent or to Usta's test writer —
decide pass/fail. All tasks and hidden tests were generated by Muse Spark (≥6 explicit requirements per task, 12–20
hidden tests); a task entered a set only if Spark's reference solution passed all of its hidden tests. One run per task
and mode. Intervals: 95% Wilson (single rates) and task-level bootstrap (paired differences).

### Main result — 114 hard tasks × 3 runs (`zor3`), Spark executor, isolated WSL runner, 28–29 Oct

The strongest version of the verifier: three independent Spark test writers (edge cases / requirements / Turkish-local
rules), a test is kept only if at least 2 of the 3 writers' reference solutions pass it, then a mutation loop (Spark
writes 12–16 requirement-violating mutants of the reference; tests are added until they kill them, up to 2 rounds).
Tasks: 221 "very hard" Turkey-specific candidates passed the reference filter; a pilot run of (a) passed 164 of them
(74%). We kept the 57 the pilot failed plus 57 random ones it passed. The pilot run is **not** part of the results —
(a) was re-run. Every task and mode ran 3 times (1026 runs, 0 infrastructure errors).

| Mode | Pass rate (95% task-bootstrap CI) | "Done/verified" verdicts that were actually correct | Failed runs the system flagged |
|---|---|---|---|
| (a) executor alone | **60.2% (52–68)** | 201/321 (63%) | 16/136 (12%) |
| (b) + own tests | 56.7% (49–64) | 193/317 (61%) | 24/148 (16%) |
| (c) Usta | 57.6% (49–65) | 184/307 (60%) | 22/145 (15%) |

Paired over tasks: c − a −2.6 points (−9.1 … +3.2); c − b +0.9 (−4.7 … +6.1); b − a −3.5 (−7.6 … +0.9).
Acceptance tests per run ≈ 43 after filtering. Mutation score against the reference: 84% after the first round,
94% after strengthening — yet that did not translate into catching the executor's mistakes. A repair round ran in
38 of 342 c runs; rollback triggered once. Meta API cost of this run ≈ $17.6 (c ≈ $0.03 per run).

**Usta's "verified" verdict was no more reliable than the executor's own "done" (60% vs 63% correct), and it flagged
about as few failures (15% vs 12%).** The executor's errors here are mostly misreadings of the task that the verifier,
being the same model family, shares; strong mutation scores measure sensitivity to *small code changes*, not to
*interpretation* errors.

### Earlier run — 157 held-out tasks (`zor2`, h001–h157), single run per task

Generated after the method was frozen; never used for tuning.

| Mode | All hidden tests pass | Hidden tests passed | Meta API cost (157 runs) |
|---|---|---|---|
| (a) executor alone | 121/157 (77%; 70–83) | 96% | $1.13 |
| (b) + own tests | **134/157 (85%; 79–90)** | 97% | $1.27 |
| (c) Usta | 128/157 (82%; 75–87) | 96% | $1.69 |
| (d) Usta + evidence-gated review | 125/157 (80%; 73–85) | 96% | $2.23 |

Paired on the same tasks: c vs a **+4.5 points (−1.3 … +10.8)**; c vs b −3.8 (−9.6 … +1.9); d vs a +2.5 (−3.2 … +8.3);
d vs c −1.9 (−6.4 … +2.5). **No difference between modes is statistically significant.** The best point estimate is
(b), plain self-testing.

How often the verification actually acted: in c the acceptance tests failed and a repair round ran on 9 of 157 tasks;
in d on 20. d's review wrote 49 suspected-violation tests, 26 of them passed the evidence gate (on 13 tasks). In both c
and d, Usta reported "all acceptance tests pass" on 153 tasks, and the hidden tests still failed on 29 of those.

### Earlier runs — 34 tasks (`zor`, g07–g40)

| Mode | Glimmer 30B executor (Modal Sandbox, 27–28 Oct) | Spark executor (local runner, 28 Oct) |
|---|---|---|
| (a) executor alone | **20/34 (59%; 42–74)** | **30/34 (88%; 73–95)** |
| (b) + own tests | 14/34 (41%; 26–58) | 28/34 (82%; 66–92) |
| (c) Usta | 18/34 (53%; 37–69) | 29/34 (85%; 70–94) |
| c vs a, paired | −5.9 points (−14.7 … 0.0) | −2.9 points (−11.8 … +5.9) |
| Usta said "tests pass" but hidden tests failed | 15 of 33 | 5 of 34 |

The Glimmer column used an earlier method version (≈12 acceptance tests, no rollback); the analysis of that run
([`sonuclar/analiz_c_vs_a.md`](sonuclar/analiz_c_vs_a.md)) led to the requirement-by-requirement tests and rollback used
afterwards. g01–g06 were used for tuning and are excluded everywhere. Glimmer could not be re-run on the larger set:
our GPU budget ran out.

### What we read from this

- **Across three task sets, two executors and four verifier versions, Usta never significantly beat the executor alone.**
  The best Usta estimate was +4.5 points (zor2, CI −1.3 … +10.8); on the 3-run zor3 set it was −2.6.
- **Independent tests did not reliably catch what the executor missed.** The bottleneck is coverage, not repair: when
  the acceptance tests do not probe a requirement, the loop has nothing to fix. Even with 17–19 requirement-by-
  requirement tests, Usta said "pass" on 29 tasks whose hidden tests failed.
- **Correlated judges.** With the Spark executor the code, the acceptance tests and the hidden tests all come from the
  same model family; they share interpretations, so the verifier rarely disagrees with the executor, and the absolute
  pass rates are probably optimistic.
- **Self-testing: mixed.** It hurt Glimmer (stopped earlier, 41% vs 59%) but was the best mode with Spark on the large
  set. With N=34 and N=157 and one run per task, we cannot separate these effects from noise.
- **Fixed along the way (git history):** an interface contract that invented behaviour (now naming-only); ambiguous
  task text read differently by acceptance and hidden tests (arbiter); a repair round that broke working code
  (rollback); faulty LLM tests (reference filter); a race in our own spending counter (append-only ledger).
- **What Usta delivers:** a visible, reproducible record of what was checked, which tests passed in which round, and
  which were not enforced and why. In our measurements it does **not** raise the pass rate over the best baseline.

Before the hackathon (separate project, not in this repository) untrained Muse Glimmer 30B scored 88% on our Turkish
coding exam. A 6-task pilot on an "easy" set gave 100% in all modes, which is why we built the hard sets.
Meta API spend for everything in this repository: about $31 (counter in `kayitlar/`, not committed).

## Run it

Requirements: Python 3.12, a Meta Model API key, and the `usta-kum` WSL distribution (setup in `tests/GUVENLIK.md`). Modal is only needed for the
Glimmer executor and the network-isolated sandbox.

```bash
pip install -r requirements.txt
export META_MODEL_API_KEY=...                 # or put it in ~/.pflow-anahtarlar.env
python calistir.py                            # web UI at http://127.0.0.1:8765 (Spark executor, WSL runner)
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
python betikler/degerlendir.py --set zor2 --yurutucu spark --kipler a b c d --paralel 40
python betikler/degerlendir.py --set zor2 --yurutucu spark --ozet
python betikler/set_uret.py --zorluk zor --cikis veri/zor.jsonl    # generate a new task set (Spark)
```

Privacy: requests to `muse-spark-1.3-contributor` may be used by Meta for product development, and voice recordings
are sent to Meta for transcription. Do not send personal data.

## Repository

| Path | What |
|---|---|
| `sunucu/glimmer_modal.py` | Authenticated vLLM server for Muse Glimmer on Modal |
| `usta/ajan.py` | Agent loop (executor tool calls → workspace → results); Glimmer or Spark executor |
| `usta/arac.py` | Tools and runners (isolated WSL distribution — default; Modal Sandbox; local runner without isolation) |
| `usta/dogrulayici.py` | Spark naming contract, acceptance tests, reference-solution filter, arbiter |
| `usta/surec.py` | End-to-end pipeline and the a/b/c modes |
| `usta/spark.py` | Muse Spark client with a spending counter (stops at a set limit) |
| `usta/ses.py` | Muse Voice Transcribe client |
| `usta/web.py`, `usta/statik/` | Web UI (live steps over SSE, test badges, files) |
| `betikler/` | Evaluation-set generation, a/b/c evaluation, end-to-end check |
| `veri/` | Generated evaluation sets (tasks + hidden tests) |
| `sonuclar/` | Raw evaluation records and summary |
| `DEMO.md`, `sunum/` | Demo script, submission texts |

License: Apache 2.0.
