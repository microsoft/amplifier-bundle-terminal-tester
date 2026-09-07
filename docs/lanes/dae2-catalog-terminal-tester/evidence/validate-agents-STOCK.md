# validate-agents on STOCK (origin/main `fde68aa`)

- recipe: `foundation:recipes/validate-agents.yaml` **v1.8.0**
- foundation dependency: `git+https://github.com/microsoft/amplifier-foundation@v2.1.2`
  resolved_revision `a27d5824517d078097b60d84779dd3eae80202cd`
- run_id: `run-e9c0134900c4` - session `fa7484d1e96e40c5-20260907-160501_recipe`
- repo_path: `/tmp/dae2/stock-wt` (detached worktree at `origin/main`)

## VERDICT (verbatim from the report's Executive Summary)

> - **Overall Verdict**: ❌ **FAIL** — critical structural errors in all 3 agents
> - **Agents Found**: 3 total across 1 location
> - **Quality Breakdown**: 0 good, 0 polish, 0 needs_work, **3 critical**
> - **Issues**: **5 errors**, 4 warnings, 3 suggestions

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

## structural_results.summary (verbatim JSON)

```json
{"errors": 5, "passed": 0, "total": 3, "warnings": 4}
```

## Per-agent structural findings (verbatim codes)

| agent | description_length | example_count | errors | warnings |
|---|---:|---:|---|---|
| terminal-debugger | 1270 | 2 | `DESCRIPTION_EXCESSIVE` (>1200), `EXAMPLE_BLOCK_PRESENT` | `NO_TOOLS_SECTION` |
| terminal-operator | 1109 | 2 | `EXAMPLE_BLOCK_PRESENT` | `NO_TOOLS_SECTION`, `DESCRIPTION_HIGH` (>600) |
| terminal-visual-tester | 1222 | 2 | `DESCRIPTION_EXCESSIVE` (>1200), `EXAMPLE_BLOCK_PRESENT` | `NO_TOOLS_SECTION` |

`commentary_count` is 0 on all three - the `<commentary>` blocks were already
removed upstream by `fde68aa` (PR #15).

## The report's own cross-cutting note (verbatim)

> **Cross-cutting note:** these three are siblings over the same `terminal_inspector`
> surface, and **not one stock description states a DO NOT USE WHEN**. A router sees
> three agents each claiming "terminal application testing" with no tiebreaker.
