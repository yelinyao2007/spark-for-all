from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator

class Understanding(StrEnum):
    UNKNOWN = 'unknown'
    EXPLORING = 'exploring'
    PARTIAL = 'partially_understood'
    UNDERSTOOD = 'understood'
    REINFORCE = 'needs_reinforcement'

class Strategy(StrEnum):
    SIMPLE = 'simple'
    ANALOGY = 'analogy'
    STEPS = 'steps'
    GUIDED = 'guided'
    EXAMPLE = 'example'
    QUIZ = 'quiz'

class Source(BaseModel):
    id: str
    title: str
    url: HttpUrl
    snippet: str
    retrieved_at: str
    # Retrieved is provenance, not a claim of independently verified truth.
    provenance: Literal['retrieved'] = 'retrieved'

class Quiz(BaseModel):
    kind: Literal['multiple_choice', 'true_false', 'short_answer']
    question: str = Field(min_length=2, max_length=300)
    options: list[str] = Field(default_factory=list, max_length=4)
    answer: str = Field(min_length=1, max_length=100)
    explanation: str = Field(min_length=1, max_length=300)

    @model_validator(mode='after')
    def valid_choices(self):
        if self.kind in ('multiple_choice', 'true_false'):
            if len(self.options) < 2 or self.answer not in self.options:
                raise ValueError('Answer must be an offered choice')
        return self

class Lesson(BaseModel):
    explanation: str = Field(min_length=5, max_length=2000)
    quiz: Quiz | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=5)
    visual: Literal['none', 'fractions'] = 'none'

class TopicState(BaseModel):
    topic: str
    question: str
    understanding: Understanding = Understanding.UNKNOWN
    strategy: Strategy = Strategy.SIMPLE
    attempts: int = 0
    correct_checks: int = 0
    completed_quizzes: int = 0
    confusion_count: int = 0
    self_reported: bool = False
    pending_quiz: Quiz | None = None
    previous_explanation: str = ''
    sources: list[Source] = Field(default_factory=list)
    checked_questions: list[str] = Field(default_factory=list)

class SessionState(BaseModel):
    grade: int = Field(default=5, ge=4, le=6)
    current_topic: str | None = None
    topics: dict[str, TopicState] = Field(default_factory=dict)
    interactions: int = 0

class Turn(BaseModel):
    text: str = Field(default='', max_length=1000)
    action: Literal['ask','again','example','understood','quiz','answer','skip'] = 'ask'

class SessionInput(BaseModel):
    grade: int = Field(default=5, ge=4, le=6)
