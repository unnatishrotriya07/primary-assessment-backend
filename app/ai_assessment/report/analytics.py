import json
import random

def step_transcript_cleanup(interview, raw_turns: list) -> dict:
    if not raw_turns:
        return {"dialogue": []}

    dialogue_text = ""
    for turn in raw_turns:
        role_label = "Buddy (AI)" if turn["role"] == "ai" else f"Student ({interview.student_name})"
        dialogue_text += f"{role_label}: {turn['text']}\n"

    prompt = f"""You are a school transcription assistant. Clean up the following student assessment dialogue.
Remove verbal speech fillers like "um", "uh", "like", "you know" and speech-to-text stuttering.
Correct obvious grammar and capitalization errors but strictly preserve the exact semantic content and factual meaning of the student's responses.

Raw Dialogue:
{dialogue_text}

Respond ONLY with a JSON object of this structure:
{{
  "dialogue": [
    {{
      "role": "ai" or "student",
      "text": "cleaned text",
      "category": "category name or null"
    }}
  ]
}}"""
    system_instruction = "You are a transcription formatting engine. Return raw JSON only, no explanation."
    
    fallback_data = {
        "dialogue": [
            {"role": t["role"], "text": t["text"], "category": t.get("category")}
            for t in raw_turns
        ]
    }
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_question_mapping(q_list: list, dialogue_turns: list) -> dict:
    dialogue_text = ""
    for t in dialogue_turns:
        dialogue_text += f"{t['role'].upper()}: {t['text']}\n"

    prompt = f"""You are an educational assistant. Map the student's final answers in the transcript to the assessment questions.
Identify what the student responded for each specific assessment question listed.

Assessment Questions:
{json.dumps(q_list, indent=2)}

Dialogue Transcript:
{dialogue_text}

Respond ONLY with a JSON list containing the mapped answer for each question index:
[
  {{
    "index": <question index number>,
    "question": "<question text>",
    "student_answer": "<what the student said or typed in response to this question, or empty string if they skipped it>",
    "expected_answer": "<expected correct answer>",
    "options": <options array>,
    "question_type": "mcq or tita"
  }}
]"""
    system_instruction = "You are a question mapping engine. Return a raw JSON list only, no markdown, no explanation."
    
    fallback_data = []
    student_turns = [t for t in dialogue_turns if t["role"] == "student"]
    for idx, q in enumerate(q_list):
        ans_text = ""
        if idx < len(student_turns):
            ans_text = student_turns[idx]["text"]
        fallback_data.append({
            "index": q["index"],
            "question": q["text"],
            "student_answer": ans_text,
            "expected_answer": q["expected"],
            "options": q["options"],
            "question_type": q["type"]
        })
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_answer_understanding(mapped_questions: list) -> dict:
    prompt = f"""You are an educational response analysis assistant.
Analyze the student's responses to understand their semantic intent.
Identify:
1. Did the student skip or decline to answer (e.g., "I don't know", "skip", silence, etc.)?
2. Did the student provide a partial or incomplete answer?
3. Were there potential speech recognition issues (mumbled, gibberish)?
4. Is it a clean, complete response?

Mapped Answers:
{json.dumps(mapped_questions, indent=2)}

Respond ONLY with a JSON list of objects matching the input array order:
[
  {{
    "index": <index>,
    "question": "<question>",
    "student_answer": "<student_answer>",
    "is_skipped": <true/false>,
    "is_partial": <true/false>,
    "has_speech_issue": <true/false>,
    "cleaned_response": "<semantic response summary>"
  }}
]"""
    system_instruction = "You are a semantic answer analyzer. Return raw JSON list only."
    fallback_data = [
        {
            "index": q["index"],
            "question": q["question"],
            "student_answer": q["student_answer"],
            "is_skipped": q["student_answer"] == "" or "don't know" in q["student_answer"].lower(),
            "is_partial": False,
            "has_speech_issue": False,
            "cleaned_response": q["student_answer"]
        } for q in mapped_questions
    ]
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_per_question_evaluation(ua: dict, db_q, assessment, interview, expected_answer, student_response) -> dict:
    chapter_title = db_q.chapter.title if db_q and db_q.chapter else "General"
    concept_name = db_q.section if db_q and db_q.section else "Core Understanding"
    paragraph_text = db_q.reference_text if db_q and db_q.reference_text else (db_q.chapter.text_content if db_q and db_q.chapter else "")
    bloom_level = db_q.cognitive_level if db_q and db_q.cognitive_level else "remembering"
    q_text = ua.get("question", "").strip()

    prompt = f"""You are an educational diagnostic grader evaluating a primary student response.
Evaluate this student response against the textbook chapter context and expected answer.
Ignore minor spelling or grammatical errors. Grade based on conceptual understanding.

Assessment Metadata:
- Subject: {assessment.subject.name if assessment and assessment.subject else "General"}
- Class Grade: {interview.student_class}
- Bloom Cognitive Level: {bloom_level}

Chapter Content Context:
- Chapter Title: {chapter_title}
- Concept Focus: {concept_name}
- Reference Textbook Paragraph: {paragraph_text}

Question Details:
- Question: {q_text}
- Expected Correct Answer: {expected_answer}

Student Response:
- Student's Answer: {student_response}

Evaluate and return ONLY a JSON object:
{{
  "concept": "{concept_name}",
  "masteryScore": <score between 0 and 100 representing mastery of the concept>,
  "confidence": <score between 0 and 100 representing your grading confidence>,
  "reasoning": "<very concise description of why the score was given, under 15 words>",
  "misconception": "<concise description of student's misconception, or null if correct>",
  "evidence": "<the exact key phrase from the Student's Answer that proves this score>"
}}"""
    system_instruction = "You are a precise diagnostic grader. Return raw JSON object only. Do NOT output natural language or explanations outside the JSON."
    
    fallback_val = {
        "concept": concept_name,
        "masteryScore": 75 if student_response != "" else 0,
        "confidence": 90,
        "reasoning": "Heuristic match verification.",
        "misconception": None if student_response != "" else "No response provided",
        "evidence": student_response[:30]
    }
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_val,
        "concept_name": concept_name
    }

def step_concept_mastery_detection(evaluated_answers: list) -> dict:
    prompt = f"""You are a child diagnostics specialist.
Aggregate all per-question evaluations to compute the student's mastery.

Evaluations:
{json.dumps(evaluated_answers, indent=2)}

Respond ONLY with a JSON object:
{{
  "subjectMastery": <overall grade average 0-100>,
  "chapterMastery": <chapter average 0-100>,
  "concepts": [
    {{
      "name": "<concept name>",
      "score": <0-100>,
      "understood": <true/false>,
      "evidence": "<brief phrase evidence>"
    }}
  ],
  "bloomDistribution": {{
    "remembering": <average score 0-100 or null>,
    "understanding": <average score 0-100 or null>,
    "applying": <average score 0-100 or null>,
    "analyzing": <average score 0-100 or null>
  }}
}}"""
    system_instruction = "Return aggregated masteries in raw JSON only."
    fallback_data = {
        "subjectMastery": 75,
        "chapterMastery": 75,
        "concepts": [],
        "bloomDistribution": {}
    }
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }
