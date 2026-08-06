---
name: explain-decisions
description: Explain a technical choice in this project so the owner actually understands it and can defend it in an interview — the symptom, the real cause, the alternatives that lost, the cost, and the industry name for the pattern. Use when asked "why did you do it that way", "explain this", "what is X", or after any change that involved a real design decision. Also writes the decision to docs/decisions/ as a durable record.
---

# Explain decisions

The owner of this project is learning as it is built, and intends to use this
work when applying for engineering roles. That has two consequences for how
work gets explained here:

1. **A change is not finished when it works. It is finished when the owner
   could explain it to someone else.** An explanation nobody can repeat back
   is a code comment with extra steps.
2. **The vocabulary matters as much as the reasoning.** Knowing that a change
   avoided re-fetching the same data is useful. Knowing it is called
   *memoisation*, or *cache invalidation*, or *N+1* is what makes it findable
   later and sayable in an interview.

## When to run this

- The owner asks *why*, *what is*, *how does this work*, *explain* — anything
  where the question is about understanding rather than about shipping.
- A change just landed that involved a genuine choice between two workable
  approaches. Offer the explanation; do not wait to be asked.
- A bug turned out to have a cause that was not the obvious one. Those are
  the highest-value explanations in the whole project, because the gap
  between the symptom and the cause is exactly what experience is.

Do **not** run this for typo fixes, renames, dependency bumps, or anything
where there was no decision to make. Explaining a non-decision teaches that
explanations are noise.

## The shape of an explanation

Six parts, in this order, short. The whole thing should be readable in two
minutes.

**1. The symptom.** What was actually observed, in the owner's words, not in
system terms. "The bar stopped at 50% and no game started." If this section
needs jargon, the explanation has already gone wrong.

**2. The real cause.** One sentence, at the level of mechanism — what the
machine was actually doing. Then, if the cause is not obvious from the
symptom, one more sentence on why it *looked* like something else. Name the
misleading appearance explicitly; that gap is the lesson.

**3. The choice, and what lost.** What was done, plus the two or three real
alternatives and the specific reason each was rejected. An explanation with
no rejected alternatives is not describing a decision — either find them or
say plainly that there was only one sane option.

**4. The cost.** Every choice buys something with something. Name what this
one costs: latency, memory, a migration the owner has to apply, a case that
is now silently slower, code that is harder to change later. A "free" answer
is an incomplete one.

**5. The name.** What is this pattern called in the industry — backoff,
idempotency, optimistic UI, connection pooling, structural sharing, the
thundering herd, an ADR. One line on where else it shows up. This is the part
that transfers to a job that has nothing to do with language learning.

**6. One question back.** A single concrete question the owner should be able
to answer from the explanation — ideally about a *neighbouring* case, not the
one just explained. "What would happen if two tabs did this at once?" beats
"does that make sense?", which everyone answers yes to.

## Rules

- **Point at real code.** `backend/services/auto_translate.py:412`, not "the
  translation service". The owner should be able to open the thing being
  described. Clickable references are the difference between a lecture and a
  tour.
- **Define jargon on first use, inline, in six words or fewer.** "The pooled
  connection runs one transaction (one all-or-nothing unit of work), so…". If
  a term cannot be defined in six words, it needs its own paragraph or it
  should not be used.
- **Never explain more than the change touched.** The temptation is to teach
  all of Postgres. Teach the one behaviour that made this bug possible.
- **Be honest about the uncertain parts.** "I believe this is why, but the
  matrix tests pass in every locale, so the remaining failure is
  environmental and I have not reproduced it" is a real and useful thing to
  say. Confident wrong explanations are worse than no explanation, because
  they get repeated in interviews.
- **Do not flatter the owner's understanding.** If a question reveals a
  wrong mental model, correct the model first and answer second. The answer
  is worthless on top of a broken model.

## Interview framing

For anything substantial, close with one line the owner could actually say
out loud in an interview. The format that works:

> *"We had X breaking in production. It looked like A, but the real cause was
> B. I fixed it by C rather than D because of E — the trade-off was F."*

Four things make this land: a concrete symptom, a wrong first hypothesis (it
proves you debugged rather than guessed), a rejected alternative, and a named
cost. Notice that admitting the wrong first hypothesis is what makes it
credible — polished stories where the first guess was right sound invented.

## The decision log

Write anything with lasting consequence to `docs/decisions/` using
`templates/decision-note.md` in this skill directory. Number them
sequentially: `0001-single-transaction-probes.md`, `0002-…`.

This is called an **ADR** — Architecture Decision Record. It is a widely used
convention, it is a reasonable thing to point at in an interview, and its
real value is six months from now when the reason for a constraint has been
forgotten and the only surviving artefact is the constraint itself.

Log a decision when it (a) constrains future work, (b) would be surprising to
a newcomer, or (c) was expensive to arrive at. Do not log routine work — a
log where everything is written down is one where nothing is findable.

Keep entries short. A note nobody rereads is a note that was written for the
wrong audience.
