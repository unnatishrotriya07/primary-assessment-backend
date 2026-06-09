from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.question_repository import QuestionRepository
from app.schemas.question_schema import QuestionCreate, AIQuestionParams, QuestionBatchSave
from app.models.question import Question
from app.models.subject import Subject
from app.models.chapter import Chapter
from app.core.exceptions import EntityNotFoundException
from app.ai.question_generator import QuestionGenerator

class QuestionService:
    def __init__(self, db: Session):
        self.db = db
        self.question_repo = QuestionRepository(db)
        self.ai_generator = QuestionGenerator()

    def get_all_questions(self) -> List[Question]:
        return self.question_repo.get_all()

    def get_questions(
        self,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        session: Optional[str] = None
    ) -> List[Question]:
        query = self.db.query(Question)
        if class_id is not None:
            query = query.filter(Question.class_id == class_id)
        if subject_id is not None:
            query = query.filter(Question.subject_id == subject_id)
        if chapter_id is not None:
            query = query.filter(Question.chapter_id == chapter_id)
        if session is not None and session != "":
            query = query.filter(Question.session == session)
        return query.all()

    def get_question_by_id(self, question_id: int) -> Question:
        q = self.question_repo.get_by_id(question_id)
        if not q:
            raise EntityNotFoundException("Question", str(question_id))
        return q

    def create_question(self, question_in: QuestionCreate) -> Question:
        q = Question(
            text=question_in.text,
            options=question_in.options,
            correct_answer=question_in.correct_answer,
            difficulty=question_in.difficulty,
            cognitive_level=question_in.cognitive_level,
            class_id=question_in.class_id,
            subject_id=question_in.subject_id,
            chapter_id=question_in.chapter_id,
            generated_by="manual",
            session=question_in.session
        )
        return self.question_repo.create(q)

    def generate_ai_questions(self, params: AIQuestionParams) -> List[Question]:
        # Caching/DB Check: If not regenerating, check for existing questions
        if not params.regenerate:
            query = self.db.query(Question).filter(
                Question.chapter_id == params.chapter_id,
                Question.difficulty == params.difficulty,
                Question.cognitive_level == params.cognitive_level
            )
            if params.session:
                query = query.filter(Question.session == params.session)
            existing = query.all()
            if existing:
                return existing

        # If regenerating, delete existing questions matching the combination (only if NOT preview_only)
        if params.regenerate and not params.preview_only:
            query = self.db.query(Question).filter(
                Question.chapter_id == params.chapter_id,
                Question.difficulty == params.difficulty,
                Question.cognitive_level == params.cognitive_level
            )
            if params.session:
                query = query.filter(Question.session == params.session)
            query.delete()
            self.db.commit()

        # Fetch subject details for route determination (Math/Logic detection)
        subject = self.db.query(Subject).filter(Subject.id == params.subject_id).first()
        subject_name = subject.name if subject else "Unknown"
        subject_code = subject.code if subject else "UNK"

        # Fetch chapter details (number, title, content)
        chapter = self.db.query(Chapter).filter(Chapter.id == params.chapter_id).first()
        chapter_number = chapter.number if chapter else "Unknown"
        chapter_title = chapter.title if chapter else "Unknown"
        chapter_content = (chapter.text_content or chapter.content) if chapter else None

        # Invoke LLM/AI question generator component
        generated_data, provider = self.ai_generator.generate_questions(
            subject_name=subject_name,
            subject_code=subject_code,
            subject_id=params.subject_id,
            chapter_id=params.chapter_id,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            chapter_content=chapter_content,
            difficulty=params.difficulty,
            cognitive_level=params.cognitive_level,
            count=params.count
        )
        
        saved_questions = []
        for item in generated_data:
            q = Question(
                text=item["text"],
                options=item["options"],
                correct_answer=item["correct_answer"],
                difficulty=params.difficulty,
                cognitive_level=params.cognitive_level,
                class_id=params.class_id,
                subject_id=params.subject_id,
                chapter_id=params.chapter_id,
                generated_by=provider,
                session=params.session
            )
            if params.preview_only:
                q.id = 0
                saved_questions.append(q)
            else:
                saved_questions.append(self.question_repo.create(q))
            
        return saved_questions

    def batch_create_questions(self, batch_in: QuestionBatchSave) -> List[Question]:
        # If clear_existing is True and filters are provided, delete existing ones first
        if batch_in.clear_existing and batch_in.chapter_id:
            query = self.db.query(Question).filter(Question.chapter_id == batch_in.chapter_id)
            if batch_in.difficulty:
                query = query.filter(Question.difficulty == batch_in.difficulty)
            if batch_in.cognitive_level:
                query = query.filter(Question.cognitive_level == batch_in.cognitive_level)
            if batch_in.questions and len(batch_in.questions) > 0 and batch_in.questions[0].session:
                query = query.filter(Question.session == batch_in.questions[0].session)
            query.delete()
            self.db.commit()

        saved_questions = []
        for q_in in batch_in.questions:
            q = Question(
                text=q_in.text,
                options=q_in.options,
                correct_answer=q_in.correct_answer,
                difficulty=q_in.difficulty,
                cognitive_level=q_in.cognitive_level,
                class_id=q_in.class_id,
                subject_id=q_in.subject_id,
                chapter_id=q_in.chapter_id,
                generated_by=q_in.generated_by or "manual",
                session=q_in.session
            )
            saved_questions.append(self.question_repo.create(q))
            
        return saved_questions

    def delete_question(self, question_id: int) -> None:
        q = self.get_question_by_id(question_id)
        self.question_repo.delete(q)
