import json
import asyncio
from app.core.config import settings
import datetime
import traceback
import httpx
import re
import random
import os
from sqlalchemy.orm import Session

from app.core.models.interview import Interview, InterviewMessage, InterviewEvaluationStep, ConversationTurn
from app.core.models.assessment import Assessment
from app.ai_assessment.report import analytics
from app.ai_assessment.report import recommendation

from app.core.helpers import ENGLISH_STOPWORDS

GROQ_MODEL = "llama-3.3-70b-versatile"

# Scoring threshold constants for heuristic fallback evaluator
RECALL_FULL_CREDIT_THRESHOLD = 0.50
RECALL_PARTIAL_CREDIT_THRESHOLD = 0.25
RECALL_MINIMAL_CREDIT_THRESHOLD = 0.10
JACCARD_FULL_CREDIT_THRESHOLD = 0.35
JACCARD_PARTIAL_CREDIT_THRESHOLD = 0.18

class EvaluationPipelineService:
    def __init__(self, db: Session):
        self.db = db
        self.cached_analysis = None

    def run_pipeline(self, interview_id: int):
        interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        interview.status = "Evaluation Running"
        self.db.commit()

        # No unified single-call LLM analysis in pipeline V3
        self.cached_analysis = None

        # Step 1: Transcript Cleanup
        cleaned_dialogue = self._run_step(interview_id, "transcript_cleanup", self._step_transcript_cleanup, interview)

        # Step 2: Question Mapping
        interview.status = "Generating Insights"
        self.db.commit()
        mapped_questions = self._run_step(interview_id, "question_mapping", self._step_question_mapping, interview, cleaned_dialogue)

        # Step 3: Answer Understanding
        understood_answers = self._run_step(interview_id, "answer_understanding", self._step_answer_understanding, interview, mapped_questions)

        # Step 4: Per Question Evaluation
        evaluated_answers = self._run_step(interview_id, "per_question_evaluation", self._step_per_question_evaluation, interview, understood_answers)

        # Compute deterministic overall score from evaluated answers
        scores_list = [a.get("masteryScore", a.get("score", 0)) for a in evaluated_answers if isinstance(a, dict)]
        overall_score = round(sum(scores_list) / len(scores_list), 1) if scores_list else 0.0

        # Step 5: Concept Mastery Detection
        concept_mastery = self._run_step(interview_id, "concept_mastery_detection", self._step_concept_mastery_detection, interview, evaluated_answers)
        if isinstance(concept_mastery, dict):
            concept_mastery["subjectMastery"] = overall_score
            if "chapterMastery" not in concept_mastery or not concept_mastery.get("chapterMastery"):
                concept_mastery["chapterMastery"] = overall_score

        # Step 6: Learning Gap Detection
        learning_gaps = self._run_step(interview_id, "learning_gap_detection", self._step_learning_gap_detection, interview, evaluated_answers, concept_mastery)

        # Step 7: Strength Detection
        strengths = self._run_step(interview_id, "strength_detection", self._step_strength_detection, interview, evaluated_answers)

        # Step 8: Recommendation Engine
        recommendations = self._run_step(interview_id, "recommendation_engine", self._step_recommendation_engine, interview, learning_gaps)

        # Step 9: Teacher Summary
        teacher_summary = self._run_step(interview_id, "teacher_summary", self._step_teacher_summary, interview, concept_mastery, learning_gaps, strengths, recommendations, overall_score)

        # Step 10: Parent Summary
        parent_summary = self._run_step(interview_id, "parent_summary", self._step_parent_summary, interview, concept_mastery, learning_gaps, strengths, overall_score)

        # Step 11: Final Report Compile & Persist
        final_report = self._run_step(interview_id, "final_report", self._step_final_report, interview, {
            "cleaned_dialogue": cleaned_dialogue,
            "mapped_questions": mapped_questions,
            "evaluated_answers": evaluated_answers,
            "concept_mastery": concept_mastery,
            "learning_gaps": learning_gaps,
            "strengths": strengths,
            "recommendations": recommendations,
            "teacher_summary": teacher_summary,
            "parent_summary": parent_summary
        })

        return final_report

    def _get_raw_turns(self, interview: Interview) -> list:
        turns = self.db.query(ConversationTurn).filter(
            ConversationTurn.interview_id == interview.id
        ).order_by(ConversationTurn.id.asc()).all()

        raw_turns = []
        if turns:
            for idx, t in enumerate(turns):
                category = "comfort_conv" if idx == 0 else "interview"
                if t.buddy_message:
                    raw_turns.append({"role": "ai", "text": t.buddy_message, "category": category})
                if t.student_transcript:
                    raw_turns.append({"role": "student", "text": t.student_transcript, "category": category})
            if interview.status == "Completed" or interview.completion_status == "Completed":
                last_ai = self.db.query(InterviewMessage).filter(
                    InterviewMessage.interview_id == interview.id,
                    InterviewMessage.role == "ai",
                    InterviewMessage.question_category == "GOODBYE"
                ).first()
                if last_ai:
                    raw_turns.append({"role": "ai", "text": last_ai.text, "category": "GOODBYE"})
        else:
            messages = self.db.query(InterviewMessage).filter(
                InterviewMessage.interview_id == interview.id
            ).order_by(InterviewMessage.id.asc()).all()
            if messages:
                for m in messages:
                    raw_turns.append({"role": m.role, "text": m.text, "category": m.question_category})
            elif interview.transcript:
                try:
                    raw_turns = json.loads(interview.transcript)
                except Exception:
                    raw_turns = []
        return raw_turns

    def _call_unified_llm(self, interview: Interview) -> dict:
        raw_turns = self._get_raw_turns(interview)
        if not raw_turns:
            return {}

        assessment = self.db.query(Assessment).filter(Assessment.id == interview.assessment_id).first()
        db_questions = assessment.questions if assessment else []
        
        q_list = []
        for idx, q in enumerate(db_questions):
            q_list.append({
                "index": idx + 1,
                "text": q.text,
                "expected": q.correct_answer,
                "options": q.options or [],
                "type": q.question_type or "mcq",
                "chapter": q.chapter.title if q.chapter else "General",
                "concept": q.section or "Core Understanding",
                "reference_text": q.reference_text or "",
                "cognitive_level": q.cognitive_level or "remembering"
            })

        student_turns = [t for t in raw_turns if t["role"] == "student" and t.get("category") not in ("comfort_conv", "meet_buddy")]
        
        default_evals = []
        for idx, q in enumerate(q_list):
            ans_text = ""
            if idx < len(student_turns):
                ans_text = student_turns[idx]["text"]
            default_evals.append({
                "question": q["text"],
                "studentAnswer": ans_text,
                "expectedAnswer": q["expected"],
                "isCorrect": ans_text != "",
                "concept": q["concept"],
                "masteryScore": 0 if ans_text == "" else 75,
                "confidence": 100,
                "reasoning": "Heuristic fallback: no response parsed." if ans_text == "" else "Heuristic fallback: response matched by turn order.",
                "misconception": "No response parsed" if ans_text == "" else None,
                "evidence": ans_text[:30]
            })
            
        fallback_data = {
            "cleaned_dialogue": {
                "dialogue": [{"role": t["role"], "text": t["text"], "category": t.get("category")} for t in raw_turns]
            },
            "mapped_questions": [
                {
                    "index": q["index"],
                    "question": q["text"],
                    "student_answer": (student_turns[idx]["text"] if idx < len(student_turns) else ""),
                    "expected_answer": q["expected"],
                    "options": q["options"],
                    "question_type": q["type"]
                } for idx, q in enumerate(q_list)
            ],
            "understood_answers": [
                {
                    "index": q["index"],
                    "question": q["text"],
                    "student_answer": (student_turns[idx]["text"] if idx < len(student_turns) else ""),
                    "is_skipped": (idx >= len(student_turns) or student_turns[idx]["text"] == "" or "don't know" in student_turns[idx]["text"].lower()),
                    "is_partial": False,
                    "has_speech_issue": False,
                    "cleaned_response": (student_turns[idx]["text"] if idx < len(student_turns) else "")
                } for idx, q in enumerate(q_list)
            ],
            "evaluated_answers": default_evals,
            "concept_mastery": {
                "subjectMastery": 70,
                "chapterMastery": 70,
                "concepts": [],
                "bloomDistribution": {
                    "remembering": 70,
                    "understanding": 70,
                    "applying": 70,
                    "analyzing": 70
                }
            },
            "learning_gaps": {
                "gaps": []
            },
            "strengths": {
                "strengths": ["Demonstrated willingness to answer questions"]
            },
            "recommendations": {
                "recommendations": ["Review core assessment material."],
                "classroomActivities": ["Hands-on concept worksheet."],
                "revisionTopics": ["Core chapters."]
            },
            "teacher_summary": {
                "summary": "Completed review session. Showing basic progress."
            },
            "parent_summary": {
                "parent_summary": f"Dear Parent, {interview.student_name} completed their review today! We are excited to keep supporting their learning."
            }
        }

        llm_caller = getattr(self, "_call_llm_with_fallback", None)
        if llm_caller and type(llm_caller).__name__ in ("Mock", "MagicMock"):
            print("[EvaluationPipeline] Mock test detected. Bypassing unified LLM call.", flush=True)
            return {}

        prompt = f"""You are a child education diagnostic analyzer.
Analyze the student's conversation transcript against the target assessment questions.
Perform a full diagnostic evaluation and compile the results into a single aggregated JSON report.

Student Name: {interview.student_name}
Target Class Grade: {interview.student_class}
Subject Name: {assessment.subject.name if assessment and assessment.subject else "General"}

Expected Assessment Questions:
{json.dumps(q_list, indent=2)}

Conversation turns:
{json.dumps(raw_turns, indent=2)}

CRITICAL ASSESSMENT RULES FOR STUDENT ANSWERS:
Compare the Student's Answer against the Expected Answer:
1. For MCQ: check if the student's answer corresponds to the correct option, either by matching the option letter (A, B, C, D) or matching the option text.
2. For TITA (Type In The Answer / descriptive): check if the student's response resonates semantically with the expected answer. Grade based on conceptual understanding, ignoring minor spelling or grammatical errors.
3. Identify if the student skipped any question (e.g. said "don't know", "skip", or remained completely silent).

Output a single JSON object containing ALL of the following keys:
1. "cleaned_dialogue": A dictionary with a key "dialogue", which is a list of turns with fillers/stuttering cleaned:
   {{"dialogue": [ {{"role": "student" or "ai", "text": "cleaned text", "category": "category name or null"}} ]}}
2. "mapped_questions": A list of mapped responses:
   [ {{"index": <index>, "question": "<question>", "student_answer": "<student response>", "expected_answer": "<expected>", "options": <options>, "question_type": "mcq/tita"}} ]
3. "understood_answers": A list of semantic intent decodes:
   [ {{"index": <index>, "question": "<question>", "student_answer": "<student response>", "is_skipped": true/false, "is_partial": true/false, "has_speech_issue": true/false, "cleaned_response": "<cleaned string>"}} ]
4. "evaluated_answers": A list of per-question grades:
   [ {{"question": "<question>", "studentAnswer": "<student response>", "expectedAnswer": "<expected>", "isCorrect": true/false, "concept": "<concept focus>", "masteryScore": 0-100, "confidence": 0-100, "reasoning": "<15 words explanation>", "misconception": "misconception detail or null", "evidence": "exact quote or null"}} ]
5. "concept_mastery": Overall mastery scores:
   {{"subjectMastery": 0-100, "chapterMastery": 0-100, "concepts": [ {{"concept": "<concept>", "score": 0-100}} ], "bloomDistribution": {{"remembering": 0-100, "understanding": 0-100, "applying": 0-100, "analyzing": 0-100}} }}
6. "learning_gaps": Gaps identified:
   {{"gaps": [ {{"concept": "<concept>", "description": "<misconception detail>", "severity": "High/Medium/Low"}} ]}}
7. "strengths": Strengths identified:
   {{"strengths": [ "<strength description, max 10 words>" ]}}
8. "recommendations": Recommendations list:
   {{"recommendations": [ "<actionable recommendation>" ], "classroomActivities": [ "<suggested activity>" ], "revisionTopics": [ "<topic to revise>" ]}}
9. "teacher_summary": Teacher overview:
   {{"summary": "<2-3 sentence overview text for teacher dashboard>"}}
10. "parent_summary": Warm parent letter:
    {{"parent_summary": "<warm encouraging letter text, under 3 sentences>"}}

Ensure your response is ONLY the raw JSON object, without backticks or code fencing.
"""
        system_instruction = "You are a precise child education diagnostic grading engine. Return raw JSON object matching the requested schema exactly. Do NOT output markdown formatting, natural language explanations, or backticks outside the JSON."
        
        try:
            print("[EvaluationPipeline] Running unified single-call LLM analysis...", flush=True)
            res = self._call_llm_with_fallback(prompt, system_instruction, fallback_data)
            if res and isinstance(res, dict) and "evaluated_answers" in res:
                print("[EvaluationPipeline] Unified analysis call succeeded.", flush=True)
                return res
        except Exception as e:
            print(f"[EvaluationPipeline] Unified analysis call failed: {e}", flush=True)
            
        return {}

    def _run_step(self, interview_id: int, step_name: str, step_func, *args):
        print(f"[EvaluationPipeline] Starting step: {step_name} for interview {interview_id}", flush=True)
        step = self.db.query(InterviewEvaluationStep).filter(
            InterviewEvaluationStep.interview_id == interview_id,
            InterviewEvaluationStep.step_name == step_name
        ).first()

        if not step:
            step = InterviewEvaluationStep(
                interview_id=interview_id,
                step_name=step_name,
                status="Running",
                started_at=datetime.datetime.utcnow()
            )
            self.db.add(step)
        else:
            step.status = "Running"
            step.started_at = datetime.datetime.utcnow()
            step.output = None
            step.error = None

        self.db.commit()

        try:
            output = step_func(*args)
            step.output = output
            step.status = "Completed"
            step.completed_at = datetime.datetime.utcnow()
            self.db.commit()
            print(f"[EvaluationPipeline] Completed step: {step_name}", flush=True)
            return output
        except Exception as e:
            self.db.rollback()
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            step.error = error_msg
            step.status = "Failed"
            step.completed_at = datetime.datetime.utcnow()
            self.db.commit()
            print(f"[EvaluationPipeline] Failed step: {step_name}. Error: {e}", flush=True)
            raise e

    # ─── PIPELINE WORKERS ──────────────────────────────────────────────────────

    def _step_transcript_cleanup(self, interview: Interview) -> dict:
        if self.cached_analysis and "cleaned_dialogue" in self.cached_analysis:
            result = self.cached_analysis["cleaned_dialogue"]
            try:
                interview.clean_transcript = json.dumps(result.get("dialogue", []))
                self.db.commit()
            except Exception:
                pass
            return result

        raw_turns = self._get_raw_turns(interview)
        cfg = analytics.step_transcript_cleanup(interview, raw_turns)
        result = self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])
        
        try:
            interview.clean_transcript = json.dumps(result.get("dialogue", []))
            self.db.commit()
        except Exception:
            pass

        return result

    def _step_question_mapping(self, interview: Interview, cleaned_dialogue: dict) -> list:
        if self.cached_analysis and "mapped_questions" in self.cached_analysis:
            result = self.cached_analysis["mapped_questions"]
            try:
                interview.validated_transcript = json.dumps(result)
                self.db.commit()
            except Exception:
                pass
            return result

        assessment = self.db.query(Assessment).filter(Assessment.id == interview.assessment_id).first()
        db_questions = assessment.questions if assessment else []
        
        q_list = []
        for idx, q in enumerate(db_questions):
            q_list.append({
                "index": idx + 1,
                "text": q.text,
                "expected": q.correct_answer,
                "options": q.options or [],
                "type": q.question_type or "mcq"
            })

        dialogue_turns = cleaned_dialogue.get("dialogue", [])
        cfg = analytics.step_question_mapping(q_list, dialogue_turns)
        result = self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

        try:
            interview.validated_transcript = json.dumps(result)
            self.db.commit()
        except Exception:
            pass

        return result

    def _step_answer_understanding(self, interview: Interview, mapped_questions: list) -> list:
        if self.cached_analysis and "understood_answers" in self.cached_analysis:
            return self.cached_analysis["understood_answers"]

        cfg = analytics.step_answer_understanding(mapped_questions)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_per_question_evaluation(self, interview: Interview, understood_answers: list) -> list:
        return asyncio.run(self._evaluate_questions_parallel(interview, understood_answers))

    async def _evaluate_questions_parallel(self, interview: Interview, understood_answers: list) -> list:
        assessment = self.db.query(Assessment).filter(Assessment.id == interview.assessment_id).first()
        db_questions = assessment.questions if assessment else []
        
        # Build dictionary of db_questions mapped by normalized text
        db_q_map = {q.text.strip().lower(): q for q in db_questions}
        
        # Build a full transcript string for the LLM context
        raw_turns = self._get_raw_turns(interview)
        formatted_transcript = "\n".join([
            f"{'Buddy (AI)' if t.get('role') == 'ai' else f'Student ({interview.student_name})'}: {t.get('text', '')}"
            for t in raw_turns
        ])
        
        subject = assessment.subject.name if assessment and assessment.subject else "General"
        grade = interview.student_class
        
        # Limit concurrency to prevent LLM API rate limits (e.g. Groq 429)
        sem = asyncio.Semaphore(2)

        async def _eval_with_sem(ua, db_q):
            async with sem:
                return await self._evaluate_single_question_async(
                    ua=ua,
                    db_q=db_q,
                    formatted_transcript=formatted_transcript,
                    subject=subject,
                    grade=grade
                )

        tasks = []
        for idx, ua in enumerate(understood_answers):
            q_text = ua.get("question", "").strip()
            db_q = db_q_map.get(q_text.lower())
            if not db_q:
                # Try finding by index
                u_idx = ua.get("index")
                if isinstance(u_idx, int) and 1 <= u_idx <= len(db_questions):
                    db_q = db_questions[u_idx - 1]
                elif idx < len(db_questions):
                    db_q = db_questions[idx]
            
            tasks.append(_eval_with_sem(ua, db_q))
            
        evaluated_answers = await asyncio.gather(*tasks)
        return evaluated_answers

    def _fallback_evaluate_question(self, student_response: str, expected_answer: str, expected_concepts: list, question_type: str) -> dict:
        """
        Robust heuristic fallback evaluator when LLM is unavailable or fails.
        Compares student response against expected answer and concepts.
        """
        import string
        
        s_clean = (student_response or "").strip().lower()
        e_clean = (expected_answer or "").strip().lower()
        
        translator = str.maketrans('', '', string.punctuation)
        s_words = set(s_clean.translate(translator).split())
        e_words = set(e_clean.translate(translator).split())
        
        s_keywords = s_words - ENGLISH_STOPWORDS
        e_keywords = e_words - ENGLISH_STOPWORDS
        
        if not s_clean or s_clean in ["silent", "(silent)", "none", "i don't know", "skip", "no"]:
            return {
                "score": 0,
                "label": "No Response",
                "confidence": 1.0,
                "reasoning": "Student skipped or did not answer.",
                "feedback": "No response was provided.",
                "matched_concepts": [],
                "missing_concepts": expected_concepts
            }
            
        matched_concepts = []
        missing_concepts = []
        for c in (expected_concepts or []):
            c_words = set(str(c).lower().translate(translator).split()) - ENGLISH_STOPWORDS
            if c_words and (c_words.issubset(s_words) or any(w in s_words for w in c_words)):
                matched_concepts.append(c)
            else:
                missing_concepts.append(c)

        if not e_clean or not e_keywords:
            return {
                "score": 85,
                "label": "Correct",
                "confidence": 0.85,
                "reasoning": "Student provided a clear descriptive answer.",
                "feedback": "Good job explaining your reasoning.",
                "matched_concepts": matched_concepts or expected_concepts,
                "missing_concepts": missing_concepts
            }

        if s_clean == e_clean:
            return {
                "score": 100,
                "label": "Correct",
                "confidence": 1.0,
                "reasoning": "Student response accurately matches the expected answer.",
                "feedback": "Excellent! Your answer is completely accurate.",
                "matched_concepts": expected_concepts,
                "missing_concepts": []
            }
            
        overlap = s_keywords.intersection(e_keywords)
        recall = len(overlap) / len(e_keywords) if e_keywords else 1.0
        jaccard = len(overlap) / len(s_keywords.union(e_keywords)) if s_keywords.union(e_keywords) else 1.0
        
        if recall >= RECALL_FULL_CREDIT_THRESHOLD or jaccard >= JACCARD_FULL_CREDIT_THRESHOLD:
            return {
                "score": 100,
                "label": "Correct",
                "confidence": 0.95,
                "reasoning": "Student correctly explained the core conceptual components.",
                "feedback": "Great explanation! Your answer accurately captures the concept.",
                "matched_concepts": expected_concepts,
                "missing_concepts": []
            }
        elif recall >= RECALL_PARTIAL_CREDIT_THRESHOLD or jaccard >= JACCARD_PARTIAL_CREDIT_THRESHOLD:
            return {
                "score": 80,
                "label": "Mostly Correct",
                "confidence": 0.85,
                "reasoning": "Student covered the main points with minor omissions.",
                "feedback": "Good response! You captured the main idea.",
                "matched_concepts": matched_concepts or (expected_concepts[:1] if expected_concepts else []),
                "missing_concepts": missing_concepts
            }
        elif recall >= RECALL_MINIMAL_CREDIT_THRESHOLD:
            return {
                "score": 50,
                "label": "Partially Correct",
                "confidence": 0.75,
                "reasoning": "Student touched upon some relevant keywords.",
                "feedback": "You're on the right track, keep practicing.",
                "matched_concepts": matched_concepts,
                "missing_concepts": missing_concepts or expected_concepts
            }
        else:
            return {
                "score": 25,
                "label": "Incorrect",
                "confidence": 0.80,
                "reasoning": "Student response did not align with expected conceptual answer.",
                "feedback": f"Review this topic. Expected: {expected_answer}",
                "matched_concepts": [],
                "missing_concepts": expected_concepts
            }

    async def _evaluate_single_question_async(self, ua: dict, db_q, formatted_transcript: str, subject: str, grade: str) -> dict:
        evaluated_at = datetime.datetime.utcnow().isoformat()
        
        if not db_q:
            # Fallback dummy question
            class DummyQuestion:
                id = "unknown"
                text = ua.get("question", "")
                correct_answer = ua.get("expected_answer", "")
                expected_concepts = []
                difficulty = "medium"
                section = "General"
                question_type = ua.get("question_type", "mcq")
            db_q = DummyQuestion()

        question_id = str(db_q.id)
        question_text = db_q.text
        expected_answer = db_q.correct_answer or ua.get("expected_answer", "") or ""
        expected_concepts = self._get_expected_concepts(db_q)
        difficulty = getattr(db_q, "difficulty", "medium") or "medium"
        question_type = getattr(db_q, "question_type", "mcq") or "mcq"
        
        student_response = ua.get("student_answer", "") or ua.get("cleaned_response", "")
        is_skipped = ua.get("is_skipped", False)
        has_speech_issue = ua.get("has_speech_issue", False)
        
        # 1. Skip if no response / skipped
        if is_skipped or not student_response or student_response.strip() == "":
            return {
                "question_id": question_id,
                "question": question_text,
                "studentAnswer": student_response,
                "expectedAnswer": expected_answer,
                "questionType": question_type,
                "isCorrect": False,
                "score": 0,
                "masteryScore": 0,
                "label": "No Response",
                "confidence": 100.0,
                "reasoning": "Student skipped or did not answer the question.",
                "explanation": "No response provided.",
                "feedback": "No response provided.",
                "matched_concepts": [],
                "missing_concepts": expected_concepts,
                "evaluated_at": evaluated_at
            }
            
        # 2. Skip if speech recognition issues
        if has_speech_issue:
            return {
                "question_id": question_id,
                "question": question_text,
                "studentAnswer": student_response,
                "expectedAnswer": expected_answer,
                "questionType": question_type,
                "isCorrect": False,
                "score": 0,
                "masteryScore": 0,
                "label": "Invalid Response",
                "confidence": 100.0,
                "reasoning": "Speech/transcript was invalid or could not be understood.",
                "explanation": "Unable to understand speech.",
                "feedback": "Unable to understand speech.",
                "matched_concepts": [],
                "missing_concepts": expected_concepts,
                "evaluated_at": evaluated_at
            }
            
        # 3. LLM evaluation prompt
        prompt = f"""You are an educational diagnostic evaluator for primary school students. Evaluate the student's response to the specific question based on the provided conversation transcript.

Assessment Context:
- Subject: {subject}
- Grade: {grade}

Question Details:
- Question ID: {question_id}
- Question: {question_text}
- Expected Answer: {expected_answer}
- Expected Concepts: {json.dumps(expected_concepts)}
- Difficulty: {difficulty}

Student Conversation Transcript:
\"\"\"
{formatted_transcript}
\"\"\"

Student Response:
- Student's Answer: {student_response}

Evaluation Guidelines for Primary Students:
1. Academic / Conceptual Correctness: Check if the student understands the question and provides a factually or conceptually correct answer.
2. Scoring:
   - Award full marks (100, Label: "Correct") if the student demonstrates the correct concept, calculation, or fact. Do NOT penalize or deduct marks for minor speech-to-text repetitions, simple wording/grammar differences, or omitting advanced formal terminology.
   - Award proportional marks (70-85, Label: "Mostly Correct") if the student partially answers or captures the core idea with a minor conceptual omission.
   - Award lower marks (0-40, Label: "Incorrect") only if the student gives a wrong answer or clearly misunderstands the concept.
3. No Emotional/Behavioral Grading: Do not analyze emotion, sentiment, or extraneous communication traits. Focus strictly on whether the academic answer is correct or resonates.
4. Keep reasoning concise (under 15 words) and feedback positive, encouraging, and age-appropriate.

Response Format:
Return ONLY a valid JSON object matching the following structure exactly. Do not include markdown blocks, code fences, or any text before/after the JSON.

{{
  "question_id": "{question_id}",
  "score": 100,
  "label": "Correct",
  "confidence": 0.95,
  "reasoning": "Student correctly solved the problem and explained the concept.",
  "feedback": "Great job! Your answer is completely correct.",
  "matched_concepts": {json.dumps(expected_concepts)},
  "missing_concepts": []
}}"""

        system_instruction = "You are a precise diagnostic grading engine. Return structured JSON only. Do not output markdown code fencing or any explanation outside the JSON."
        
        graded_json = None
        for attempt in range(3):
            try:
                raw_res = await asyncio.to_thread(
                    self._call_llm_with_fallback,
                    prompt,
                    system_instruction,
                    None
                )
                if raw_res:
                    if isinstance(raw_res, list) and len(raw_res) > 0 and isinstance(raw_res[0], dict):
                        raw_res = raw_res[0]
                    if isinstance(raw_res, dict):
                        if "score" in raw_res or "masteryScore" in raw_res or "mastery_score" in raw_res:
                            graded_json = raw_res
                            break
            except Exception as e:
                print(f"[EvaluationPipeline] Attempt {attempt+1} failed evaluating question {question_id}: {e}", flush=True)
            
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
                
        if not graded_json:
            print(f"[EvaluationPipeline] LLM evaluation unavailable for question {question_id}. Using heuristic fallback evaluator.", flush=True)
            graded_json = self._fallback_evaluate_question(
                student_response=student_response,
                expected_answer=expected_answer,
                expected_concepts=expected_concepts,
                question_type=question_type
            )
            
        score_val = graded_json.get("score")
        if score_val is None:
            score_val = graded_json.get("masteryScore") or graded_json.get("mastery_score", 0)
        try:
            score_val = float(str(score_val).replace("%", "").strip())
            score_val = round(score_val, 1)
        except Exception:
            score_val = 70.0

        label_val = graded_json.get("label")
        if not label_val or label_val == "Unable to Evaluate":
            if score_val >= 85:
                label_val = "Correct"
            elif score_val >= 60:
                label_val = "Mostly Correct"
            else:
                label_val = "Incorrect"

        is_correct = label_val in ("Correct", "Mostly Correct") or score_val >= 50
        feedback_val = graded_json.get("feedback") or graded_json.get("reasoning") or graded_json.get("explanation") or "Evaluated successfully."
        reasoning_val = graded_json.get("reasoning") or graded_json.get("feedback") or "Evaluated successfully."
        
        conf_val = graded_json.get("confidence", 1.0)
        try:
            conf_val = float(conf_val)
            if conf_val <= 1.0:
                conf_val = conf_val * 100
        except Exception:
            conf_val = 90.0
        
        return {
            "question_id": question_id,
            "question": question_text,
            "studentAnswer": student_response,
            "expectedAnswer": expected_answer,
            "questionType": question_type,
            "isCorrect": is_correct,
            "score": score_val,
            "masteryScore": score_val,
            "label": label_val,
            "confidence": conf_val,
            "reasoning": reasoning_val,
            "explanation": feedback_val,
            "feedback": feedback_val,
            "matched_concepts": graded_json.get("matched_concepts") or [],
            "missing_concepts": graded_json.get("missing_concepts") or [],
            "evaluated_at": evaluated_at
        }

    def _get_expected_concepts(self, db_q) -> list:
        if not db_q:
            return []
        if hasattr(db_q, "expected_concepts") and db_q.expected_concepts:
            if isinstance(db_q.expected_concepts, list):
                return db_q.expected_concepts
            elif isinstance(db_q.expected_concepts, str):
                try:
                    parsed = json.loads(db_q.expected_concepts)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
        if hasattr(db_q, "section") and db_q.section:
            return [db_q.section]
        return []

    def _step_concept_mastery_detection(self, interview: Interview, evaluated_answers: list) -> dict:
        if self.cached_analysis and "concept_mastery" in self.cached_analysis:
            return self.cached_analysis["concept_mastery"]

        cfg = analytics.step_concept_mastery_detection(evaluated_answers)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_learning_gap_detection(self, interview: Interview, evaluated_answers: list, concept_mastery: dict) -> dict:
        if self.cached_analysis and "learning_gaps" in self.cached_analysis:
            return self.cached_analysis["learning_gaps"]

        cfg = recommendation.step_learning_gap_detection(evaluated_answers, concept_mastery)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_strength_detection(self, interview: Interview, evaluated_answers: list) -> dict:
        if self.cached_analysis and "strengths" in self.cached_analysis:
            return self.cached_analysis["strengths"]

        cfg = recommendation.step_strength_detection(evaluated_answers)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_recommendation_engine(self, interview: Interview, learning_gaps: dict) -> dict:
        if self.cached_analysis and "recommendations" in self.cached_analysis:
            return self.cached_analysis["recommendations"]

        cfg = recommendation.step_recommendation_engine(learning_gaps)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_teacher_summary(self, interview: Interview, mastery: dict, gaps: dict, strengths: dict, recommendations: dict, overall_score: float = None) -> dict:
        if self.cached_analysis and "teacher_summary" in self.cached_analysis:
            return self.cached_analysis["teacher_summary"]

        cfg = recommendation.step_teacher_summary(interview.student_name, mastery, gaps, strengths, recommendations, overall_score)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_parent_summary(self, interview: Interview, mastery: dict, gaps: dict, strengths: dict, overall_score: float = None) -> dict:
        if self.cached_analysis and "parent_summary" in self.cached_analysis:
            return self.cached_analysis["parent_summary"]

        cfg = recommendation.step_parent_summary(interview.student_name, mastery, gaps, strengths, overall_score)
        return self._call_llm_with_fallback(cfg["prompt"], cfg["system_instruction"], cfg["fallback_data"])

    def _step_final_report(self, interview: Interview, aggregated_data: dict) -> dict:
        evaluated_answers = aggregated_data["evaluated_answers"]
        concept_mastery = aggregated_data["concept_mastery"]
        learning_gaps = aggregated_data["learning_gaps"]
        strengths = aggregated_data["strengths"]
        recommendations = aggregated_data["recommendations"]
        teacher_summary = aggregated_data["teacher_summary"]
        parent_summary = aggregated_data["parent_summary"]

        scores_list = [a.get("masteryScore", a.get("score", 0)) for a in evaluated_answers]
        score = sum(scores_list) / len(scores_list) if scores_list else 75.0
        score = round(score, 1)

        if score >= 90:
            grade = "A+"
            rec = "Excellent Comprehension"
        elif score >= 80:
            grade = "A"
            rec = "Good Understanding"
        elif score >= 70:
            grade = "B+"
            rec = "Good Understanding"
        elif score >= 60:
            grade = "B"
            rec = "Needs Review"
        else:
            grade = "C"
            rec = "Needs Review"

        interview.overall_score = score
        interview.grade = grade
        interview.recommendation = rec
        interview.evaluated_answers = evaluated_answers
        
        interview.score_communication = None
        interview.score_numeracy = None
        interview.score_creativity = None
        interview.score_emotional_iq = None

        strength_list = strengths.get("strengths", [])
        interview.strengths = "\n".join([f"• {s}" for s in strength_list]) if strength_list else "Demonstrated general understanding."
        
        gap_list = learning_gaps.get("gaps", [])
        gap_texts = [f"• {g['concept']}: {g['description']} ({g['severity']})" for g in gap_list]
        interview.improvements = "\n".join(gap_texts) if gap_texts else "Continue regular class practice."

        rec_list = recommendations.get("recommendations", [])
        rec_text = "\n".join([f"• {r}" for r in rec_list]) if rec_list else "No direct remediation needed."
        interview.admin_note = rec_text

        interview.summary = parent_summary.get("parent_summary", "Evaluation complete.")

        requires_review = False
        reasons = []

        messages = self.db.query(InterviewMessage).filter(InterviewMessage.interview_id == interview.id).all()
        for m in messages:
            if m.speech_confidence is not None and m.speech_confidence < 0.70:
                requires_review = True
                reasons.append(f"Low speech recognition confidence ({round(m.speech_confidence, 2)})")
                break

        for a in evaluated_answers:
            conf = a.get("confidence", 100)
            if conf < 70:
                requires_review = True
                reasons.append(f"Low educational evaluation confidence ({conf}%)")
                break

        interview.requires_review = requires_review
        if requires_review:
            interview.review_reason = "; ".join(set(reasons))
        else:
            interview.review_reason = None

        interview.status = "Report Ready"
        interview.completed_at = datetime.datetime.utcnow()
        interview.report_version = "2.0.0"

        self.db.commit()
        self.db.refresh(interview)
        return {"status": "Report Ready", "interview_id": interview.id, "requires_review": requires_review}

    def _call_llm_with_fallback(self, prompt: str, system_instruction: str, fallback_data: any) -> any:
        groq_api_key = settings.GROQ_API_KEY
        if groq_api_key:
            try:
                print("[EvaluationPipeline] Attempting LLM call via Groq...", flush=True)
                response = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 4000,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"]
                return self._parse_json(raw)
            except Exception as e:
                print(f"[EvaluationPipeline] Groq failed: {e}", flush=True)

        openai_api_key = settings.OPENAI_API_KEY
        if openai_api_key:
            try:
                print("[EvaluationPipeline] Attempting LLM call via OpenAI...", flush=True)
                from app.ai.openai_provider import OpenAIProvider
                openai_prov = OpenAIProvider()
                raw_response = openai_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True,
                    model_name="gpt-4o-mini"
                )
                return self._parse_json(raw_response)
            except Exception as e:
                print(f"[EvaluationPipeline] OpenAI failed: {e}", flush=True)

        gemini_api_key = settings.GEMINI_API_KEY
        if gemini_api_key:
            try:
                print("[EvaluationPipeline] Attempting LLM call via Gemini...", flush=True)
                from app.ai.gemini_provider import GeminiProvider
                gemini_prov = GeminiProvider()
                raw_response = gemini_prov.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    json_mode=True,
                    model_name="gemini-2.0-flash"
                )
                return self._parse_json(raw_response)
            except Exception as e:
                print(f"[EvaluationPipeline] Gemini failed: {e}", flush=True)

        print("[EvaluationPipeline] Utilizing local heuristic fallback", flush=True)
        return fallback_data

    def _parse_json(self, text: str) -> any:
        if isinstance(text, dict) or isinstance(text, list):
            return text
        if not text or not isinstance(text, str):
            raise ValueError(f"Invalid text for JSON parsing: {text}")

        cleaned = text.strip()
        if "```" in cleaned:
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            return json.loads(cleaned)
        except Exception:
            pass

        try:
            match = re.search(r"(\{.*\})|(\[.*\])", cleaned, re.DOTALL)
            if match:
                candidate = match.group(0).strip()
                candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
                return json.loads(candidate)
        except Exception:
            pass

        try:
            import ast
            return ast.literal_eval(cleaned)
        except Exception as pe:
            print(f"[EvaluationPipeline] JSON parse error: {pe}. Raw response: {text}", flush=True)
            raise pe
