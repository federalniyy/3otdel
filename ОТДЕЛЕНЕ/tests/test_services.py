from __future__ import annotations

import unittest
from datetime import date

from bot.services import MorningService, WeeklyService
from bot.storage import JsonStore


class ServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = JsonStore(":memory:")
        self.store.data["weekly_assignments"] = []
        self.weekly = WeeklyService(self.store)
        self.morning = MorningService(self.store)

    def tearDown(self) -> None:
        pass

    def test_dorm_weekly_runs_every_saturday(self) -> None:
        self.weekly.set_anchor("dorm_weekly", date(2026, 6, 13))

        self.assertTrue(self.weekly.is_cleaning_saturday("dorm_weekly", date(2026, 6, 13)))
        self.assertTrue(self.weekly.is_cleaning_saturday("dorm_weekly", date(2026, 6, 20)))
        self.assertTrue(self.weekly.is_cleaning_saturday("dorm_weekly", date(2026, 6, 27)))
        self.assertTrue(self.weekly.is_cleaning_saturday("dorm_weekly", date(2026, 7, 4)))
        self.assertFalse(self.weekly.is_cleaning_saturday("dorm_weekly", date(2026, 7, 5)))

    def test_toilet_weekly_keeps_two_on_one_off_cycle(self) -> None:
        self.weekly.set_anchor("toilet", date(2026, 6, 13))

        self.assertTrue(self.weekly.is_cleaning_saturday("toilet", date(2026, 6, 13)))
        self.assertTrue(self.weekly.is_cleaning_saturday("toilet", date(2026, 6, 20)))
        self.assertFalse(self.weekly.is_cleaning_saturday("toilet", date(2026, 6, 27)))
        self.assertTrue(self.weekly.is_cleaning_saturday("toilet", date(2026, 7, 4)))

    def test_seeded_dorm_weekly_history_counts_once(self) -> None:
        seeded_store = JsonStore(":memory:")
        seeded_weekly = WeeklyService(seeded_store)
        counts = seeded_weekly.counts("dorm_weekly")

        self.assertEqual(counts["lavrentyev"], 1.0)
        self.assertEqual(counts["kurochkin"], 1.0)
        self.assertEqual(counts["kazakov"], 0.5)
        self.assertEqual(counts["orlov"], 0.5)
        self.assertEqual(counts["sovenko"], 2.0)
        self.assertEqual(counts["leontyev"], 1.0)

        seeded_store.bootstrap()
        history_items = [
            assignment
            for assignment in seeded_store.data["weekly_assignments"]
            if assignment["task_id"] == "dorm_weekly"
            and assignment["work_date"]
            in {
                "2026-05-02",
                "2026-05-09",
                "2026-05-16",
                "2026-05-23",
                "2026-05-30",
                "2026-06-06",
            }
        ]

        self.assertEqual(len(history_items), 6)

    def test_toilet_does_not_reuse_dorm_person_same_week(self) -> None:
        day = date(2026, 6, 13)

        dorm = self.weekly.ensure_assignment("dorm_weekly", day)
        toilet = self.weekly.ensure_assignment("toilet", day)

        self.assertIsNotNone(dorm)
        self.assertIsNotNone(toilet)
        dorm_people = {person_id for person_id, _ in dorm.participants}
        toilet_people = {person_id for person_id, _ in toilet.participants}
        self.assertTrue(dorm_people.isdisjoint(toilet_people))

    def test_seeded_toilet_history_makes_sovenko_next(self) -> None:
        seeded_store = JsonStore(":memory:")
        seeded_weekly = WeeklyService(seeded_store)

        counts = seeded_weekly.counts("toilet")
        assignment = seeded_weekly.ensure_assignment("toilet", date(2026, 6, 13))

        self.assertEqual(counts["sovenko"], 0.0)
        self.assertEqual(counts["klyus"], 1.0)
        self.assertEqual(counts["leontyev"], 1.0)
        self.assertEqual(counts["orlov"], 1.0)
        self.assertEqual(counts["kazakov"], 1.0)
        self.assertEqual(counts["pilugin"], 2.0)
        self.assertEqual(assignment.participants[0][0], "sovenko")

    def test_regular_bind_does_not_overwrite_occupied_person(self) -> None:
        self.store.bind_person("orlov", 101, 201)

        with self.assertRaises(ValueError):
            self.store.bind_person("orlov", 102, 202)

        self.assertEqual(self.store.data["people"]["orlov"]["telegram_id"], 101)

    def test_force_bind_moves_account_to_selected_person(self) -> None:
        self.store.remember_account(101, 201, username="serzhop", full_name="Sergey")
        self.store.bind_person("orlov", 101, 201)

        self.store.force_bind_person("leontyev", 101)

        self.assertIsNone(self.store.data["people"]["orlov"]["telegram_id"])
        self.assertEqual(self.store.data["people"]["leontyev"]["telegram_id"], 101)
        account = next(item for item in self.store.known_accounts() if item["telegram_id"] == 101)
        self.assertEqual(account["username"], "serzhop")
        self.assertEqual(account["person_id"], "leontyev")

    def test_weekly_enhanced_cleanup_counts_half_for_each(self) -> None:
        day = date(2026, 6, 13)
        assignment = self.weekly.ensure_assignment("dorm_weekly", day)
        first = assignment.participants[0][0]
        self.weekly.add_second_person("dorm_weekly", day, "leontyev")

        counts = self.weekly.counts("dorm_weekly")

        self.assertEqual(counts[first], 0.5)
        self.assertEqual(counts["leontyev"], 0.5)

    def test_weekly_replace_drops_future_generated_assignments(self) -> None:
        first_day = date(2026, 6, 13)
        second_day = date(2026, 6, 20)
        self.weekly.ensure_assignment("dorm_weekly", first_day)
        second_before = self.weekly.ensure_assignment("dorm_weekly", second_day)

        self.assertEqual(second_before.participants[0][0], "leontyev")

        self.weekly.replace_person("dorm_weekly", first_day, "leontyev")
        second_after = self.weekly.ensure_assignment("dorm_weekly", second_day)

        self.assertEqual(second_after.participants[0][0], "sharov")

    def test_past_weekly_planned_assignment_becomes_completed(self) -> None:
        day = date(2026, 6, 13)
        self.weekly.set_anchor("toilet", date(2026, 6, 20))
        assignment = self.weekly.ensure_assignment("dorm_weekly", day)

        self.assertEqual(assignment.status, "planned")
        self.assertEqual(self.weekly.complete_past_planned(day), 0)
        self.assertEqual(self.weekly.get_assignment("dorm_weekly", day).status, "planned")

        self.assertEqual(self.weekly.complete_past_planned(date(2026, 6, 14)), 1)
        self.assertEqual(self.weekly.get_assignment("dorm_weekly", day).status, "completed")
        self.assertEqual(self.weekly.history("dorm_weekly")[0].work_date, day)

    def test_past_weekly_autocomplete_creates_missing_saturday(self) -> None:
        day = date(2026, 6, 13)

        completed = self.weekly.complete_past_planned(date(2026, 6, 14))

        self.assertEqual(completed, 2)
        self.assertEqual(self.weekly.get_assignment("dorm_weekly", day).status, "completed")
        self.assertEqual(self.weekly.get_assignment("toilet", day).status, "completed")

    def test_weekly_done_missing_skips_one_and_completes_other(self) -> None:
        day = date(2026, 6, 13)
        self.weekly.ensure_assignment("dorm_weekly", day)
        self.weekly.ensure_assignment("toilet", day)

        self.weekly.mark_skipped("dorm_weekly", day)
        completed = self.weekly.complete_scheduled_for_day(day, except_task="dorm_weekly")

        self.assertEqual(completed, ["toilet"])
        self.assertEqual(self.weekly.get_assignment("dorm_weekly", day).status, "skipped")
        self.assertEqual(self.weekly.get_assignment("toilet", day).status, "completed")

    def test_record_completed_history_affects_next_pick(self) -> None:
        self.weekly.record_completed("dorm_weekly", date(2026, 6, 7), ["sharov"])

        next_assignment = self.weekly.ensure_assignment("dorm_weekly", date(2026, 6, 13))

        self.assertEqual(self.weekly.counts("dorm_weekly")["sharov"], 1.0)
        self.assertEqual(next_assignment.participants[0][0], "leontyev")

    def test_morning_pairs_follow_strict_odd_roster(self) -> None:
        first_day = self.morning.ensure_day(date(2026, 6, 8))
        second_day = self.morning.ensure_day(date(2026, 6, 9))
        fourth_day = self.morning.ensure_day(date(2026, 6, 11))

        self.assertEqual([slot.person_id for slot in first_day], ["lavrentyev", "kurochkin"])
        self.assertEqual([slot.person_id for slot in second_day], ["leontyev", "orlov"])
        self.assertEqual([slot.person_id for slot in fourth_day], ["kazakov", "lavrentyev"])

    def test_morning_borrow_creates_debt_paid_on_lender_turn(self) -> None:
        self.morning.ensure_day(date(2026, 6, 8))
        lender, debt_id = self.morning.borrow(date(2026, 6, 8), "lavrentyev")

        self.assertEqual(lender, "leontyev")
        changed_day = self.morning.get_day(date(2026, 6, 8))
        self.assertEqual([slot.person_id for slot in changed_day], ["leontyev", "kurochkin"])

        repay_day = self.morning.ensure_day(date(2026, 6, 9))
        self.assertEqual(repay_day[0].original_person_id, "leontyev")
        self.assertEqual(repay_day[0].person_id, "lavrentyev")
        debt = self.store.morning_debt(debt_id)
        self.assertEqual(debt["status"], "paid")

    def test_skipped_morning_shifts_queue_forward(self) -> None:
        self.morning.ensure_day(date(2026, 6, 8))
        self.morning.mark_skipped(date(2026, 6, 8))

        next_day = self.morning.ensure_day(date(2026, 6, 9))

        self.assertEqual([slot.person_id for slot in next_day], ["lavrentyev", "kurochkin"])

    def test_morning_restart_overwrites_already_generated_future(self) -> None:
        self.morning.preview(date(2026, 6, 8), 7)

        self.morning.restart_from_pair(date(2026, 6, 10), "orlov", "pilugin")
        restart_day = self.morning.ensure_day(date(2026, 6, 10))
        next_day = self.morning.ensure_day(date(2026, 6, 11))

        self.assertEqual([slot.person_id for slot in restart_day], ["orlov", "pilugin"])
        self.assertEqual([slot.person_id for slot in next_day], ["sovenko", "kazakov"])

    def test_morning_manual_slot_replacement_creates_debt(self) -> None:
        self.morning.ensure_day(date(2026, 6, 8))

        self.morning.replace_slot(date(2026, 6, 8), 1, "orlov")
        changed_day = self.morning.get_day(date(2026, 6, 8))
        next_day = self.morning.ensure_day(date(2026, 6, 9))

        self.assertEqual([slot.person_id for slot in changed_day], ["orlov", "kurochkin"])
        self.assertEqual([slot.person_id for slot in next_day], ["leontyev", "lavrentyev"])

    def test_morning_manual_replacement_rebuilds_generated_future_for_debt(self) -> None:
        self.morning.preview(date(2026, 6, 8), 7)

        self.morning.replace_slot(date(2026, 6, 8), 1, "orlov")
        next_day = self.morning.ensure_day(date(2026, 6, 9))

        self.assertEqual([slot.person_id for slot in next_day], ["leontyev", "lavrentyev"])


if __name__ == "__main__":
    unittest.main()
