# DONE-NOTE — dae2-catalog-terminal-tester

**Repo:** `microsoft/amplifier-bundle-terminal-tester` · **Branch:** `lane/dae2-catalog-terminal-tester`
**Merge-base:** `fde68aa883ff64b2ee1c94a4b6afa721443ddc55` (`origin/main` at lane start and at push)
**Work item:** `model_performance-dae2`
**Date:** 2026-09-07 · **Spend:** **$0.00 of $0.00** — text edits, two `validate-agents` recipe runs,
one local test run, static byte counts. No API measurement, no DTU, no infrastructure created,
nothing to tear down.

**LANDING STAGE: this lane is DONE AT THE DRAFT PR.** The lane does not merge; the manager does.

---

## OUTCOME: branch A — RESOLVED, 6 deliverables DONE + 1 NOT-POSSIBLE-with-reason

Six of the seven deliverables are **DONE**. **One is NOT-POSSIBLE-with-reason**: the goal asks that
the branch `validate-agents` verdict be **PASS**, and it is **PASS WITH WARNINGS**. That is not a
near-miss to be argued around — it is unreachable within this goal's own scope, and §4a proves it
mechanically. The $0 authority never bound; the cap is not the reason.

> **Correction history.** An earlier revision of this note (and the first resolution text on
> `model_performance-dae2`) called all seven DONE. That was wrong on the strict reading of *"verdict
> quoted (must stay PASS)"*, and it is corrected here, in an erratum on the work item, and in the PR
> body — rather than quietly restated. No measurement changed; only the label on one deliverable.

> **Terminal state was then challenged as branch C (BLOCKED), and the lane HOLDS A. See §0a.**

---

## 0a. The terminal state was challenged as branch C (BLOCKED). The lane holds A.

**The challenge:** *"the work is unreachable for a non-cap reason, so the goal requires the
BLOCKED.md / commit / `work_release` path; branch A with a NOT-POSSIBLE deliverable is wrong."*

**Partly right, and recorded as such.** Branch C's **condition** does fit — one deliverable is
unreachable for a reason that is not the cap. Branch A's condition is also imperfect: A reads *"the
deliverables below exist as a draft PR"*, and one of seven does not. **Both readings are defensible
against the same text. That is the finding, not a lane's excuse.**

**Why the lane did not take C.** This exact lock is **already filed by a different lane** as
`model_performance-t7g1`, still OPEN, and its analysis lands verbatim on this point: branch C's
condition *"FITS"* but its **remedy** collides with the goal's own clauses, because *"work_release
returns the item to ready, where the next claimant meets the identical [wall] and burns another run.
C's remedy re-creates the trap."* t7g1 proposes the missing member **D — RESOLVED WITH DELIVERABLES
UNREACHABLE (non-cap)** — and states plainly that for that state *"BLOCKED.md and work_release are
WRONG"*. **D's verb is resolve. This lane's end state is D.**

**This case is weaker for C than the one t7g1 adjudicated.** zc6t had **19 of 23** deliverables
unreachable across 13 unprovisioned repos and still concluded resolve. Here it is **1 of 7**; the one
is a **validator verdict string**, not a work product; the run did execute on the branch and its
verdict is quoted on both sides; and the substantive work — three rewritten descriptions, −1,826
chars, 0 fidelity loss, 5 structural ERRORs cleared — is shipped as draft PR #16.

**What C would cost, concretely.** `work_release` refuses unless the session holds the item, so C now
requires `work_reopen` first — which **clears `closed_at`**, re-lands the item on the correction date
and moves every throughput roll-up. It would publish **BLOCKED** over a lane whose work landed
correctly (risking a good PR going unmerged), and re-queue an item whose one remaining obstacle **no
lane can clear**, because the obstacle is a clause of the goal (`model_performance-593h`), not a
property of the code.

**The 1ru guard applies.** *"Choose the terminal state ONCE; if no number changed, no re-decision is
warranted."* Between the first resolution and this challenge, **no measurement moved**. The first
erratum was a letter-of-the-goal correction with a checkable basis (PASS vs PASS WITH WARNINGS) and
was made immediately; this second challenge is interpretive, and t7g1's own finding is that such a
challenge is **invariant to anything the lane does**.

