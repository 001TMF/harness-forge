// Meta-Harness — native search loop (the default execution mode).
//
// Replaces claude_wrapper.py + meta_harness.py. The only domain code it calls is your $0 scorer.
// Invoke via the Workflow tool:
//   Workflow({ scriptPath: "<this file>", args: { rounds: 2, k: 3 } })
//
// HOW TO ADAPT (search for ADAPT):
//   - DIR        : the working directory holding your scaffold (scorer + candidate interface + agents/)
//   - SCORE_CMD  : the shell command that runs your $0 scorer for a candidate
//   - the proposer prompt: point it at your corpus/rubric/baseline + proposer prior
//   - QUALITY/COST field names + the floor
//
// Workflow JS is sandboxed: NO filesystem, NO Date.now()/Math.random(), NO Node APIs.
// All file writes + scorer execution happen INSIDE agent() subagents via Bash. The JS only does
// control flow + the Pareto math.

export const meta = {
  name: 'meta-harness-search',
  description: 'Evolve harness candidates: parallel propose -> $0 score -> floor-respecting Pareto frontier, looped',
  phases: [{ title: 'Propose' }, { title: 'Score' }, { title: 'Frontier' }],
}

// ADAPT ----------------------------------------------------------------------
const DIR = (args && args.dir) || '/PATH/TO/your-scaffold-dir'  // absolute path; pass via args.dir
const ROUNDS = (args && args.rounds) || 2
const K = (args && args.k) || 3
const FLOOR = (args && args.floor) || 0.70
// The scorer command for a candidate named <name>. Must print/return quality+cost+min_quality.
const SCORE_CMD = (name) => `cd ${DIR} && python inner_loop.py --agent ${name}`
// Seed the frontier with the incumbent you must beat (quality 1.0 by definition, known cost):
let frontier = [{ agent: 'baseline_incumbent', quality: 1.0, cost: 269.2, min_quality: 1.0 }]
// ---------------------------------------------------------------------------

const CAND = {
  type: 'object', additionalProperties: false,
  properties: { name: { type: 'string' }, hypothesis: { type: 'string' } },
  required: ['name', 'hypothesis'],
}
const SCORE = {
  type: 'object', additionalProperties: false,
  properties: {
    agent: { type: 'string' }, quality: { type: 'number' },
    cost: { type: 'number' }, min_quality: { type: 'number' },
  },
  required: ['agent', 'quality', 'cost', 'min_quality'],
}

for (let r = 1; r <= ROUNDS; r++) {
  // ── Propose: K proposers in parallel, each writes ONE candidate file ──
  phase('Propose')
  const proposed = await parallel(Array.from({ length: K }, (_, i) => () =>
    agent(
      `Round ${r}, proposer ${i + 1} of a Meta-Harness search. cd ${DIR}.\n` +
      `Read the proposer prior (.claude/skills/*/SKILL.md or proposer-prior file), the corpus + ` +
      `rubric you're graded on, and agents/baseline_incumbent.py (the system to beat). Read the ` +
      `run log + frontier if present.\n` +
      `Write ONE new candidate to agents/cand_r${r}_${i + 1}.py implementing the candidate ` +
      `interface, via a genuinely NEW mechanism (not a tweaked constant; never hardcode an ` +
      `eval-set value). Keep quality >= ${FLOOR} (worst record) while reducing cost.\n` +
      `Validate it imports: cd ${DIR} && python -c "import agents.cand_r${r}_${i + 1}; print('OK')".\n` +
      `Return {name:"cand_r${r}_${i + 1}", hypothesis:"<falsifiable claim about quality/cost>"}.`,
      { label: `propose:r${r}c${i + 1}`, phase: 'Propose', schema: CAND, agentType: 'general-purpose' }
    )
  ))
  const cands = proposed.filter(Boolean)
  if (!cands.length) { log(`round ${r}: no candidates proposed`); continue }

  // ── Score: each candidate through the $0 scorer (Bash inside an agent) ──
  phase('Score')
  const scores = await parallel(cands.map(c => () =>
    agent(
      `Run: ${SCORE_CMD(c.name)}\n` +
      `Read the printed summary (or the result JSON it writes) and return ` +
      `{agent, quality, cost, min_quality}. Modify no files.`,
      { label: `score:${c.name}`, phase: 'Score', schema: SCORE, agentType: 'general-purpose' }
    )
  ))

  // ── Frontier: floor-respecting 2D Pareto, pure JS, carried across rounds ──
  phase('Frontier')
  const pool = [...frontier, ...scores.filter(Boolean).filter(s => s.min_quality >= FLOOR)]
  pool.sort((a, b) => b.quality - a.quality || a.cost - b.cost)
  frontier = []
  let best = Infinity
  for (const p of pool) { if (p.cost <= best) { frontier.push(p); best = p.cost } }
  log(`round ${r}: frontier = ${frontier.map(p => `${p.agent}@${p.cost}/${p.quality}`).join(', ')}`)
}

return { frontier }
