import sys, os, unittest, tempfile, tarfile
from datetime import date
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import backup_state as bs


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.root = tempfile.mkdtemp()
        os.chdir(self.root)
        os.makedirs("data/raw_nq_extended"); os.makedirs("registry"); os.makedirs("results"); os.makedirs("lab"); os.makedirs("launchd")
        open("data/a_paper_account.json", "w").write("{}")
        open("data/raw_nq_extended/x.csv", "w").write("1")
        open("research_log.md", "w").write("log")
        open(".env", "w").write("SECRET=1")
        open("lab/.env.local", "w").write("SECRET=2")
        self.dest = tempfile.mkdtemp()

    def tearDown(self):
        os.chdir(self.cwd)

    def names(self, f):
        with tarfile.open(f) as t:
            return t.getnames()

    def test_daily_contains_state_not_archives_or_secrets(self):
        res = bs.run(self.dest, today=date(2026, 10, 26))   # Monday
        self.assertEqual(len(res), 1)
        n = self.names(res[0][0])
        self.assertIn("data/a_paper_account.json", n)
        self.assertIn("research_log.md", n)
        self.assertFalse(any("raw_nq" in x for x in n))
        self.assertFalse(any(x.endswith(".env") or ".env." in x for x in n))

    def test_sunday_adds_weekly_archives(self):
        res = bs.run(self.dest, today=date(2026, 10, 25))   # Sunday
        self.assertEqual(len(res), 2)
        self.assertTrue(any("raw_nq" in x for x in self.names(res[1][0])))

    def test_prunes_old_daily(self):
        for d in range(1, 21):
            bs.run(self.dest, today=date(2026, 9, d) if date(2026, 9, d).weekday() != 6 else date(2026, 9, d))
        daily = [f for f in os.listdir(self.dest) if f.startswith("state_")]
        self.assertEqual(len(daily), bs.KEEP_DAILY)


if __name__ == "__main__":
    unittest.main()