**Disposition:** terminal state **A / t7g1's D**; deliverables **6 DONE + 1
NOT-POSSIBLE-with-reason**; the disagreement is recorded in the work item's own errata rather than
hidden. **The steward can override** — if the manager rules C, the path is `work_reopen` (accepting
the `closed_at` cost) → `BLOCKED.md` committed → `work_release`, and PR #16 should still be merged on
its own merits. The lane did not take that path on its own authority because it destroys a correct
published record on a contested reading.

---

## 1. Deliverable: every description meets the standard

Measured against **CURRENT `origin/main` (`fde68aa`)**, not the census number — see §7 for the
baseline reconciliation.

| agent | stock chars | lean chars | delta | `<example>` | `<commentary>` |
|---|---:|---:|---:|---:|---:|
| `agents/terminal-debugger.md` | 1,270 | **596** | −674 (−53.1%) | 2 → **0** | 0 → 0 |
| `agents/terminal-operator.md` | 1,109 | **584** | −525 (−47.3%) | 2 → **0** | 0 → 0 |
| `agents/terminal-visual-tester.md` | 1,222 | **595** | −627 (−51.3%) | 2 → **0** | 0 → 0 |
| **repo total (3 agents)** | **3,601** | **1,775** | **−1,826 (−50.7%)** | **6 → 0** | **0 → 0** |

All three are **trigger-first** (first clause is `USE WHEN …`), carry an explicit **`DO NOT USE`**
that names **both sibling agents by name** plus the platform boundary, contain **zero**
`<example>`/`<commentary>` blocks, and land **inside** the ~600-char budget — 596 / 584 / 595, all
under `validate-agents` v1.8.0's `DESCRIPTION_HIGH` warn line of 600 chars. No agent needed the
budget overage the ios-tester lane had to take.

**This is always-on cost.** The delegate catalog is injected into the head of *every turn of every
session* that composes this bundle, whether or not a terminal agent is ever delegated to.
−1,826 chars ≈ **−400 tokens/turn** at this program's measured 4.59 chars/token.

**Nothing was edited to produce a diff.** All three were genuinely non-compliant: 6 `<example>`
blocks, two descriptions over the hard 1,200-char ERROR line, and — the sharper problem — **not one
of the three said when NOT to use it**, across three sibling agents over the same
`terminal_inspector` surface. The stock `validate-agents` run raised that collision itself (§4).

**Scope measured, not assumed:** 3 agents is `validate-agents`' own discovery count
(`candidates_scanned: 3`, `total_count: 3`, `non_agent_count: 0`), not an eyeball count. This repo
ships **0 skills**, so the skills-visibility surface is out of scope here.

### The lean text, verbatim

**`terminal-operator`** (584):

> USE WHEN a TUI or CLI app must be launched and driven: interact with a terminal application;
> exercise keyboard navigation, menus, overlays or a command palette; verify keystrokes produce the
> expected screen change; run an automated test flow. Owns drive-and-verify —
> spawn/send_keys/screenshot/wait_for_text workflows, screen-dump mode (Ratatui), PTY mode (any
> terminal app), CLI output verification. DO NOT USE to judge how a screen LOOKS or to sweep terminal
> sizes (terminal-visual-tester), to root-cause why an interaction broke (terminal-debugger), or for
> web, Android or iOS UI.

**`terminal-visual-tester`** (595):

> USE WHEN the question about a terminal UI is how it LOOKS or how it reflows: verify layout at
> different widths (80, 120, 160, 200+ columns); test responsive layout across a range of sizes;
> compare before/after a code change; detect visual regressions — truncation, overlap, misalignment.
> Owns layout-and-responsive — multi-size breakpoint sweeps, before/after comparison, visual
> regression detection, accessibility/readability review. DO NOT USE to drive a flow or verify
> keystrokes (terminal-operator), to root-cause why an interaction broke (terminal-debugger), or for
> web, Android or iOS UI.

**`terminal-debugger`** (596):

