"""Which variant a given person sees, and why.

The whole rollout mechanism reduces to `resolve_variants`. It runs on the
profile endpoint, which is fetched on every page load, so it has two hard
constraints: it must never write, and it must never raise.

The rule, in order:

  1. A disabled experiment answers with its default — for everyone,
     including the accounts an admin pinned. That is what makes "off" a
     real kill switch rather than a pause: flip it and the withdrawn look
     is gone from every account on its next page load, with the
     assignments still on disk for when it comes back on.
  2. Otherwise an explicit assignment wins. An admin put them there, or
     they chose it themselves in Settings, and it holds until somebody
     changes it — a percentage moving underneath them must never take
     someone off the thing they are giving feedback about.
  3. Everyone else is bucketed from a hash of (user id, experiment key).

Point 3 is the one worth explaining. The obvious implementation of "roll out
to 25%" is to draw a random number per user and store it. That needs a write
on the hot path, and a write means the first request of every new user's
session either blocks on the database or races another tab. Hashing the user
id instead gives the same distribution with no storage at all: the same
person always lands in the same bucket, so the assignment is stable across
devices, sessions and server restarts, and raising 25% to 50% keeps everyone
who was already in — nobody gets yanked back out of the experiment they've
been giving feedback about.

Salting the hash with the experiment key matters too: without it, the same
users would be in the first bucket of every experiment forever, and the
same unlucky cohort would receive every single change the app ever tries.
"""
from __future__ import annotations

import hashlib
import logging

from backend.repositories.experiments import get_assignments, list_experiments

logger = logging.getLogger(__name__)

BUCKETS = 100


def bucket_of(user_id: str, key: str) -> int:
    """A stable 0–99 for this (user, experiment). Pure function: same inputs,
    same answer, on any machine and any deploy."""
    digest = hashlib.sha256(f"{key}:{user_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % BUCKETS


def variant_for_bucket(experiment: dict, bucket: int) -> str:
    """Walk the rollout percentages in the variants' declared order.

    Order is taken from `variants`, not from the rollout dict, so the
    boundaries never move because a JSON object came back with its keys in a
    different order — which would silently reshuffle every bucketed user.
    """
    edge = 0
    rollout = experiment.get("rollout") or {}
    for variant in experiment.get("variants") or []:
        key = variant.get("key") if isinstance(variant, dict) else variant
        try:
            share = int(rollout.get(key, 0) or 0)
        except (TypeError, ValueError):
            share = 0
        if share <= 0:
            continue
        edge += share
        if bucket < edge:
            return key
    return experiment["default_variant"]


def resolve(experiment: dict, user_id: str, assignment: dict | None) -> str:
    """One experiment, one user. See the rule at the top of the module.

    Order matters and is not the obvious one: OFF is checked before the
    assignment. An admin who withdraws a look expects it gone from every
    account on their next page load — including the accounts that were
    deliberately pinned to it, who are exactly the people still looking at
    it. A pin that outlived the kill switch would leave the handful of
    testers as the only people in the world seeing a withdrawn design.
    The assignments stay on disk and take effect again when it comes back.
    """
    if not experiment.get("enabled"):
        return experiment["default_variant"]
    if assignment and assignment.get("variant"):
        pinned = assignment["variant"]
        # A variant that has since been renamed or removed must not strand
        # someone on a look that no longer exists.
        known = {
            (v.get("key") if isinstance(v, dict) else v)
            for v in (experiment.get("variants") or [])
        }
        if pinned in known:
            return pinned
    return variant_for_bucket(experiment, bucket_of(user_id, experiment["key"]))


async def resolve_variants(conn, user_id: str) -> dict[str, str]:
    """{experiment_key: variant} for this user — the profile's payload.

    Swallows everything. This is called from the endpoint the whole app
    depends on to render at all; an experiment mechanism that can take the
    app down is worse than no experiment mechanism.
    """
    try:
        experiments = await list_experiments(conn)
        if not experiments:
            return {}
        assignments = await get_assignments(conn, user_id)
    except Exception:  # noqa: BLE001 — never break the page load
        logger.warning("Experiment resolution failed; serving no variants",
                       exc_info=True)
        return {}
    resolved: dict[str, str] = {}
    for experiment in experiments:
        try:
            resolved[experiment["key"]] = resolve(
                experiment, user_id, assignments.get(experiment["key"])
            )
        except Exception:  # noqa: BLE001 — one bad row is not all of them
            logger.warning("Could not resolve experiment %s",
                           experiment.get("key"), exc_info=True)
    return resolved
