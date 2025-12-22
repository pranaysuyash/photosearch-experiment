from pydantic import BaseModel


class NoteCreate(BaseModel):
    note: str
