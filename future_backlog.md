# 🚀 Future Improvements & Technical Debt

This file tracks critical improvements, features, and fixes that have been identified but deferred for future implementation.

---

## 🏗️ NLU & Logic

### 5.1 | Smart Price Extraction (Roman Urdu)
**Status:** Deferred
**Context:** The current NLU price extraction using `re.search(r"(\d+)", text)` is too naive and captures quantities (e.g., "2 items") as prices.
**Requirement:** 
- Support Roman Urdu context (e.g., "1500 mein", "2000 ka dedo").
- Use English digits but ignore low-value carding/quantities.
**Proposed Solution:**
1. Extract all numbers.
2. Filter out numbers below a threshold (e.g., `< 50`).
3. Use keyword proximity matching for negation/currency terms (`rs`, `pkr`, `me`, `ka`, `ke`).

---

## 🔒 Security & Architecture
*(Add other deferred items here as we go)*
