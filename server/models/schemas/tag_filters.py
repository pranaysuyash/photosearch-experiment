from typing import List, Optional

from pydantic import BaseModel


class Legacy2TagExpression(BaseModel):
    tag: str
    operator: str = "has"  # 'has', 'not_has', 'maybe_has'


class Legacy2TagFilterCreateRequest(BaseModel):
    name: str
    tag_expressions: List[Legacy2TagExpression]
    combination_operator: str = "AND"  # 'AND' or 'OR'


class Legacy2TagFilterUpdateRequest(BaseModel):
    name: Optional[str] = None
    tag_expressions: Optional[List[Legacy2TagExpression]] = None
    combination_operator: Optional[str] = None


class TagExpression(BaseModel):
    tag: str
    operator: str = "has"  # 'has', 'not_has', 'maybe_has'


class TagFilterCreateRequest(BaseModel):
    name: str
    tag_expressions: List[TagExpression]
    combination_operator: str = "AND"  # 'AND' or 'OR'


class TagFilterUpdateRequest(BaseModel):
    name: Optional[str] = None
    tag_expressions: Optional[List[TagExpression]] = None
    combination_operator: Optional[str] = None