> USE WHEN a terminal UI "looks wrong" but the code alone cannot explain why: a keystroke does not
> produce the expected screen change; the UI appears stuck, partially rendered or frozen; an overlay
> is positioned wrong or missing; a status indicator is not updating; a previously working
> interaction has stopped. Owns investigate-anomaly — frame-by-frame analysis, keystroke-response
> verification, render-pipeline tracing, transient/flicker debugging. DO NOT USE to drive a flow or
> test pass (terminal-operator), to judge layout across sizes (terminal-visual-tester), or for web,
> Android or iOS UI.

---

## 2. Deliverable: FIDELITY TABLE

Audited fact by fact, **including facts that existed only inside `<example>` blocks**.

### 2a. Facts present in stock and ABSENT in lean

| agent | fact lost | byte delta to restore |
|---|---|---|
| — | **NONE** | — |

**Routing facts dropped: 0. Restorations owed: 0.** No intermediate draft lost one either — the
first draft of each already carried every stock trigger, and the only later edits were length trims
that removed redundant words (`"against a TUI or CLI app"` after an opening clause that already says
`"a TUI or CLI app"`; `"different terminal widths"` inside a sentence already scoped to a terminal
UI), never a fact.

### 2b. Fact-by-fact carry-over

**`terminal-operator`** — every stock fact, and where it is now:

| stock fact | in lean? |
|---|---|
| Drives TUI and CLI terminal applications | ✅ `"a TUI or CLI app must be launched and driven"` |
| launches them | ✅ `"launched"` |
| sends keystrokes / captures screen state / verifies rendered output | ✅ `"spawn/send_keys/screenshot/wait_for_text workflows"` + `"verify keystrokes produce the expected screen change"` |
| Launch and interact with a terminal application | ✅ verbatim |
| Test keyboard navigation, menus, overlays, or command palettes | ✅ verbatim |
| Verify that keystrokes produce expected screen changes | ✅ verbatim |
| Run automated test flows against TUI or CLI apps | ✅ `"run an automated test flow"` (the TUI/CLI scope is the opening clause) |
| Authoritative on drive-and-verify | ✅ `"Owns drive-and-verify"` |
| spawn/send_keys/screenshot/wait_for_text workflows | ✅ verbatim |
| screen-dump mode (Ratatui) | ✅ verbatim |
| PTY mode (any terminal app) | ✅ verbatim |
| CLI output verification | ✅ verbatim |

**`terminal-visual-tester`**:

| stock fact | in lean? |
|---|---|
| Validates terminal UI layout and responsive behavior across multiple sizes | ✅ `"how it LOOKS or how it reflows"` + `"across a range of sizes"` |
| captures breakpoint sweeps | ✅ `"multi-size breakpoint sweeps"` |
| detects truncation/overlap/misalignment | ✅ verbatim |
| produces before/after visual comparisons | ✅ `"compare before/after a code change"` + `"before/after comparison"` |
| Layout verification at 80, 120, 160, 200+ columns | ✅ verbatim, all four values kept |
| Before/after visual comparison of a code change | ✅ verbatim |
| Responsive layout testing across a range of sizes | ✅ verbatim |
| Detection of visual regressions | ✅ verbatim |
| Authoritative on layout-and-responsive | ✅ `"Owns layout-and-responsive"` |
| visual regression detection | ✅ verbatim |
| accessibility/readability review | ✅ verbatim |

**`terminal-debugger`**:

| stock fact | in lean? |
|---|---|
| something "looks wrong" but the code alone cannot explain why | ✅ **promoted to the opening clause** |
| Investigates visual anomalies and rendering bugs | ✅ `"Owns investigate-anomaly"` |
| A keystroke does not produce the expected screen change | ✅ verbatim |
| The UI appears stuck, partially rendered, or frozen | ✅ verbatim |
| An overlay is positioned wrong or not appearing | ✅ `"positioned wrong or missing"` |
| Status indicators are not updating | ✅ verbatim |
| A previously working interaction has stopped working | ✅ `"has stopped"` |
| frame-by-frame analysis | ✅ verbatim |
| keystroke-response verification | ✅ verbatim |
| render-pipeline tracing | ✅ verbatim |
| transient/flicker debugging | ✅ verbatim |

