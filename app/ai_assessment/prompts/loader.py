import os
from typing import Union

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_prompt_template(relative_path: str) -> str:
    full_path = os.path.join(BASE_DIR, relative_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def load_system_instruction() -> str:
    return get_prompt_template("system/system_instruction.txt").strip()

def load_persona_rewrite(persona_style: str, sentence_limit: str, text: str) -> str:
    template = get_prompt_template("teacher/persona_rewrite.txt")
    return template.format(
        persona_style=persona_style,
        sentence_limit=sentence_limit,
        text=text
    )

def load_response_analysis(question_text: str, correct_answer: str, expected_concepts: list, student_response: str) -> str:
    template = get_prompt_template("student/response_analysis.txt")
    import json
    return template.format(
        question_text=question_text,
        correct_answer=correct_answer,
        expected_concepts=json.dumps(expected_concepts),
        student_response=student_response
    )

def load_evaluate_interview(student_name: str, transcript_text: str) -> str:
    template = get_prompt_template("report/evaluate_interview.txt")
    return template.format(
        student_name=student_name,
        transcript_text=transcript_text
    )

def load_evaluate_answer(question_text: str, correct_answer: str, student_answer: str) -> str:
    template = get_prompt_template("evaluation/evaluate_answer.txt")
    return template.format(
        question_text=question_text,
        correct_answer=correct_answer,
        student_answer=student_answer
    )

def load_generate_questions(
    count: int,
    subject_name: str,
    chapter_number: str,
    chapter_title: str,
    difficulty: str,
    cognitive_level: str,
    chapter_content: str,
    selected_text: str
) -> str:
    template = get_prompt_template("evaluation/generate_questions.txt")
    return template.format(
        count=count,
        subject_name=subject_name,
        chapter_number=chapter_number,
        chapter_title=chapter_title,
        difficulty=difficulty,
        cognitive_level=cognitive_level,
        chapter_content=chapter_content,
        selected_text=selected_text
    )

def load_generate_report(score: Union[int, float], accuracy: Union[int, float], class_name: str) -> str:
    template = get_prompt_template("report/generate_report.txt")
    return template.format(
        score=score,
        accuracy=accuracy,
        class_name=class_name
    )
