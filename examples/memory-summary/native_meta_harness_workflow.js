// Native Meta-Harness — the whole outer loop as one Workflow script.
// This is the entire "outer loop" the Stanford harness needs ~1,260 lines of Python for. The
// only thing it reuses is the $0 Python scorer (inner_loop.py + corpus.py). Run via the
// Workflow tool, passing the ABSOLUTE path to this example dir as args.dir:
//   Workflow({ scriptPath: "<abs path>/examples/memory-summary/native_meta_harness_workflow.js",
//              args: { dir: "<abs path>/examples/memory-summary", rounds: 2, k: 3 } })
// Cost: proposer + scorer agents run on your session model; the scorer itself
// is $0 Python. No claude_wrapper, no metered solver API.

export const meta = {
  name: 'memory-summary-search',
  description: 'Evolve memory-summary compressors: parallel propose -> $0 score -> Pareto frontier, looped',
  phases: [{ title: 'Propose' }, { title: 'Score' }, { title: 'Frontier' }],
}

// Absolute path to this example directory (Workflow scripts need absolute paths). Pass via args.dir.
const DIR = (args && args.dir) || '/PATH/TO/examples/memory-summary'
const ROUNDS = (args && args.rounds) || 2
const K = (args && args.k) || 3
const FLOOR = 0.70

const CAND = {
  type: 'object', additionalProperties: false,
  properties: { name: { type: 'string' }, hypothesis: { type: 'string' } },
  required: ['name', 'hypothesis'],
}
const SCORE = {
  type: 'object', additionalProperties: false,
  properties: {
    agent: { type: 'string' }, mean_fidelity: { type: 'number' },
    mean_chars: { type: 'number' }, min_fidelity: { type: 'number' },
  },
  required: ['agent', 'mean_fidelity', 'mean_chars', 'min_fidelity'],
}

// Seed the frontier with the incumbent — the bar every candidate must beat.
let frontier = [{ agent: 'baseline_incumbent', mean_fidelity: 1.0, mean_chars: 269.2, min_fidelity: 1.0 }]

for (let r = 1; r <= ROUNDS; r++) {
  // ── Propose: K proposers in parallel, each writes ONE candidate file ──
  phase('Propose')
  const proposed = await parallel(Array.from({ length: K }, (_, i) => () =>
    agent(
      `Round ${r}, proposer ${i + 1} of a proteus memory-summary search. cd ${DIR}.\n` +
      `Read corpus.py (records + the fidelity rubric you're graded on), ` +
      `agents/baseline_incumbent.py (the 269-char system to beat), and logs/frontier.json if present.\n` +
      `Write ONE new SummaryCompressor to agents/cand_r${r}_${i + 1}.py: preserve fidelity ` +
      `(>= ${FLOOR} worst-record) in FEWER chars than the incumbent, via a genuinely NEW mechanism ` +
      `(not a tweaked constant; never hardcode a record value). Subclass SummaryCompressor from ` +
      `candidate_base, implement summarize(self, record)->str, pure & deterministic.\n` +
      `Validate: python -c "import agents.cand_r${r}_${i + 1}; print('OK')".\n` +
      `Return {name:"cand_r${r}_${i + 1}", hypothesis:"<falsifiable claim>"}.`,
      { label: `propose:r${r}c${i + 1}`, phase: 'Propose', schema: CAND, agentType: 'general-purpose' }
    )
  ))
  const cands = proposed.filter(Boolean)

  // ── Score: each candidate through the $0 Python inner loop ──
  phase('Score')
  const scores = await parallel(cands.map(c => () =>
    agent(
      `cd ${DIR} && run: python inner_loop.py --agent ${c.name}\n` +
      `Read the printed "<agent> fidelity=<f> chars=<c> min_fid=<m>" line ` +
      `(or logs/${c.name}.json) and return {agent, mean_fidelity, mean_chars, min_fidelity}. ` +
      `Modify no files.`,
      { label: `score:${c.name}`, phase: 'Score', schema: SCORE, agentType: 'general-purpose' }
    )
  ))

  // ── Frontier: floor-respecting 2D Pareto, pure JS, carried across rounds ──
  phase('Frontier')
  const pool = [...frontier, ...scores.filter(Boolean).filter(s => s.min_fidelity >= FLOOR)]
  pool.sort((a, b) => b.mean_fidelity - a.mean_fidelity || a.mean_chars - b.mean_chars)
  frontier = []
  let best = Infinity
  for (const p of pool) { if (p.mean_chars <= best) { frontier.push(p); best = p.mean_chars } }
  log(`round ${r}: frontier = ${frontier.map(p => `${p.agent}@${p.mean_chars}c/${p.mean_fidelity}f`).join(', ')}`)
}

return { frontier }
