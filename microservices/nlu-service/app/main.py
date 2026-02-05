import re
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="NLU Service (MS2)")


class NLUInput(BaseModel):
    text: str
    session_id: str


class NLUOutput(BaseModel):
    intent: str
    entities: dict
    sentiment: str


@app.post("/parse", response_model=NLUOutput)
async def parse(input: NLUInput):
    text = input.text.lower()

    # -------------------------
    # 1️⃣ PRICE Extraction
    # -------------------------
    price_match = re.search(r"(\d+)", text)
    price = float(price_match.group(1)) if price_match else None

    # -------------------------
    # -------------------------
    # 2️⃣ Intent Detection
    # -------------------------
    greetings = ["hi", "hello", "hey"]
    farewells = ["bye", "goodbye", "see you", "later"]
    deal_words = ["deal", "accept", "agree"]
    previous_offer_queries = ["earlier price", "previous offer", "last offer", "previous counter", "previous deal"]

    # Use regex for word boundary matching to avoid partial matches (e.g., "this" -> "hi")
    def contains_word(text, words):
        pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\b"
        return re.search(pattern, text) is not None

    if contains_word(text, greetings):
        intent = "GREET"
    elif contains_word(text, farewells):
        intent = "BYE"
    elif any(word in text for word in deal_words):
        intent = "DEAL"
    elif any(word in text for word in previous_offer_queries):
        intent = "ASK_PREVIOUS_OFFER"
    elif price:
        intent = "MAKE_OFFER"
    else:
        intent = "ASK_QUESTION"


    # -------------------------
    # 3️⃣ Sentiment Detection
    # -------------------------
    def detect_sentiment(text: str) -> str:
        text = text.lower()
        negative_words = ["high", "disappointed","expensive", "unfair", "bad", "angry", "upset", "worst", "frustrated", "annoyed"]
        positive_words = ["good", "great", "happy", "perfect", "amazing", "love"]

        if any(w in text for w in negative_words):
            return "negative"
        if any(w in text for w in positive_words):
            return "positive"
        else:
            return "neutral"

    sentiment = detect_sentiment(text)

    return {
        "intent": intent,
        "entities": {"PRICE": price},
        "sentiment": sentiment,
    }
