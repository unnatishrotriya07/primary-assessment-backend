import re
from sqlalchemy.orm import Session
from app.core.models.student_assessment import StudentAssessment
from app.core.models.assessment import Assessment

def get_basic_class_questions(class_name: str) -> list:
    name_lower = class_name.lower()
    if "1" in name_lower or "one" in name_lower or "2" in name_lower or "two" in name_lower:
        return [
            {
                "q": "Great! What is your favourite game to play with your friends, and who do you play it with?",
                "skill": "communication",
                "category": "Basic Social"
            },
            {
                "q": "If you had 4 cookies and ate 2, how many cookies would you have left to share?",
                "skill": "numeracy",
                "category": "Basic Math"
            }
        ]
    elif "3" in name_lower or "three" in name_lower or "4" in name_lower or "four" in name_lower:
        return [
            {
                "q": "Wonderful! Can you tell me about your favourite animal and what they like to do?",
                "skill": "creativity",
                "category": "Basic Creativity"
            },
            {
                "q": "If a box contains 12 pencils and you give 4 to your classmate, how many pencils remain in the box?",
                "skill": "numeracy",
                "category": "Basic Math"
            }
        ]
    else:
        return [
            {
                "q": "Awesome! What is your favourite hobby when you are not at school, and what makes it fun?",
                "skill": "communication",
                "category": "Basic Social"
            },
            {
                "q": "If you have 20 books and you read 5 of them this week, how many books do you have left to read?",
                "skill": "numeracy",
                "category": "Basic Math"
            }
        ]

def get_grade_adapted_persona(student_grade: str) -> dict:
    grade_num = 3
    try:
        m = re.search(r'\d+', student_grade)
        if m:
            grade_num = int(m.group(0))
    except Exception:
        pass

    if grade_num <= 2:
        return {
            "grade_group": "Grade 1-2",
            "voice_speed": "very slow",
            "expressiveness": "very high",
            "sentence_limit": "5-8 words",
            "style": "cheerful, slow, expressive"
        }
    elif grade_num <= 5:
        return {
            "grade_group": "Grade 3-5",
            "voice_speed": "normal",
            "expressiveness": "high",
            "sentence_limit": "8-15 words",
            "style": "friendly, encouraging, teacher-like"
        }
    elif grade_num <= 8:
        return {
            "grade_group": "Grade 6-8",
            "voice_speed": "normal",
            "expressiveness": "medium",
            "sentence_limit": "15-20 words",
            "style": "professional, energetic"
        }
    else:
        return {
            "grade_group": "Grade 9-10",
            "voice_speed": "normal",
            "expressiveness": "calm",
            "sentence_limit": "20-25 words",
            "style": "calm, respectful, examiner style"
        }

class SessionBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build_questions_and_persona(self, sa: StudentAssessment, assessment: Assessment, token: str) -> tuple:
        # Build dynamic list of questions
        dynamic_questions = []

        subject_name = assessment.subject.name.lower() if assessment.subject else ""
        default_skill = "communication"
        if "math" in subject_name or "num" in subject_name:
            default_skill = "numeracy"
        elif "art" in subject_name or "creat" in subject_name:
            default_skill = "creativity"

        from app.core.services.assessment_service import AssessmentService
        asmt_service = AssessmentService(self.db)
        questions_to_use = asmt_service.get_questions_for_session(assessment.id, seed_str=token)

        for q in questions_to_use:
            hint_val = getattr(q, 'hint', None)
            if not hint_val:
                text_lower = q.text.lower()
                if "numerator" in text_lower:
                    hint_val = "In a fraction, the numerator is the number on the top, which tells us how many parts we are taking."
                elif "denominator" in text_lower:
                    hint_val = "In a fraction, the denominator is the bottom number, which tells us the total number of equal parts."
                elif "equivalent" in text_lower:
                    hint_val = "To find equivalent fractions, think about multiplying or dividing both top and bottom numbers by the same number."
                elif " राहुल" in text_lower or "rahul" in text_lower or "pizza" in text_lower:
                    hint_val = "Think about the total number of slices as the bottom number, and the slices eaten as the top number."
                elif "shaded" in text_lower or "visual" in text_lower or "circle" in text_lower:
                    hint_val = "Count how many parts are colored blue compared to the total number of parts in the shape."
                else:
                    hint_val = "Let's think together. Can you break the question down or explain what you think it means?"
            
            dynamic_questions.append({
                "id": q.id,
                "q": q.text,
                "skill": q.bloom_level or default_skill,
                "category": q.chapter.title if q.chapter else "Assessment Content",
                "hints": q.hints if q.hints else [hint_val],
                "expected_concepts": q.expected_concepts or [],
                "followups": q.followups or [],
                "learning_objective": q.learning_objective or "",
            })

        if len(dynamic_questions) == 0:
            dynamic_questions.append({
                "id": 1,
                "q": "If you could visit any place in the world, where would you go and why?",
                "skill": "creativity",
                "category": "Aspirations",
                "hints": ["Think of your favorite place, maybe a park or beach.", "Why does that place make you happy?"],
                "expected_concepts": ["place", "reason"],
                "followups": ["What would you do when you get there?"],
                "learning_objective": "Communicate creative thoughts clearly",
            })

        grade_persona = get_grade_adapted_persona(sa.student_class or "Grade 3")
        return dynamic_questions, grade_persona, default_skill
