import tempfile
import unittest
from pathlib import Path

import evaluate_clip as ev


def ann(event, start, end, badge=None):
    return {"event": event, "start": start, "end": end, "badge": badge, "person": ""}


def alert(t, event, badge=None):
    return {"t": t, "event": event, "badge": badge}


class ScoreTests(unittest.TestCase):
    def test_two_people_two_alerts_both_detected(self):
        r = ev.score([alert(4, "no-helmet"), alert(4.2, "no-helmet")], [ann("no-helmet", 3, 40), ann("no-helmet", 3, 40)])
        self.assertEqual((r["overall"]["detected"], r["overall"]["duplicates"]), (2, 0))

    def test_repeat_within_episode_is_duplicate(self):
        r = ev.score([alert(4, "no-vest"), alert(20, "no-vest")], [ann("no-vest", 3, 40)])
        self.assertEqual((r["overall"]["detected"], r["overall"]["duplicates"], r["overall"]["false_alerts"]), (1, 1, 0))

    def test_alert_outside_any_episode_is_false(self):
        r = ev.score([alert(100, "no-vest")], [ann("no-vest", 3, 40)])
        self.assertEqual((r["overall"]["missed"], r["overall"]["false_alerts"]), (1, 1))
        self.assertEqual(r["overall"]["precision"], 0.0)

    def test_grace_after_episode_end(self):
        self.assertEqual(ev.score([alert(43, "FALL")], [ann("FALL", 30, 40)], grace=5)["overall"]["detected"], 1)
        self.assertEqual(ev.score([alert(46, "FALL")], [ann("FALL", 30, 40)], grace=5)["overall"]["detected"], 0)

    def test_wrong_event_does_not_match(self):
        r = ev.score([alert(5, "no-gloves")], [ann("no-helmet", 3, 40)])
        self.assertEqual((r["overall"]["detected"], r["overall"]["false_alerts"]), (0, 1))

    def test_identity_counts_prefer_own_badge(self):
        alerts = [alert(4, "no-helmet", "SSW1:sara"), alert(4.1, "no-helmet", "SSW1:ali"), alert(4.2, "no-helmet")]
        anns = [ann("no-helmet", 3, 40, "SSW1:ali"), ann("no-helmet", 3, 40, "SSW1:sara"), ann("no-helmet", 3, 40, "SSW1:omar")]
        ident = ev.score(alerts, anns)["overall"]["identity"]
        self.assertEqual((ident["correct"], ident["wrong"], ident["unidentified"]), (2, 0, 1))

    def test_delay_and_rates(self):
        r = ev.score([alert(5, "no-helmet")], [ann("no-helmet", 3, 40), ann("no-vest", 3, 40)])
        self.assertEqual(r["overall"]["delay_s_median"], 2)
        self.assertEqual(r["overall"]["recall"], 0.5)
        self.assertEqual(r["by_event"]["no-vest"]["missed"], 1)


class FileTests(unittest.TestCase):
    def test_template_parses_and_comments_are_skipped(self):
        rows = ev.load_annotations(Path(__file__).with_name("clip_annotations_template.csv"))
        self.assertEqual([r["event"] for r in rows], ["no-helmet", "no-vest", "INACTIVITY", "FALL"])
        self.assertEqual(rows[1]["badge"], "SSW1:replace-me")

    def test_rejects_end_before_start(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("event,start_s,end_s\nno-vest,10,5\n")
        with self.assertRaises(ValueError):
            ev.load_annotations(Path(f.name))

    def test_activity_records_are_not_alerts(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write('{"t": 1, "event": "SIGHTING"}\n{"t": 2, "event": "no-vest"}\n')
        self.assertEqual([e["event"] for e in ev.load_events(Path(f.name))], ["no-vest"])


if __name__ == "__main__":
    unittest.main()
