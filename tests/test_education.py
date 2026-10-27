import unittest

from newsren import education
from tests.test_papers import XML
from newsren import papers


class EducationTests(unittest.TestCase):
    def study(self, question="Does AI improve learning?", xml=XML):
        self.assertTrue(hasattr(education, "inspect_study"))
        return education.inspect_study(papers.parse_paper(xml, "PMC1234567", "2026-10-26T12:00:00Z"), question)

    def test_design_population_sample_and_groups_have_source_spans(self):
        study = self.study()
        for field in ("population", "sample", "design", "groups", "limitations"):
            self.assertEqual(study["fields"][field]["status"], "passage_found")
            self.assertTrue(study["fields"][field]["citations"])
        self.assertIn("240 students", " ".join(row["quote"] for row in study["evidence"]))
        for row in study["evidence"]:
            self.assertEqual(row["quote"], row["source_text"][row["span"]["start"]:row["span"]["end"]])
            self.assertIn("article", row["scope"].lower())

    def test_practice_and_unassisted_outcomes_are_distinct(self):
        study = self.study()
        self.assertEqual(study["outcomes"]["practice"]["status"], "measurement_passage_found")
        self.assertEqual(study["outcomes"]["independent_test"]["status"], "measurement_passage_found")
        self.assertNotEqual(study["outcomes"]["practice"]["citations"], study["outcomes"]["independent_test"]["citations"])
        for key in ("practice", "independent_test"):
            self.assertTrue(set(study["outcomes"][key]["citations"]) <= set(study["claim_check"]["citations"]))

    def test_future_work_and_references_do_not_establish_transfer(self):
        study = self.study()
        self.assertEqual(study["outcomes"]["transfer"]["status"], "not_established")
        self.assertEqual(study["outcomes"]["retention"]["status"], "not_established")
        self.assertEqual(study["claim_check"]["status"], "needs_qualification")

    def test_generalizing_to_every_student_is_flagged_for_review(self):
        study = self.study("AI always improves learning for every student.")
        self.assertEqual(study["claim_check"]["status"], "overgeneralization_risk")
        self.assertTrue(study["claim_check"]["citations"])

    def test_missing_participant_count_is_not_invented(self):
        study = self.study(xml=XML.replace(b"240 students", b"students"))
        self.assertEqual(study["fields"]["sample"]["status"], "not_found")

    def test_measurement_plan_does_not_displace_actual_results(self):
        xml = XML.replace(b'<sec><title>Results</title>', b'<sec><title>Results</title><p>Our regression evaluates performance in assisted practice and unassisted exams.</p>')
        study = self.study(xml=xml)
        by_id = {e["id"]: e for e in study["evidence"]}
        for key, value in (("practice", "40%"), ("independent_test", "10%")):
            self.assertIn(value, by_id[study["outcomes"][key]["citations"][0]]["quote"])

    def test_nested_sections_keep_methods_and_results_context(self):
        xml = XML.replace(b'<title>Methods</title>', b'<title>Methods</title><sec><title>Participants</title>')
        xml = xml.replace(b'<sec><title>Results</title>', b'</sec><sec><title>Results</title><sec><title>Academic achievement</title>')
        xml = xml.replace(b'<sec><title>Discussion</title>', b'</sec><sec><title>Discussion</title>')
        study = self.study(xml=xml)
        self.assertEqual(study["fields"]["sample"]["status"], "passage_found")
        self.assertEqual(study["outcomes"]["practice"]["status"], "measurement_passage_found")
        self.assertEqual(study["outcomes"]["independent_test"]["status"], "measurement_passage_found")

    def test_assisted_or_unspecified_exam_does_not_establish_independent_test(self):
        for wording in (b"On the AI-assisted exam, exam scores increased by 10%.", b"On the exam, exam performance increased by 10%."):
            xml = XML.replace(b"On the subsequent unassisted exam, the general assistant group scored 10% lower than the control group.", wording)
            self.assertEqual(self.study(xml=xml)["outcomes"]["independent_test"]["status"], "not_established")


if __name__ == "__main__":
    unittest.main()
