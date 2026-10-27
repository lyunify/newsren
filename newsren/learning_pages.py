"""Render teaching material separately from quoted news evidence."""

from html import escape

from newsren.learning import learning_material


def render_learning(story):
    material = learning_material(story)
    concepts = "".join(f'<dt>{escape(row["term"])}</dt><dd>{escape(row["definition"])}</dd>' for row in material["concepts"])
    steps = "".join(f'<li>{escape(step)}</li>' for step in material["student"]["steps"])
    student = f'<h4>Concepts in plain language</h4><p class="muted">General teaching material, separate from the reported claims below.</p><dl class="concepts">{concepts}</dl><ol>{steps}</ol>'
    goals = "".join(f'<li>{escape(goal)}</li>' for goal in material["educator"]["objectives"])
    quiz = []
    for number, question in enumerate(material["educator"]["quiz"], 1):
        options = "".join(f'<li>{escape(option)}</li>' for option in question["options"])
        answer = question["options"][question["answer"]]
        quiz.append(f'<article class="quiz"><p><strong>{number}. {escape(question["question"])}</strong></p><ol type="A">{options}</ol><details><summary>Check answer</summary><p>{escape(answer)}</p><p>{escape(question["explanation"])}</p></details></article>')
    educator = f'<h4>Learning objectives</h4><ul>{goals}</ul><h4>Classroom activity</h4><p>{escape(material["educator"]["activity"])}</p><h4>Check your understanding</h4>{"".join(quiz)}'
    questions = "".join(f'<li>{escape(question)}</li>' for question in material["professional"]["questions"])
    professional = f'<h4>Decision questions</h4><ul>{questions}</ul><h4>Evidence limits</h4><p>{escape(material["professional"]["limits"])}</p>'
    return {"student": student, "educator": educator, "professional": professional}
