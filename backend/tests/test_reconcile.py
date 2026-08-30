

def test_the_apply_summary_names_every_counter_it_keeps():
    """Whatever `apply` counts, the summary line must report.

    s-layer was computed, applied and rolled back but printed nowhere — not
    in the report column, not in the summary. The 30 Aug production run said
    "532 glosses corrected, 0 translations inserted, 3409 parts of speech
    corrected" while quietly filling 5,541 interlinear glosses and
    transliterations, the one thing a re-seed can never write. An operator
    reading that line would not know the layer work had landed at all.
    """
    import inspect

    from backend.services.seeder import reconcile

    src = inspect.getsource(reconcile.main)
    summary = src[src.index('print(f"applied'):]
    summary = summary[:summary.index(")\n")]
    for key in ("gloss", "pos", "added_translation", "sentence_layers"):
        assert key in summary, (
            f"apply() counts {key!r} but the summary line never prints it")