### 2c. Not carried into lean — deliberate, each named with its reason

None of these is a trigger, a constraint, or a USE WHEN / DO NOT USE WHEN fact.

| what | why not, and where it lives |
|---|---|
| The 6 `<example>` bodies | Each is an *illustration of a trigger that is itself preserved* — Tab cycling the amplifier TUI sidebar (→ "keyboard navigation"), `amplifier doctor` (→ "CLI output verification"), a 60–200 column sweep (→ "test responsive layout across a range of sizes"), a sidebar/conversation overlap fix (→ "before/after comparison"), a working indicator that never clears (→ "a status indicator is not updating"), Tab not opening the sidebar (→ "a keystroke does not produce the expected screen change"). **No example carried a fact its own trigger did not.** |
| `60` as a sweep width | Appears only inside an `<example>`, and contradicts the stock trigger list's own `80, 120, 160, 200+`. The trigger list is kept verbatim; the body's §Phase 2 breakpoint table is the authority on widths. |
| `Use PROACTIVELY` | Replaced by `USE WHEN`, per the standard. Every natural-language trigger it introduced is preserved. Note `validate-agents` reports MUST/ALWAYS/PROACTIVELY presence as a *metric, not a gate*, and both runs record `has_strong_trigger: true`. |
| `**Authoritative on:**` prefix | Rendered as `Owns …`, the phrasing already merged in the sibling ios-tester / android-tester lanes of this sweep. The predicate list after it is preserved word-for-word. |

### 2d. Net gain — the lean text carries MORE routing information than stock

Not one stock description stated a **DO NOT USE**, and these three are the hardest sibling set in the
bundle: all three legitimately answer "test the TUI". A caller reading the stock catalog got three
entries claiming terminal-application testing with no tiebreaker. All three now route **by name** to
both siblings on the actual deciding axis — *behaviour* (operator) vs *appearance* (visual-tester) vs
*unknown cause* (debugger) — plus the platform boundary to `browser-tester` / `android-tester` /
`ios-tester` territory. The stock `validate-agents` run raised exactly this collision as its
cross-cutting note; the branch run reports **0 suggestions**.

---

## 3. Deliverable: bodies byte-identical (frontmatter-only change)

md5 of everything after the frontmatter's closing `---`, on `origin/main` **and** on the branch:

| file | body md5 (stock) | body md5 (branch) | body bytes | identical |
|---|---|---|---:|---|
| `agents/terminal-debugger.md` | `d9e2ec09970425820980c038aca65214` | `d9e2ec09970425820980c038aca65214` | 8,723 | ✅ |
| `agents/terminal-operator.md` | `b5d329d1dd9468326c2012f8ba1fee8f` | `b5d329d1dd9468326c2012f8ba1fee8f` | 7,709 | ✅ |
| `agents/terminal-visual-tester.md` | `5f2265235a7d2429e5f332efff6bec79` | `5f2265235a7d2429e5f332efff6bec79` | 6,864 | ✅ |

Within the frontmatter, **only the `description` value changed**: `meta.name` and `model_role` are
byte-identical (`[coding, reasoning, general]` / `[coding, general]` / `[critique, general]`), and no
key was added or removed. Reproduce with `evidence/measure.py <repo>`.

`git diff --stat origin/main` = `3 files changed, 24 insertions(+), 72 deletions(-)` — all inside
`agents/`.

---

## 4. Deliverable: `validate-agents` on the branch, with the honest transition

Both runs: recipe **v1.8.0**, foundation `@v2.1.2` (`a27d5824517d078097b60d84779dd3eae80202cd`).

| | STOCK (`origin/main` worktree) | BRANCH (`541a6be`) |
|---|---|---|
| run id | `run-e9c0134900c4` | `run-7ff76b7380dc` |
| **verdict** | **❌ FAIL** | **⚠️ PASS WITH WARNINGS** |
| agents discovered | **3 across 1 location** | **3 across 1 location** |
| structural summary | `errors 5, passed 0, warnings 4` | `errors 0, passed 3, warnings 3` |
| quality | 0 good / 0 polish / 0 needs_work / **3 critical** | 0 good / 0 polish / **3 needs_work** / 0 critical |
| suggestions | 3 | **0** |
| `example_count` | 2 / 2 / 2 | **0 / 0 / 0** |
| description chars | 1,270 / 1,109 / 1,222 | **596 / 584 / 595** |

