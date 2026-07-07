import operator
from typing import Annotated, TypedDict, List
from pydantic import BaseModel, Field
class AgentState(TypedDict):
    topic: str
    research_plan: List[str]
    raw_data: Annotated[List[str], operator.add]
    summary: str
    draft: str
    review_feedback: str
    revision_count: int

