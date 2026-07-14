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
    prompt = f"""Identify the student's cognitive and concept strengths from correct answers:
{json.dumps(evaluated_answers, indent=2)}

Respond ONLY with a JSON object:
{{
  "strengths": [
     "<strength description, max 10 words>"
  ]
}}"""
    system_instruction = "Return strengths in raw JSON only."
    fallback_data = {"strengths": ["Demonstrated willingness to answer questions", "Good communication skill"]}
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

def step_teacher_summary(student_name: str, mastery: dict, gaps: dict, strengths: dict, recommendations: dict) -> dict:
    prompt = f"""You are a school advisor writing a professional summary for a student's teacher based ONLY on the following structured facts.
Do NOT read or interpret raw student transcripts here. Simply summarize the facts into a professional overview.

Student Name: {student_name}
Subject Mastery: {mastery.get("subjectMastery")}/100
Learning Gaps: {json.dumps(gaps, indent=2)}
Strengths: {json.dumps(strengths, indent=2)}
Recommendations: {json.dumps(recommendations, indent=2)}

Respond ONLY with a JSON object:
{{
  "summary": "<2-3 sentence overview text for the teacher dashboard>"
}}"""
    system_instruction = "Return teacher summary in raw JSON only."
    fallback_data = {"summary": "Completed chapter review session. Shows good progress in basic concepts with some room for practice in revision topics."}
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }

def step_parent_summary(student_name: str, mastery: dict, gaps: dict, strengths: dict) -> dict:
    prompt = f"""Write a warm, encouraging, parent-friendly letter about {student_name}'s performance.
Use simple, positive wording and reference ONLY these structured findings:

Mastery Score: {mastery.get("subjectMastery")}/100
Strengths: {json.dumps(strengths, indent=2)}
Development Areas: {json.dumps(gaps, indent=2)}

Respond ONLY with a JSON object:
{{
  "parent_summary": "<warm letter text, under 3 sentences>"
}}"""
    system_instruction = "Return parent summary in raw JSON only."
    fallback_data = {"parent_summary": f"Dear Parent, {student_name} did a great job reviewing their lessons today! They showed great strengths and we are excited to keep supporting their learning."}
    return {
        "prompt": prompt,
        "system_instruction": system_instruction,
        "fallback_data": fallback_data
    }
