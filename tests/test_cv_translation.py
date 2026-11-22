"""Regression checks for CV wording and template tokens; no network required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("translate_markdown", ROOT / "build/translate-markdown.py")
translation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(translation)

SOURCE = """## Education

- **Ph.D. in Computer Science** · *2024 - 2027*  
  University of Lille · Villeneuve-d’Ascq, France
- **Master in Natural Language Processing** · *2022 - 2024*  
  University of Lorraine · Nancy, France
- **Bachelor in Data Science** · *2019 - 2022*  
  Lebanese University · Beirut, Lebanon

- **PhD Student** · *Oct. 2024 - Oct. 2027*  

## Hobbies

## Teaching

{{TEACHING_FROM_DATA}}
{{TEACHING_SHORT_FROM_DATA}}

## Professional Experience

  Centre Inria de l’Université de Lille · Villeneuve-d’Ascq, France
"""


class CVTranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        for name, value in [
            ("TRANSLATION_CACHE_FILE", self.directory / "cache.json"),
            ("TRANSLATION_STATE_FILE", self.directory / "state.json"),
        ]:
            patcher = patch.object(translation, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # A provider call is a failure: these labels and tokens must be deterministic.
        patcher = patch.object(translation.MarkdownTranslator, "_translate_chunk", side_effect=AssertionError("Unexpected provider/cache lookup"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_cv(self, text):
        self.assertIn("## Éducation", text)
        self.assertIn("## Loisirs", text)
        self.assertIn("## Enseignement", text)
        self.assertIn("## Expériences professionnelles", text)
        self.assertIn("- **Doctorat en informatique** · *2024 - 2027*  \n", text)
        self.assertIn("- **Master de traitement automatique des langues** · *2022 - 2024*  \n", text)
        self.assertIn("- **Licence en science des données** · *2019 - 2022*  \n", text)
        self.assertIn("- **Doctorant** · *Oct. 2024 - Oct. 2027*  \n", text)
        self.assertIn("  Université de Lille · Villeneuve-d’Ascq, France\n", text)
        self.assertIn("  Université de Lorraine · Nancy, France\n", text)
        self.assertIn("  Université Libanaise · Beyrouth, Liban\n", text)
        self.assertIn("Centre Inria de l’Université de Lille · Villeneuve-d’Ascq, France", text)
        self.assertIn("{{TEACHING_FROM_DATA}}", text)
        self.assertIn("{{TEACHING_SHORT_FROM_DATA}}", text)
        self.assertNotIn("M.Sc.", text)
        self.assertNotIn("B.Sc.", text)

    def test_fresh_translation_preserves_wording_dates_and_tokens(self):
        translator = translation.MarkdownTranslator(source="en", target="fr")
        self.assert_cv(translator.translate_markdown(SOURCE))

    def test_phd_student_is_masculine(self):
        translator = translation.MarkdownTranslator(source="en", target="fr")
        self.assertEqual(translator._postprocess_translation("**Doctorante**"), "**Doctorant**")

    def test_glossary_terms_are_locked_inside_sentences(self):
        translator = translation.MarkdownTranslator(source="en", target="fr")
        seen = []
        with patch.object(translator, "_translate_protected_text", side_effect=lambda text: seen.append(text) or text):
            out = translator._translate_plain_text("I did a Master in Natural Language Processing at University of Lorraine.")
        self.assertNotIn("Natural Language Processing", seen[0])
        self.assertIn("Master de traitement automatique des langues", out)
        self.assertIn("Université de Lorraine", out)

    def test_dropped_link_placeholder_is_not_accepted(self):
        translator = translation.MarkdownTranslator(source="en", target="fr")
        def provider(text, attempts=3):
            return "Membre du comité d’organisation," if "XQMDTOKEN" in text else "Membre du comité d’organisation, "
        with patch.object(translator, "_translate_chunk", side_effect=provider), \
                patch.object(translator, "_remember_translation"):
            out = translator._translate_plain_text("Member of the organizing committee, [ESUG’25](https://esug.org).")
        self.assertIn("[ESUG’25](https://esug.org)", out)

    def test_misaligned_translation_is_refused_not_overwritten(self):
        source = self.directory / "cv.md"
        output = self.directory / "cv-fr.md"
        source.write_text("## Hobbies\n\nHello\n")
        output.write_text("## Loisirs\n\nBonjour corrigé\n\n---\n")  # a line added by hand
        state = {translation.state_key(output): [translation.line_fingerprint(line) for line in source.read_text().split("\n")]}
        translation.TRANSLATION_STATE_FILE.write_text(json.dumps(state))
        argv = ["translate-markdown.py", "--input", str(source), "--output", str(output), "--source", "en", "--target", "fr", "--quiet"]
        with patch("sys.argv", argv), self.assertRaises(SystemExit):
            translation.main()
        self.assertIn("Bonjour corrigé", output.read_text())

    def test_other_languages_and_prose_are_not_rewritten(self):
        self.assertIsNone(translation.fixed_cv_translation("## Education", "en", "de"))
        self.assertIsNone(translation.fixed_cv_translation("Education is important.", "en", "fr"))

    def test_cached_output_then_repeat_then_date_change(self):
        source = self.directory / "cv.md"
        output = self.directory / "cv-fr.md"
        source.write_text(SOURCE)
        stale = SOURCE.replace("## Education", "## éducation").replace("## Hobbies", "## Les loisirs")
        stale = stale.replace("Master in Natural Language Processing", "M.Sc. en traitement du langage naturel")
        stale = stale.replace("Bachelor in Data Science", "B.Sc. en science des données")
        stale = stale.replace("{{TEACHING_FROM_DATA}}", "{{ANCIEN_MOT_CLE}}")
        output.write_text(stale)
        state = {translation.state_key(output): [translation.line_fingerprint(line) for line in SOURCE.split("\n")]}
        translation.TRANSLATION_STATE_FILE.write_text(json.dumps(state))
        argv = ["translate-markdown.py", "--input", str(source), "--output", str(output), "--source", "en", "--target", "fr", "--quiet"]
        with patch("sys.argv", argv):
            self.assertEqual(translation.main(), 0)
            first = output.read_text()
            self.assert_cv(first)
            self.assertEqual(translation.main(), 0)
            self.assertEqual(first, output.read_text())
            source.write_text(SOURCE.replace("2022 - 2024", "2022 - 2025"))
            self.assertEqual(translation.main(), 0)
            self.assertIn("**Master de traitement automatique des langues** · *2022 - 2025*", output.read_text())


if __name__ == "__main__":
    unittest.main()
