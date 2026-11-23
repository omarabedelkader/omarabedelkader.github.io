"""The one-page CV is generated from the full CV in both languages; no network required."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import short_cv  # noqa: E402

ENGLISH = (ROOT / "sources" / "cv.md").read_text(encoding="utf-8")
FRENCH = (ROOT / "sources" / "cv-fr.md").read_text(encoding="utf-8")
ROW_RE = re.compile(r"^- \[[^\]]*\]\{\.cvdate\} ", re.MULTILINE)


class ShortCVTests(unittest.TestCase):
    def setUp(self):
        self.english = short_cv.shorten(ENGLISH, language="en")
        self.french = short_cv.shorten(FRENCH, reference=ENGLISH, language="fr")

    def test_both_languages_have_the_same_rows(self):
        self.assertGreater(len(ROW_RE.findall(self.english)), 10)
        self.assertEqual(len(ROW_RE.findall(self.english)), len(ROW_RE.findall(self.french)))

    def test_sections_use_the_language_of_the_cv(self):
        for slug in ("key-figures", "education", "experience", "publications", "services", "volunteering"):
            self.assertIn(f"## {short_cv.LABELS['en'][slug]}", self.english)
            self.assertIn(f"## {short_cv.LABELS['fr'][slug]}", self.french)

    def test_key_figures_and_languages_are_summarised(self):
        self.assertRegex(self.english, r"\d+ publications \(")
        self.assertIn("**Languages:**", self.english)
        self.assertIn("**Langues\u00a0:**", self.french)

    def test_own_name_is_bold_in_every_publication(self):
        publications = self.english.split("## Publications", 1)[1].split("\n## ", 1)[0]
        rows = ROW_RE.findall(publications)
        self.assertTrue(rows)
        self.assertEqual(len(rows), publications.lower().count("**abedelkader, o.**"))


if __name__ == "__main__":
    unittest.main()
