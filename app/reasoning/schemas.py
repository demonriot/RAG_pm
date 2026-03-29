from typing import Literal, List, Union, Optional
from pydantic import BaseModel

class CourseNode(BaseModel):
    type: Literal["COURSE"]
    course: str

class BoolNode(BaseModel):
    type: Literal["AND", "OR"]
    items: List["PrereqNode"]

class UnknownNode(BaseModel):
    type: Literal["UNKNOWN"]
    text: str

PrereqNode = Union[CourseNode, BoolNode, UnknownNode]