from pydantic import BaseModel

class NLUInput(BaseModel):
    text: str
    session_id: str

class NLUOutput(BaseModel):
    intent: str
    entities: dict
    sentiment: str
    language: str   # e.g. "english", "roman_urdu", "urdu", "other"
