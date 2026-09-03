"""The daily prune of the append-only AI tables (brief item 6, step 4)."""
from __future__ import annotations

from unittest.mock import AsyncMock

from backend.services import retention


class TestSweep:
    async def test_prunes_both_tables_by_their_own_window(self):
        conn = AsyncMock()
        conn.fetchval.return_value = "tutor_sessions"  # both present
        conn.execute.side_effect = ["DELETE 12", "DELETE 3"]
        counts = await retention.sweep_retention(conn)
        assert counts == {"tutor_sessions": 12, "tutor_usage": 3}
        sqls = [c.args[0] for c in conn.execute.await_args_list]
        assert sqls[0].startswith("DELETE FROM tutor_sessions WHERE")
        assert "interval '180 days'" in sqls[0]
        assert sqls[1].startswith("DELETE FROM tutor_usage WHERE")
        assert "interval '13 months'" in sqls[1]

    async def test_a_missing_table_is_skipped_not_hit(self):
        # A probe, not a catch: a DELETE against a missing table inside the
        # privileged transaction would poison every statement after it.
        conn = AsyncMock()
        conn.fetchval.side_effect = [None, "tutor_usage"]
        conn.execute.return_value = "DELETE 0"
        counts = await retention.sweep_retention(conn)
        assert counts == {"tutor_sessions": 0, "tutor_usage": 0}
        conn.execute.assert_awaited_once()
        assert "tutor_usage" in conn.execute.await_args.args[0]

    def test_the_windows_sit_above_every_reader(self):
        # The allowance reads the current month; the admin cost views clamp
        # their `days` at 365. Shrinking either window below that would
        # make a report lie about a period it can no longer see.
        assert retention.TUTOR_USAGE_MONTHS >= 13
        assert retention.TUTOR_SESSIONS_DAYS >= 90

    def test_status_tag_parsing_tolerates_junk(self):
        assert retention._deleted("DELETE 7") == 7
        assert retention._deleted("") == 0
        assert retention._deleted(None) == 0
