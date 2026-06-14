# Native execution — running the loop without the Python harness

The Stanford repo drives the loop with `claude_wrapper.py` (a headless `claude -p` driver) +
`meta_harness.py` (the outer loop). In this environment, both are redundant — you have the
runtime as first-class tools. This file maps every Meta-Harness piece to its native equivalent
and details the three execution modes.

## The mapping

| Meta-Harness piece | What it does | Native equivalent |
|---|---|---|
| `claude_wrapper.run()` | spawn a headless Claude to write candidates | `Agent` / `agent()` inside a `Workflow` |
| `meta_harness.py` outer loop | propose → validate → score → frontier → repeat | a `Workflow` script (`parallel`/`pipeline`/`while`) |
| `pending_eval.json` handshake | pass proposer output back to the loop | a `schema` on `agent()` — typed return, no file handshake |
| `evolution_summary.jsonl` / `frontier.json` | persistent search memory | workflow JS variables + a results JSONL on disk |
| `validate_candidates` (import check) | reject broken candidates | a Bash line inside the scoring agent, or a validate stage |
| `SKILL.md` proposer prior | steer the proposer | a skill / a prior file the proposer agent is told to read |
| "run N iterations" | repetition | the workflow `for`-loop, or `/loop`, or `CronCreate` for unattended runs |
| 3 candidates / iteration | mutation breadth | `parallel()` — and these run *concurrently* (the Python loop is serial) |
| inner loop (`inner_loop.py`) | the cheap scorer | **stays a script** — real domain logic, invoked via Bash inside an `agent()` |
| `cost_usd` / token logging | accounting | the `budget` object + task-completion notifications |

**The irreducible remainder:** the cheap scorer + rubric + candidate interface. Everything
orchestration-shaped is native.

## Mode B — Workflow (default, the 1:1 match)

This is the recommended way to run an actual search. `assets/workflow-template.js` is a ready
template; copy it, set the working dir / candidate count `k` / rounds / floor, and run it via the
`Workflow` tool.

Shape of the script:

```
for each round:
  PROPOSE  parallel([...k proposer agents...])   // each writes ONE candidate file, returns {name, hypothesis} via schema
  SCORE    parallel([...one scorer agent per candidate...])  // each runs the $0 scorer via Bash, returns {quality, cost} via schema
  FRONTIER pure-JS Pareto merge, floor-respecting, carried in a JS variable across rounds
return { frontier }
```

Key facts that make this work:

- **The workflow JS is sandboxed** — no filesystem, no `Date.now()`/`Math.random()`, no Node
  APIs. So *all* file I/O and Python execution happens **inside `agent()` subagents via Bash**.
  The proposer agent writes candidate files; the scorer agent runs `python scorer.py` and returns
  the parsed numbers. The JS only does control flow + the Pareto math.
- **Typed returns replace the file handshake.** Give `agent()` a `schema` and it returns a
  validated object — `{name, hypothesis}` from proposers, `{agent, quality, cost, min_quality}`
  from scorers. No `pending_eval.json` round-trip.
- **Parallel proposers.** `parallel(Array.from({length:k}, ...))` fans out k proposers at once
  (the Python harness proposes serially). Give each candidate a distinct filename
  (`cand_r<round>_<i>.py`) so concurrent writes don't collide. Use `isolation:'worktree'` only if
  candidates would otherwise clobber shared files.
- **`agentType:'general-purpose'`** for proposer/scorer agents — they need Write/Edit/Bash. (The
  default read-only types like `Explore` cannot write.)
- **State across rounds** lives in the JS `frontier` variable (within one run) and/or a results
  JSONL on disk (across runs / for resume). For long searches use `budget.remaining()` to loop
  until a token target, and re-invoke with `resumeFromRunId` to continue after a pause —
  unchanged `agent()` calls return cached.
- **The proposer prior** is passed by telling each proposer agent to read
  `assets/proposer-prior-template.md` (or your domain copy), or by registering it as a skill the
  agent loads. It enforces mechanism-level changes + anti-leakage.

Cost: the $0 scorer is free; the proposer/scorer agents run on the session model. No
`claude_wrapper`, no metered solver API.

## Mode A — skill + `/loop` (you are the proposer)

The leanest mode: no Workflow, no second process. A small skill body encodes **one iteration**
("read the frontier and run log; write 3 candidate files via a mechanism-level change; run the
$0 scorer on each; Pareto-merge into the frontier; append to the run log"), and `/loop` re-invokes
it — `/loop` with an interval, or no interval to self-pace.

Use when: you want minimal machinery, a small search, and you're fine acting as the proposer
yourself (serial, in-session). Trade-off vs. Workflow: no parallel proposers, occupies the
interactive session, less isolation. Good for a first exploratory pass; graduate to Workflow for
a real search.

`scripts/pareto.py` does the frontier computation so the loop doesn't reinvent it each time.

## Mode C — Team (rarely)

`TeamCreate` + a shared task board + `SendMessage` can model durable proposer / scorer / curator
roles that persist and message each other. This is heavier than the loop needs — reach for it
only if the search is long-lived and the roles genuinely need to be standing agents (e.g. a
continuous background optimizer with a human in the loop). For a normal propose→score→frontier
search, Workflow is simpler and sufficient.

## Unattended / scheduled runs

To run searches without you present:

- `CronCreate` — a scheduled cloud agent that fires the search on a cron schedule (e.g. a nightly
  round that proposes + scores + updates the frontier).
- `/loop <interval>` — keeps re-running in the current session at a fixed cadence.
- `ScheduleWakeup` — for self-paced `/loop` continuation between rounds.

This is the one area where the standalone Python harness still has an edge: a plain
`python meta_harness.py` on a server needs no Claude Code session at all. If portability to a
bare server / CI matters, keep the Python driver; if you're working inside this environment,
native is leaner.
