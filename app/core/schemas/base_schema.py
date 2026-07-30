from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel
import datetime
from typing import Any

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @field_serializer('*', mode='wrap')
    def serialize_datetime(self, value: Any, handler: Any) -> Any:
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.isoformat()
        return handler(value)
