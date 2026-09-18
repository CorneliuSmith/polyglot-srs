"""The nightly judge: the one paid step in the quality loop, behind the
admin's switch and cap (plan §4.3 J1–J2, §8, §9.1).

The owner's two conditions for ever running a paid judge on a schedule were
that coverage is tracked first and that how much it may spend is theirs to
set in the admin panel. Both are here as gates, in this order, and each
fails closed:

1. `quality_settings.judge_enabled` — read through `get_quality_settings`,
   which answers OFF whenever it cannot read the row. Off means nothing
   else is read, not even the spend.
2. Today's spend against `judge_daily_token_cap`. The spend is the sum of
   the `quality_runs` rows this step writes (`kind='judge'`,
   `metric='tokens'`), so the cap holds across restarts and across the
   process's own cycles; it is re-checked before every batch, not once.
3. `language_quality_targets.judge_enabled` per course — a course an admin
   has not switched on is not read.
4. `data/eval/calibrated.json` per (question, course) — plan §7's phase E
   gate. An enabled course whose question has not cleared the three gold
   gates is listed in the stats as `not calibrated` and never sent.

Then `judge_rows_per_cycle` is split evenly across the surviving pairs, and
each pair runs under its own savepoint the way `quality_loop._step` runs a
course: one broken pair costs one pair. Per pair it writes three things,
all through `run_id`: ONE `quality_runs` row `metric='tokens'` (the spend
ledger — value is input+output tokens, population the calls), ONE
`metric='flagged.<question>'` (the panel's rate: findings at confidence
>= 0.7 out of rows judged), and the `content_verdicts` rows themselves.

What it does not do: route a verdict anywhere (owner decision #2), apply a
rewrite, or write to `tutor_usage` — that table's `user_id` is NOT NULL
against `auth.users`, so until decision #2 gives the judge an account its
spend lives in `quality_runs` and shows in the Content health panel's
`spent_today`, not in the AI-costs feature table (DEBT.md).
"""
from __future__ import annotations

import logging

from backend.repositories import quality as quality_repo
from backend.repositories import verdicts as verdicts_repo
from backend.repositories.pool import savepoint
from backend.services.quality import content_judge

logger = logging.getLogger(__name__)

# A finding the panel counts: the question's positive class at the
# confidence every question's rules tell the model means "no reviewer
# needed" (`content_judge.summarise` counts the same thing).
FLAG_CONFIDENCE = 0.7
# Batches in flight per run_items call. The loop is one process sharing
# the API's rate limit with every learner's tutor turn; two is enough to
# hide the round trip and not enough to crowd them.
CONCURRENCY = 2


def new_stats() -> dict:
    return {
        "enabled": False,      # the master switch, as read this cycle
        "courses": 0,          # courses whose target row has judge_enabled
        "judged": 0,           # verdicts returned by a judge that replied
        "flagged": 0,          # of those, findings at FLAG_CONFIDENCE
        "tokens": 0,           # input + output tokens spent this cycle
        "calls": 0,            # model calls this cycle
        "cap_reached": False,  # stopped by judge_daily_token_cap
        "skipped": [],         # "<code>.<question>: <why>"
        "dropped": 0,          # rows a repository could not store (table absent)
        "failures": [],        # "<code>.<question>: <error>" — one broken pair, counted
    }


def _tokens(usage: dict) -> int:
    """What the cap counts: input plus output. Cache reads are billed at a
    fraction and cache writes at a premium; the cap is a ceiling on tokens
    the panel can show as one number, and `tutor_usage` sums the same two."""
    return int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)


