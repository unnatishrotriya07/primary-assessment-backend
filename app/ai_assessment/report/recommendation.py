import json

def step_learning_gap_detection(evaluated_answers: list, concept_mastery: dict) -> dict:
    prompt = f"""You are an educational gap detector. Analyze evaluations and mastery to pinpoint learning gaps and misconceptions.

Evaluations:
{json.dumps(evaluated_answers, indent=2)}

Mastery:
{json.dumps(concept_mastery, indent=2)}

Respond ONLY with a JSON object:
{{
  "gaps": [
    {{
      "concept": "<concept name>",
      "description": "<specific student misconception detail>",
      "severity": "<High/Medium/Low>"
    }}
  ]
}}"""
    system_instruction = "Return learning gaps in raw JSON only."
    fallback_data = {"gaps": []}
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_strength_detection(evaluated_answers: list) -> dict:
    prompt = f"""Identify the student's core academic strengths and concepts understood from their correct answers:
{json.dumps(evaluated_answers, indent=2)}

Guidelines:
- Focus solely on academic/subject concept understanding (e.g. "Understands subtraction as taking away", "Strong counting skills").
- Do NOT include emotional, sentiment, or behavioral remarks.

Respond ONLY with a JSON object:
{{
  "strengths": [
     "<academic strength description, max 10 words>"
  ]
}}"""
    system_instruction = "Return academic strengths in raw JSON only."
    
    # Generate meaningful fallback strengths directly from evaluated answers
    matched = []
    for a in evaluated_answers:
        if isinstance(a, dict) and (a.get("isCorrect") or a.get("score", 0) >= 70):
            for c in a.get("matched_concepts", []):
                if c and c not in matched:
                    matched.append(f"Understands {c}")
            if not a.get("matched_concepts") and a.get("concept"):
                c = a.get("concept")
                if c and c not in matched:
                    matched.append(f"Understands {c}")
    
    fallback_data = {"strengths": matched[:3] if matched else ["Demonstrated understanding of core concepts"]}
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_recommendation_engine(learning_gaps: dict) -> dict:
    prompt = f"""Provide actionable recommendations, classroom activities, and revision topics to resolve these gaps:
{json.dumps(learning_gaps, indent=2)}

Respond ONLY with a JSON object:
{{
  "recommendations": ["<recommendation description>"],
  "classroomActivities": ["<suggested hands-on activity>"],
  "revisionTopics": ["<specific chapter/concept topic to revise>"]
}}"""
    system_instruction = "Return recommendations in raw JSON only."
    fallback_data = {
        "recommendations": ["Review chapter sections."],
        "classroomActivities": ["Concept tracing worksheet."],
        "revisionTopics": ["Core concepts."]
    }
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_teacher_summary(student_name: str, mastery: dict, gaps: dict, strengths: dict, recommendations: dict, overall_score: float = None) -> dict:
    score_display = overall_score if overall_score is not None else mastery.get("subjectMastery", 0)
    prompt = f"""You are a school advisor writing a concise professional summary for a student's teacher based ONLY on the following structured facts.
Do NOT read or interpret raw student transcripts here. Simply summarize the facts into a professional overview.

Student Name: {student_name}
Overall Score: {score_display}/100
Strengths: {json.dumps(strengths, indent=2)}
Learning Gaps: {json.dumps(gaps, indent=2)}
Recommendations: {json.dumps(recommendations, indent=2)}

Guidelines:
- If the score is mentioned, use {score_display}/100.
- Keep tone professional and academic.

Respond ONLY with a JSON object:
{{
  "summary": "<2-3 sentence overview text for the teacher dashboard>"
}}"""
    system_instruction = "Return teacher summary in raw JSON only."
    fallback_data = {"summary": f"Completed chapter review session with an overall score of {score_display}/100. Shows good understanding of core concepts."}
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_parent_summary(student_name: str, mastery: dict, gaps: dict, strengths: dict, overall_score: float = None) -> dict:
    score_display = overall_score if overall_score is not None else mastery.get("subjectMastery", 0)
    prompt = f"""Write a warm, encouraging, parent-friendly letter about {student_name}'s performance.
Use simple, positive, encouraging wording and reference ONLY these structured findings:

Overall Score: {score_display}/100
Academic Strengths: {json.dumps(strengths, indent=2)}
Development Areas: {json.dumps(gaps, indent=2)}

Guidelines:
- If the score is mentioned, reference {score_display}/100.
- Focus on what the student learned and did well. Do NOT include behavioral, sentiment, or emotional analysis.
- Under 3 sentences.

Respond ONLY with a JSON object:
{{
  "parent_summary": "<warm encouraging letter text, under 3 sentences>"
}}"""
    system_instruction = "Return parent summary in raw JSON only."
    fallback_data = {"parent_summary": f"Dear Parent, {student_name} did a great job on their assessment today with a score of {score_display}/100! We are proud of their effort and look forward to supporting their ongoing learning."}
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }
