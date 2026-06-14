# Proposer prior (template)

This is the mini-skill each proposer agent reads before writing candidates. It is the single
biggest lever on search *quality* — a weak prior produces parameter-tweaks that tie or regress; a
strong one produces real mechanism changes. ADAPT the bracketed parts to your domain.

---

You are proposing candidate implementations of the [CANDIDATE INTERFACE] for a Meta-Harness
search. Do all the work yourself in one session — don't delegate. You do **not** run the scorer;
the outer loop does that separately.

## Produce exactly [K] candidates this round

Mix exploitation (refine what's near the frontier) and exploration (try something structurally
new). Do not abort early or declare the frontier optimal.

## Change a MECHANISM, not a constant

The most common failure is a candidate that is the baseline with a number changed — these almost
always tie or regress, because the search space of constants is shallow and already well-explored
by the frontier. A good candidate changes *how* the work is done:

- [a new algorithm — e.g. a different ranking/selection/compression strategy]
- [a new representation — e.g. a key:value micro-syntax vs prose; symbol encoding of fixed vocab]
- [a new structure — e.g. hierarchical vs flat; fast/slow pools; ordered-by-value-so-truncation-is-safe]
- [combining two prior ideas — take the retrieval from A and the encoding from B]

Self-test before committing: *"If I diff my candidate against the baseline, is the difference a
new mechanism, or just different numbers?"* If it's just numbers, rewrite.

## Anti-leakage (load-bearing)

Never hardcode a value, id, name, or fact from the eval corpus into a candidate. The candidate
must generalize to unseen items. A candidate that memorizes the corpus is worthless and invalid.

## Prototype + self-critique (mandatory)

Before writing the final candidate, run your core idea on 1-2 corpus items in a throwaway script
and check the quality rubric by eye. Candidates that skip this tend to have bugs or no
improvement. Then re-read your file with fresh eyes against the two rules above.

## Output

Write [K] files into `agents/<snake_name>.py`, each subclassing the candidate interface and
implementing the method(s) — pure, deterministic, no I/O, no LLM. Validate each imports. Then
return the structured result the loop asked for (a `{name, hypothesis}` per candidate), where the
hypothesis is a falsifiable claim about its quality/cost relative to the incumbent.
