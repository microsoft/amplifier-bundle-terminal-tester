# validate-agents on the BRANCH (`lane/dae2-catalog-terminal-tester`, commit `541a6be`)

- recipe: `foundation:recipes/validate-agents.yaml` **v1.8.0**
- foundation dependency: `git+https://github.com/microsoft/amplifier-foundation@v2.1.2`
  resolved_revision `a27d5824517d078097b60d84779dd3eae80202cd`
- run_id: `run-7ff76b7380dc` - session `b6eccf5a509d4e20-20260907-160855_recipe`
- repo_path: the lane worktree

## VERDICT (verbatim from the report's Executive Summary)

> - **Overall Verdict**: ⚠️ **PASS WITH WARNINGS**
> - **Agents Found**: 3 total across 1 location
> - **Quality Breakdown**: 0 good, 0 polish, 3 needs_work, 0 critical
> - **Issues**: 0 errors, 3 warnings, 0 suggestions
>
> The `needs_work` rating on all three agents traces to a **single warning code
> repeated three times — `NO_TOOLS_SECTION`**. Zero description defects were found.
> Every description is trigger-first, under the 600-char budget, carries explicit
> USE WHEN / DO NOT USE WHEN, and contains zero `<example>`/`<commentary>` blocks.

## Coverage (verbatim)

```
Scanned: ['<repo>/**/agents/*.md', '<repo>/agents/*.md'], excluding ['.git', '.venv', 'docs', 'node_modules', 'test-fixtures', 'tests']
Candidates: 3 files matched the scan
Classified as agents: 3 across 1 locations
Classified as NON-agents: 0 ({})
Classifier: frontmatter declares a top-level `meta:` key (docs/AGENT_AUTHORING.md)
```

| Location | Agents |
|----------|--------|
| agents/  | 3      |

**Discovered agent count for this repo: 3** (`candidates_scanned: 3`,
`total_count: 3`, `non_agent_count: 0`) - the validator's own count, not an
eyeball count.

## structural_results.summary (verbatim JSON)

```json
{"errors": 0, "passed": 3, "total": 3, "warnings": 3}
```

## Per-agent structural findings

| agent | description_length | description_tokens | example_count | errors | warnings |
|---|---:|---:|---:|---|---|
| terminal-debugger | 596 | 149 | 0 | none | `NO_TOOLS_SECTION` |
| terminal-operator | 584 | 146 | 0 | none | `NO_TOOLS_SECTION` |
| terminal-visual-tester | 595 | 148 | 0 | none | `NO_TOOLS_SECTION` |

## Suggestions section (verbatim)

> ### Suggestions (Consider) - LOW Priority
>
> None. The description review found no weak triggers, no missing WHEN deciding
> factor, and no under-length descriptions.
> [...]
> **An edit that exists to produce a diff is worse than no edit.** All three
> descriptions are left unedited, and that is the correct outcome.

## The honest transition

**FAIL → PASS WITH WARNINGS. Not "PASS held".** Stock carried 5 structural ERRORs
(3 × `EXAMPLE_BLOCK_PRESENT`, 2 × `DESCRIPTION_EXCESSIVE`), so a "must stay PASS"
gate has a false premise on this repo - the same finding the ios-tester and
android-tester lanes of this sweep recorded. The branch clears every ERROR.

The 3 residual `NO_TOOLS_SECTION` warnings are **identical on stock and branch**
and were deliberately not touched - see DONE-NOTE §5.

## This is NOT the `PASS` the goal asks for

The goal's deliverable reads *"verdict quoted (must stay PASS)"*. `⚠️ PASS WITH WARNINGS` is a
different verdict. **That deliverable is recorded NOT-POSSIBLE-with-reason**, not DONE — see
DONE-NOTE §4a for the deterministic proof (`classify_agent` pins any agent with
`has_explicit_tools == false` to `needs_work` before it looks at the description at all) and
`model_performance-593h` for the filed goal defect.
