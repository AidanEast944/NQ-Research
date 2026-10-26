import sys, os, unittest, tempfile, plistlib
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import heartbeat as hb

NOW = datetime(2026, 10, 26, 18, 10)  # Monday


def make_plist(label, hour, minute, weekday=None, err=None):
    d = tempfile.mkdtemp()
    sci = {"Hour": hour, "Minute": minute}
    if weekday is not None:
        sci["Weekday"] = weekday
    body = {"Label": label, "StartCalendarInterval": sci}
    if err:
        body["StandardErrorPath"] = err
    p = os.path.join(d, label + ".plist")
    with open(p, "wb") as f:
        plistlib.dump(body, f)
    return p


def fake(runs, code=0, rc=0):
    return lambda label: (rc, f"state = not running\n\truns = {runs}\n\tlast exit code = {code}\n")


class TestHeartbeat(unittest.TestCase):
    def test_all_ok(self):
        p = make_plist("com.nqresearch.a", 17, 5)
        probs, st, _ = hb.check(NOW, fake(6), [p], {"com.nqresearch.a": {"runs": 5, "err_size": 0}})
        self.assertEqual(probs, [])
        self.assertEqual(st["com.nqresearch.a"]["runs"], 6)

    def test_job_did_not_run(self):
        p = make_plist("com.nqresearch.a", 17, 5)
        probs, _, _ = hb.check(NOW, fake(5), [p], {"com.nqresearch.a": {"runs": 5, "err_size": 0}})
        self.assertTrue(any("did not run" in x for x in probs))

    def test_not_yet_due_is_ok(self):
        p = make_plist("com.nqresearch.late", 23, 0)
        probs, _, _ = hb.check(NOW, fake(5), [p], {"com.nqresearch.late": {"runs": 5, "err_size": 0}})
        self.assertEqual(probs, [])

    def test_weekday_restricted_job_skipped_on_other_days(self):
        p = make_plist("com.nqresearch.sun", 17, 5, weekday=0)  # Sundays only; NOW is Monday
        probs, _, _ = hb.check(NOW, fake(5), [p], {"com.nqresearch.sun": {"runs": 5, "err_size": 0}})
        self.assertEqual(probs, [])

    def test_bad_exit_code(self):
        p = make_plist("com.nqresearch.a", 17, 5)
        probs, _, _ = hb.check(NOW, fake(6, code=1), [p], {"com.nqresearch.a": {"runs": 5, "err_size": 0}})
        self.assertTrue(any("exit code 1" in x for x in probs))

    def test_not_loaded(self):
        p = make_plist("com.nqresearch.a", 17, 5)
        probs, _, _ = hb.check(NOW, lambda l: (113, ""), [p], {})
        self.assertTrue(any("not loaded" in x for x in probs))

    def test_error_file_growth(self):
        err = tempfile.mktemp()
        open(err, "w").write("boom")
        p = make_plist("com.nqresearch.a", 17, 5, err=err)
        probs, _, _ = hb.check(NOW, fake(6), [p], {"com.nqresearch.a": {"runs": 5, "err_size": 0}})
        self.assertTrue(any("error file" in x for x in probs))

    def test_first_run_has_no_false_alarms(self):
        p = make_plist("com.nqresearch.a", 17, 5)
        probs, _, _ = hb.check(NOW, fake(5), [p], {})
        self.assertEqual(probs, [])

    def test_never_exited_ok(self):
        p = make_plist("com.nqresearch.a", 17, 5)
        probs, _, _ = hb.check(NOW, lambda l: (0, "runs = 0\n\tlast exit code = (never exited)\n"), [p], {})
        self.assertEqual(probs, [])


if __name__ == "__main__":
    unittest.main()
