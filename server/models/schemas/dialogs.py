from typing import List, Optional

from pydantic import BaseModel


class DialogRequest(BaseModel):
    dialog_type: str
    title: str
    message: str
    options: Optional[List[str]] = None
    timeout: Optional[int] = None
    user_id: str = "system"


class DialogActionRequest(BaseModel):
    action: str
    user_id: str = "system"


class ProgressDialogRequest(BaseModel):
    title: str
    message: str
    max_value: int = 100
    current_value: int = 0
    user_id: str = "system"


class InputDialogRequest(BaseModel):
    title: str
    message: str
    input_type: str = "text"
    default_value: Optional[str] = None
    user_id: str = "system"