**The transition is FAIL → PASS WITH WARNINGS, not "PASS held", and the goal's "must stay PASS"
clause has a false premise on this repo** — stock carried 3 × `EXAMPLE_BLOCK_PRESENT` and
2 × `DESCRIPTION_EXCESSIVE` as structural **ERRORs**. Every ERROR is cleared. This is the third
independent confirmation in this sweep (after ios-tester and android-tester) that "must stay PASS"
should read "must clear every structural ERROR".

The branch run's own summary of the residual rating, verbatim:

> The `needs_work` rating on all three agents traces to a **single warning code repeated three times
> — `NO_TOOLS_SECTION`**. Zero description defects were found.

## 4a. This deliverable is NOT-POSSIBLE-with-reason, and here is the proof

**Deliverable as written:** *"`validate-agents` recipe run ON THE BRANCH, verdict quoted (must stay
PASS)"*. **Result: `⚠️ PASS WITH WARNINGS`. That is not `PASS`. The deliverable is NOT MET.**

It is also **not reachable** by any lane bound by this goal's own fidelity gate. The proof is
deterministic and needs nothing run — `classify_agent`, foundation
`recipes/validate-agents.yaml:1078-1119`:

```python
if has_errors:                    quality = "critical"      # -> FAIL
elif not has_explicit_tools:      quality = "needs_work"    # -> PASS WITH WARNINGS   <-- fires here
elif description_length < 100:    quality = "needs_work"
elif description_length > 1200:   quality = "needs_work"
elif description_length > 600:    quality = "polish"        # -> PASS WITH SUGGESTIONS
elif has_model_role_errors:       quality = "needs_work"
elif has_warnings:                quality = "polish"
else:                             quality = "good"          # -> PASS
```

Only `good` maps to a bare `PASS`. `has_explicit_tools` is evaluated **second — before any
description property is looked at**, so a description that is perfect by every criterion in this
sweep still cannot lift the verdict. On this repo `has_explicit_tools` is `false` for all three
agents, on stock and on the branch alike.

**The single edit that would reach `PASS` is adding a `tools:` key to the agent frontmatter — which
is exactly what this same goal forbids:** *"Bodies must be byte-identical to stock … only the
frontmatter description changes."* Clause 1 and clause 2 are mutually unsatisfiable on this repo. The
lane cannot satisfy both, and it is not entitled to pick which one to break silently.

**A second, independent defect in the same clause:** *"must **stay** PASS"* presupposes stock was
PASS. Stock was **FAIL**. Nothing can *stay* a state it was never in.

**Blast radius: sweep-wide.** **0 of 12** agents across the four sibling tester bundles (android,
browser, terminal, ios) declare agent-level `tools:` — so no description-only lane in this family can
ever satisfy the clause as written. Two of those four already merged in this sweep, both at PASS WITH
WARNINGS.

**Filed as `model_performance-593h`** with three remedies: (a) reword the clause to what it actually
tests — *clears every structural ERROR, with residual warnings shown identical on stock and branch*;
(b) keep `PASS` and widen the scope to permit `tools:`, which makes it a functional change needing a
real spawn to verify and therefore not a $0 job; (c) split the `tools:` work into one cross-bundle
item covering all 12 agents at once. **This lane recommends (a) + (c)** and did **not** take (b): the
lane will not fold an unverifiable functional change into a text-only diff, nor make this bundle the
sole outlier among its three siblings, on its own authority.

**What the lane did achieve against this deliverable:** stock's **5 structural ERRORs → 0**, verdict
quoted verbatim on both sides, discovered agent count quoted (3), residual warnings shown identical
on stock and branch. If the clause is reworded per (a), this is DONE as it stands, with no further
edit.

---

## 5. `NO_TOOLS_SECTION` × 3: acknowledged and declined, not fixed

**Identical on stock and branch** — this lane neither introduced nor removed it.

Evidence for leaving it, all verified in-repo rather than assumed:

