import unittest

from newsren import learning
from newsren.pages import render_story
from tests.test_research import evidence_story


class LearningTests(unittest.TestCase):
    def test_modes_have_definitions_teaching_plan_and_decision_questions(self):
        self.assertTrue(hasattr(learning, "learning_material"))
        material = learning.learning_material(evidence_story())
        self.assertIn("revenue", [row["term"] for row in material["concepts"]])
        revenue = next(row for row in material["concepts"] if row["term"] == "revenue")
        self.assertIn("expenses", revenue["definition"])
        self.assertGreaterEqual(len(material["educator"]["objectives"]), 2)
        self.assertTrue(material["educator"]["quiz"])
        self.assertTrue(material["professional"]["questions"])
        self.assertNotEqual(material["student"], material["professional"])

    def test_quiz_correct_answer_is_exactly_supported_by_source(self):
        self.assertTrue(hasattr(learning, "learning_material"))
        story = evidence_story()
        quiz = learning.learning_material(story)["educator"]["quiz"]
        source_question = next(row for row in quiz if row["kind"] == "source_claim")
        correct = source_question["options"][source_question["answer"]]
        self.assertEqual(correct, "Acme Orion reports revenue of 100 million dollars.")
        self.assertIn(correct, story["excerpt"])

    def test_unknown_topic_does_not_invent_a_definition_from_a_title_word(self):
        self.assertTrue(hasattr(learning, "learning_material"))
        story = evidence_story(title="Unexplained Zorb device")
        story["excerpt"] = "A Zorb device was announced today."
        story["summary_sentences"] = [story["excerpt"]]
        concepts = learning.learning_material(story)["concepts"]
        self.assertNotIn("zorb", [row["term"] for row in concepts])
        self.assertTrue(any(row["term"] == "source" for row in concepts))

    def test_actual_story_renders_different_learning_modes(self):
        html = render_story(evidence_story())
        student = html.split('data-audience="student"')[1].split('data-audience="educator"')[0]
        educator = html.split('data-audience="educator"')[1].split('data-audience="professional"')[0]
        professional = html.split('data-audience="professional"')[1].split('id="story-follow"')[0]
        self.assertIn("Concepts in plain language", student)
        self.assertIn("Learning objectives", educator)
        self.assertIn("Check your understanding", educator)
        self.assertIn("Decision questions", professional)
        self.assertIn("Evidence limits", professional)
        self.assertNotIn("Learning objectives", student)
        self.assertNotIn("Decision questions", educator)


if __name__ == "__main__":
    unittest.main()