def is_flagged(question, verdict: dict) -> bool:
    try:
        confidence = float(verdict.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    return verdict.get("verdict") in question.positive and confidence >= FLAG_CONFIDENCE


async def _codes(conn) -> dict[str, str]:
    rows = await conn.fetch("SELECT id, code FROM languages")
    return {str(r["id"]): r["code"] for r in rows}


async def _pair(conn, stats: dict, code: str, question, fn, *args):
    """One (question, course) under its own savepoint — `quality_loop._step`'s
    shape. A failure rolls the pair's rows back, is counted, never raised.
    Tokens already spent stay counted in `stats["tokens"]` (the cap must see
    them) even though their ledger row rolled back with the pair."""
    try:
        async with savepoint(conn):
            return await fn(conn, stats, *args)
    except Exception as exc:  # noqa: BLE001 — one pair must not stop the step
        logger.warning("judge: %s %s failed: %s", code, question.name, exc)
        stats["failures"].append(f"{code}.{question.name}: {type(exc).__name__}: {exc}")
        return None


async def _judge_pair(conn, stats: dict, sha: str | None, settings: dict, spent: int,
                      question, code: str, lang_id: str, limit: int) -> None:
    items = await verdicts_repo.candidates(conn, question, lang_id, code, limit)
    if not items:
        stats["skipped"].append(f"{code}.{question.name}: no rows to judge")
        return
    model = settings["judge_model"] or None
    # base_url None: the loop's judge is Anthropic on the checker tier —
    # content_judge resolves `sentence_checker` for the course when the
    # admin has set no model. A local endpoint is the local-model plan's
    # seam and arrives through the same call, not through config.py.
    judge = content_judge.judge_for(question, None, model, code)
    name = content_judge.judge_name(None, model, code)
    cap = int(settings["judge_daily_token_cap"] or 0)
    usage = dict.fromkeys(content_judge.USAGE_KEYS, 0)
    results: list[dict] = []
    size = content_judge.BATCH_SIZE
    for start in range(0, len(items), size):
        # Before EVERY batch, against everything spent today plus this
        # cycle: the ledger row is written after the pair, so the running
        # total is the only thing that stops a 1,500-row night on a
        # 1,500,000-token cap at the cap and not at the end.
        if spent + stats["tokens"] >= cap:
            stats["cap_reached"] = True
            break
        batch = items[start:start + size]
        payload = [{k: v for k, v in item.items() if k != verdicts_repo.ENTITY_KEY}
                   for item in batch]
        verdicts, batch_usage = await content_judge.run_items(
            question, payload, judge, batch_size=size, concurrency=CONCURRENCY,
        )
        stats["tokens"] += _tokens(batch_usage)
        stats["calls"] += int(batch_usage.get("calls") or 0)
        content_judge.add_usage(usage, batch_usage)
        if not batch_usage.get("calls"):
            # run_items answers a crashed batch with `unsure` rows so a CLI
            # count cannot read the crash as clean. Here a stored `unsure`
            # would mark the row judged — the coverage numerator, and the
            # back of the queue — on the strength of a crash (quality rule
            # 14, in the ledger). No call means no reply: the rows go back
            # in the queue and the crash is a failure, not a verdict.
            stats["failures"].append(
                f"{code}.{question.name}: a batch of {len(batch)} got no reply")
            continue
        results.extend(verdicts)
    if not usage["calls"]:
        # Nothing ran, so nothing to ledger. The cap refusing the FIRST
        # batch is a skip the stats should name; every batch failing is
        # already named per batch above.
        if stats["cap_reached"]:
            stats["skipped"].append(f"{code}.{question.name}: daily token cap reached")
        return
    judged = len(results)
    flagged = sum(1 for v in results if is_flagged(question, v))
    stats["judged"] += judged
    stats["flagged"] += flagged
    run_id = await quality_repo.record_run(
        conn, kind="judge", language_id=lang_id, metric="tokens",
        value=_tokens(usage), population=int(usage["calls"]), build_sha=sha,
        meta={"question": question.name, "code": code, "model": name, "usage": usage,
              "judged": judged, "flagged": flagged},
    )
    if run_id is None:
        # quality_runs is absent, so content_verdicts (same migration) is
        # too: the tokens row, the flagged row and every verdict are lost.
        stats["dropped"] += 2 + judged
        return
    flag_id = await quality_repo.record_run(
        conn, kind="judge", language_id=lang_id, metric=f"flagged.{question.name}",
        value=flagged, population=judged, build_sha=sha,
        meta={"question": question.name, "code": code, "model": name},
    )
    if flag_id is None:
        stats["dropped"] += 1
    written = await verdicts_repo.record_verdicts(
        conn, run_id, lang_id, question, items, results, name)
    if written is None:
        stats["dropped"] += judged


async def judge_step(conn, sha: str | None) -> dict:
    """The gates in order, then every calibrated (question, course) pair
    within the budget. Returns the stats the heartbeat keeps under
    `stats["judge"]`; never raises for a single pair."""
    stats = new_stats()
    settings = await quality_repo.get_quality_settings(conn)
    if not settings["judge_enabled"]:
        return stats
    stats["enabled"] = True
    cap = int(settings["judge_daily_token_cap"] or 0)
    spent = await quality_repo.judge_tokens_spent_today(conn)
    if spent >= cap:
        stats["cap_reached"] = True
        return stats
    targets = await quality_repo.get_language_targets(conn)
    codes = await _codes(conn)
    enabled = sorted(
        (codes[lang_id], lang_id)
        for lang_id, target in targets.items()
        if target.get("judge_enabled") and lang_id in codes
    )
    stats["courses"] = len(enabled)
    if not enabled:
        return stats
    calibrated = content_judge.calibrated_pairs()
    pairs = []
    for code, lang_id in enabled:
        for question in content_judge.QUESTIONS.values():
            if (question.name, code) in calibrated:
                pairs.append((question, code, lang_id))
            else:
                stats["skipped"].append(f"{code}.{question.name}: not calibrated")
    if not pairs:
        return stats
    rows = int(settings["judge_rows_per_cycle"] or 0)
    limit = rows // len(pairs)
    if limit <= 0:
        for question, code, _ in pairs:
            stats["skipped"].append(
                f"{code}.{question.name}: 0 rows once {rows} is split {len(pairs)} ways")
        return stats
    for question, code, lang_id in pairs:
        if stats["cap_reached"]:
            stats["skipped"].append(f"{code}.{question.name}: daily token cap reached")
            continue
        await _pair(conn, stats, code, question, _judge_pair,
                    sha, settings, spent, question, code, lang_id, limit)
    return stats