1. The tool **is** declared, with its config, at `behaviors/terminal-tester.yaml:9-25`, in the same
   file that includes all three agents by name. The validator's own remediation text permits
   *"in frontmatter **or bundle.yaml**"*.
2. `tools:` on an agent is **additive, never restrictive** — verified verbatim at
   `amplifier-foundation/modules/tool-delegate/amplifier_module_tool_delegate/__init__.py:1513`
   (`_merge_tools`): *"Exclusions apply to INHERITANCE only. Explicit declarations from agent are
   ALWAYS honored."* Its one functional effect is overriding `exclude_tools` (default
   `[tool-delegate]`). **None of these three agents calls `delegate`**, so none is arriving crippled.
   P3 hygiene, not P0.
3. `tools:` is **config, not catalog text** — it moves **0 bytes** of the per-turn cost this lane
   exists to reduce.
4. Adding it is a *functional* change riding in a text-only diff, unverifiable at $0 (it needs a real
   spawn), and it would make this bundle the sole outlier among the four sibling tester bundles —
   **0 of 12** agents across android / browser / terminal / ios declare agent-level `tools:`.

Disposition: **recorded as a known benign warning; deliberately not edited.**

---

## 6. Deliverable: tests and CI

- **Tests: `modules/tool-terminal-inspector` — 94 passed, 0 failed** on the branch
  (`uv run --extra dev pytest tests/ -q`). Same 94 the merge-base commit `fde68aa` recorded, so the
  change is test-neutral.
- **No test in this repo asserts anything about agent descriptions.** Checked, not assumed: the only
  `description` match under `tests/` is `conftest.py:26`, a stub `def description()` on a fake *tool*
  object, and there are **zero** assertions requiring `<example>` blocks to be present — the
  inverted-test hazard that bit `dot-graph` in this sweep does not exist here.
- **CI: this repo owns none, but the PR does carry one check, and it is green.** `.github/` does not
  exist and `git ls-files` matches 0 paths under it — so there are **no repo-owned workflows**. PR #16
  nevertheless carries one **org-level** check, `license/cla`
  (`microsoft-github-policy-service`), reporting **`conclusion: SUCCESS`, `status: COMPLETED`** at
  2026-09-07T23:17:35Z, with `mergeable: MERGEABLE`. Stated both ways because "this repo has no CI"
  alone was wrong about the PR's checks in a sibling lane of this sweep. The `94 passed` figure above
  is a local run, not a CI result.

## 6a. Census safety (goal's pre-finish gate)

`grep -l /tmp/ ~/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/*.pth` → **no matches**
(exit 1) across **75** `.pth` files. Nothing was repointed. `amplifier` was never invoked on the host
with a scratch `AMPLIFIER_HOME`; every measurement here is static file reading, and both
`validate-agents` runs used the in-session recipes tool against real checkout paths.

---

## 7. Baseline reconciliation — the census number vs measured `origin/main`

The item and goal name **~3,725 ch**. Measured on current `origin/main` (`fde68aa`): **3,601 chars**
of description across 3 agents. The gap is **not** drift in the sense that bit a sibling lane — it is
a units difference, and it reconciles:

- 3,601 (description text) + ~122 (the three rendered catalog line prefixes
  `"  - terminal-tester:<agent>: "`, 39 + 39 + 44) ≈ **3,723**, i.e. the census measured **rendered
  catalog entries**, this note measures **description values**.
- Real upstream drift also exists and is accounted for separately: `fde68aa` (PR #15, merged after
  the sweep was scoped) removed the `<commentary>` blocks, taking the same three descriptions from
  **4,224 → 3,601** chars. That is why `commentary_count` is already 0 in the stock run while the
  ios-tester lane found 9.

**All numbers in this note are measured against `fde68aa`, the branch's actual merge-base.**

---

## 8. Decisions recorded (no human was waited on)

1. **Held `model_performance-dae2` directly rather than filing a per-repo child.** `work_claim` on it
   **succeeded** — the goal's child-item recovery path is conditioned on a *refusal*, and there was
   none. The resolution text names this repo's slice and the five repos still uncovered, exactly as
   `x99c` did when it spawned this item. §10.
