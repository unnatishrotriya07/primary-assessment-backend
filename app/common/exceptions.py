from fastapi import HTTPException, status

class BaseAPIException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class EntityNotFoundException(BaseAPIException):
    def __init__(self, entity_name: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} identified by '{identifier}' was not found."
        )

class InvalidCredentialsException(BaseAPIException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, email, or password credentials."
        )

class AccessDeniedException(BaseAPIException):
    def __init__(self, reason: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {reason}."
        )

class EntityAlreadyExistsException(BaseAPIException):
    def __init__(self, entity_name: str, field_name: str, value: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{entity_name} with {field_name} '{value}' already exists."
        )
