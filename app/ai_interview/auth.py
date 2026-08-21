import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

import app.common.database  # noqa: F401  # registers models + Base first (avoids circular import)

from app.core.dependencies import get_db
from app.core.models.interview import Interview
from app.core.models.student_assessment import StudentAssessment

logger = logging.getLogger(__name__)


def verify_token(db: Session, token: str, email: Optional[str] = None) -> StudentAssessment:
    """Validate a student assessment token. Returns the StudentAssessment row."""
    sa = (
        db.query(StudentAssessment)
        .filter(StudentAssessment.token == token)
        .first()
    )
    if not sa:
        raise HTTPException(status_code=401, detail="Invalid token.")

    if sa.status == "Completed":
        raise HTTPException(status_code=401, detail="This assessment link has already been used and completed.")
    if sa.is_used and sa.status != "Started":
        raise HTTPException(status_code=401, detail="This assessment link has already been used.")

    import datetime
    if sa.expires_at and sa.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=401, detail="This assessment link has expired.")

    if email is not None:
        if not sa.student_email or sa.student_email.strip().lower() != email.strip().lower():
            raise HTTPException(status_code=401, detail="Email mismatch. This link was created for another student.")

    return sa


def require_interview_access(
    interview_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Interview:
    """Dependency: bearer token must own the target interview (or be absent for explicitly-token routes)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    sa = verify_token(db, token.strip())

    interview = (
        db.query(Interview)
        .filter(Interview.id == interview_id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")
    if interview.student_assessment_id != sa.id:
        raise HTTPException(status_code=403, detail="Token does not own this interview.")

    return interview