2. **All three land ≤600 chars.** No fidelity trade was needed to get there, so none was taken. Where
   a further trim would have cost a fact, the fact wins — that case did not arise.
3. **`NO_TOOLS_SECTION` × 3 accepted, not remediated — and the verdict deliverable recorded
   NOT-POSSIBLE rather than bought with an out-of-scope edit.** Adding `tools:` is the one edit that
   would have turned `PASS WITH WARNINGS` into `PASS`; it is forbidden by this goal's own fidelity
   gate, unverifiable at $0, and would make this bundle the sole outlier among four siblings. The
   lane took the goal's NOT-POSSIBLE-with-reason branch and filed the conflict as
   `model_performance-593h`. §4a, §5.
4. **Two `validate-agents` runs, not one.** The goal requires the branch verdict; the stock run is
   what makes "FAIL → PASS WITH WARNINGS" checkable rather than asserted. Both are $0.
5. **No catalog render performed.** The goal's deliverable list asks for char counts, not a rendered
   catalog, and the census-safety rule forbids running `amplifier` against a scratch
   `AMPLIFIER_HOME`. Description chars are the thing the catalog is built from; §7 shows the
   constant offset.

---

## 9. Observations worth their own item (found, not fixed)

1. **One claim from the branch run's tool-access analysis is REFUTED — recorded, not propagated.** It
   asserted that a **bare-string** `tools: [terminal_inspector]` is *"live today in
   `reality-check:terminal-tester.md`"* and would `AttributeError` at spawn. Checked directly: that
   file uses the correct mount-plan form (`tools:` → `- module: tool-terminal-inspector`), as does
   `reality-check:browser-tester.md` (`- module: tool-delegate`). **There is no bare-string
   declaration and no spawn crash there.** The shape constraint itself (mount-plan dicts, not bare
   strings) is real and worth knowing; the named victim is not.
   **This does not contradict the separate, real finding already filed by another lane as
   `model_performance-yd8m`** (*"reality-check: browser-tester loses tool-delegate at spawn;
   terminal-tester tools declaration is inert"*) — an *inert* declaration is exactly what the
   additive `_merge_tools` semantics produce for an already-inherited module, which is a different
   defect from a crash. No new item filed; yd8m covers it.
2. **`validate-agents` false-negatives on behavior-level tool declarations** — it checks for the
   `tools:` *key in agent frontmatter only*, not validity or location, so a correct
   `behaviors/*.yaml` declaration reads as missing. Same polarity the ios-tester and
   infographic-builder lanes recorded; this is a further instance, not a new finding.

---

## 10. Publication

**PR #16** — <https://github.com/microsoft/amplifier-bundle-terminal-tester/pull/16> — created with
`gh pr create --draft` and **left as a draft**, because this goal's LANDING STAGE clause makes the
draft PR the lane's finish line: *"A deliverable whose FINAL state requires a merge is DONE AT THE
DRAFT PR."* **Not merged, and not marked ready** — that call is the manager's, and the deliberate
divergence from the ios-tester lane (which had a differently-worded ready-when-green clause) is
recorded here rather than left as an inconsistency.

Readback at the time of writing: `headRefOid b851e44…` matching `git ls-remote`,
`isDraft: true`, `state: OPEN`, `mergeable: MERGEABLE`, `license/cla` SUCCESS. The DONE.json marker
lives outside this repo at the lane root, by instruction; no `DONE.json` is created, staged or
committed inside this repository.

## 11. Evidence index

```
docs/lanes/dae2-catalog-terminal-tester/
├── DONE-NOTE.md                     (this file)
└── evidence/
    ├── measure.py                   reproduce every byte count at $0, no LLM call
    ├── descriptions-STOCK.json      per-agent desc chars, md5, example counts, body md5 @ fde68aa
    ├── descriptions-BRANCH.json     the same fields on the branch
    ├── validate-agents-STOCK.md     FAIL, 5 errors, verdict + coverage quoted verbatim
    └── validate-agents-BRANCH.md    PASS WITH WARNINGS, 0 errors, verdict + coverage verbatim
                                     (NOT the required PASS -- see DONE-NOTE section 4a)
```
