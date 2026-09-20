"""
rag_engine.py  -  ChatGPT/Claude-style patient assistant (matches patients/models.py)

Per question:
  1. Load the patient's real data from the DB (diagnosis, treatments, medicines)
  2. Classify intent: FACTUAL / SYMPTOM / GENERAL
  3. For SYMPTOM/GENERAL: LLM builds a search query, searches the real web
  4. LLM answers with a prompt matched to the intent
  5. Safety pass + urgent-symptom banner (for SYMPTOM/GENERAL patient answers)

Install:
    pip install tavily-python duckduckgo-search
settings.py:
    TAVILY_API_KEY = config('TAVILY_API_KEY', default='')   # optional, DuckDuckGo is the fallback
"""

import re
import uuid
from django.conf import settings


from langchain_groq import ChatGroq
from patients.models import Patient

FALLBACK_MESSAGE = (
    "I'm having trouble connecting to the AI assistant right now. "
    "Please try again in a moment, or reach out to your care team directly if this is urgent."
)

MAIN_MODEL = "openai/gpt-oss-120b"   # answers
FAST_MODEL = "openai/gpt-oss-20b"    # small helper tasks

TRUSTED_MEDICAL_DOMAINS = [
    "cancer.gov", "cancer.org", "mayoclinic.org", "nhs.uk", "medlineplus.gov",
    "macmillan.org.uk", "cancerresearchuk.org", "asco.org", "cancer.net",
    "clevelandclinic.org", "who.int",
]

URGENT_PATTERNS = [
    r"\bfever\b", r"\bchills\b",
    r"trouble breathing|short(ness)? of breath|can'?t breathe",
    r"chest pain",
    r"blood in (stool|urine|vomit)|vomiting blood|bleeding that (won'?t|does not) stop",
    r"swelling of (the )?(face|lips|tongue|throat)",
    r"seizure|faint(ed|ing)|unconscious",
    r"severe (pain|rash)|blister",
]

_embedding_model = None


def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

    return _embedding_model

def llm(model=MAIN_MODEL, temperature=0.3):
    return ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=model, temperature=temperature)


# ─────────────────────────────────────────────
# 1. PATIENT DATA
# ─────────────────────────────────────────────
def patient_to_text(p):
    text = (
        f"Patient: {p.name}, Age: {p.age}, Gender: {p.get_gender_display()}, "
        f"Diagnosis: {p.diagnosis}.\n"
    )
    if p.doctor_name:
        text += f"Assigned Doctor: {p.doctor_name}.\n"

    for t in p.treatments.all():
        text += (
            f"Treatment: {t.get_treatment_type_display()} - {t.treatment_name}. "
            f"Started/last given: {t.date_administered}. "
            f"Sessions completed: {t.completed_sessions}/{t.total_sessions}. "
        )
        if t.next_session_date:
            text += f"Next session: {t.next_session_date}. "
        if t.notes:
            text += f"Notes: {t.notes}"
        text += "\n"

    for m in p.medicines.all():
        times_str = ", ".join(x.strftime("%I:%M %p") for x in m.schedule_times())
        text += (
            f"Medicine: {m.medicine_name}, Dosage: {m.dosage or 'not specified'}, "
            f"Every {m.frequency_hours} hours, Times today: {times_str}."
        )
        if m.notes:
            text += f" Notes: {m.notes}"
        text += "\n"
    return text


def patient_summary(p):
    treatments = ", ".join(
        f"{t.get_treatment_type_display()} ({t.treatment_name})" for t in p.treatments.all()
    ) or "none recorded"
    medicines = ", ".join(m.medicine_name for m in p.medicines.all()) or "none recorded"
    return f"Diagnosis: {p.diagnosis}\nTreatments: {treatments}\nMedicines: {medicines}"


def staff_context(question, k=5):
    """Staff mode (all patients): include all patient records directly.
    No vector search needed at this scale, and it keeps the deployed app lightweight."""
    patients = Patient.objects.all()
    if not patients:
        return "No patients in the system."
    return "\n\n".join(patient_to_text(p) for p in patients)

# ─────────────────────────────────────────────
# 2. INTENT CLASSIFICATION
# ─────────────────────────────────────────────
def classify_intent(question, history_text):
    """Classify into FACTUAL (personal record lookup), SYMPTOM (personal health concern),
    or GENERAL (external medical knowledge not about their specific file)."""
    prompt = f"""Classify the PATIENT'S MESSAGE below into exactly one word: FACTUAL, SYMPTOM, or GENERAL.

FACTUAL = a direct lookup answerable from their own records alone, e.g. "when is my next session",
"what medicines am I on", "what's my diagnosis", "who is my doctor".

SYMPTOM = describing a new symptom, side effect, pain, or health concern about THEMSELVES that needs
explanation tied to their own treatment, self-care advice, and red-flag warnings, e.g. "I have a rash",
"I feel nauseous".

GENERAL = a general medical/knowledge question NOT about their personal situation, e.g. "what is the
survival rate for colon cancer", "what causes cancer", "latest research on chemotherapy", "is
immunotherapy better than chemo".

If genuinely unclear, choose SYMPTOM.

RECENT CONVERSATION:
{history_text}

PATIENT'S MESSAGE: {question}

Return ONLY one word: FACTUAL, SYMPTOM, or GENERAL."""
    try:
        result = llm(FAST_MODEL, 0).invoke(prompt).content.strip().upper()
        if "FACTUAL" in result:
            return "FACTUAL"
        if "GENERAL" in result:
            return "GENERAL"
        return "SYMPTOM"
    except Exception as e:
        print(f"INTENT ERROR: {e}")
        return "SYMPTOM"


# ─────────────────────────────────────────────
# 3. WEB SEARCH
# ─────────────────────────────────────────────
def build_search_query(question, summary, history_text):
    prompt = f"""Write ONE short Google-style search query (max 15 words) that will find
reliable medical information to answer the patient's question.
Combine the symptom with the patient's actual diagnosis / treatment / medicines when relevant.
Example: "skin rash side effect cisplatin chemotherapy causes management"

PATIENT SUMMARY:
{summary}

RECENT CHAT:
{history_text}

QUESTION: {question}

Return ONLY the query text."""
    try:
        return llm(FAST_MODEL, 0).invoke(prompt).content.strip().strip('"')
    except Exception as e:
        print(f"QUERY BUILD ERROR: {e}")
        return question


def web_search(query, max_results=5):
    key = getattr(settings, "TAVILY_API_KEY", "")
    if key:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=key)
            results = client.search(query, max_results=max_results,
                                    include_domains=TRUSTED_MEDICAL_DOMAINS).get("results", [])
            if len(results) < 2:
                results += client.search(query, max_results=max_results).get("results", [])
            return [{"title": r["title"], "url": r["url"], "content": r["content"]}
                    for r in results[:max_results]]
        except Exception as e:
            print(f"TAVILY ERROR: {e}")

    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            hits = list(ddgs.text(
                query + " site:cancer.gov OR site:cancer.org OR site:mayoclinic.org OR site:nhs.uk",
                max_results=max_results))
            if len(hits) < 2:
                hits += list(ddgs.text(query, max_results=max_results))
        return [{"title": h["title"], "url": h["href"], "content": h["body"]} for h in hits[:max_results]]
    except Exception as e:
        print(f"DDG ERROR: {e}")
        return []


def format_web_results(results):
    if not results:
        return "No web results were available. Answer from general medical knowledge and say so."
    return "\n\n".join(
        f"[{i}] {r['title']}\nURL: {r['url']}\n{r['content'][:700]}"
        for i, r in enumerate(results, 1)
    )


# ─────────────────────────────────────────────
# 4. SAFETY
# ─────────────────────────────────────────────
def is_urgent(text):
    return any(re.search(p, text, re.I) for p in URGENT_PATTERNS)


def safety_check(answer):
    prompt = f"""You are a medical safety reviewer.
The ANSWER below must NOT:
- tell the patient to start, stop, skip, or change the dose of any prescription medicine
- recommend a specific new drug with a dose

If it does, rewrite only those sentences so they say to ask their doctor/care team first.
If it is fine, return it EXACTLY unchanged, keeping all formatting and the Sources list.
Return ONLY the final answer.

ANSWER:
{answer}"""
    try:
        return llm(FAST_MODEL, 0).invoke(prompt).content.strip()
    except Exception as e:
        print(f"SAFETY ERROR: {e}")
        return answer


# ─────────────────────────────────────────────
# 5. MAIN ENTRY
# ─────────────────────────────────────────────
def get_answer(question, patient=None, history=None):
    history = history or []
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:]) or "None"

    # ---- Step 0: what kind of question is this? ----
    intent = classify_intent(question, history_text) if patient else "SYMPTOM"

    # ---- Step 1: patient data ----
    try:
        if patient:
            context = patient_to_text(patient)
            summary = patient_summary(patient)
        else:
            context = staff_context(question)
            summary = "Staff view (multiple patients)"
    except Exception as e:
        print(f"CONTEXT ERROR: {e}")
        return FALLBACK_MESSAGE

    # ---- Step 2: real-world search (only for SYMPTOM/GENERAL) ----
    if intent in ("SYMPTOM", "GENERAL"):
        query = build_search_query(question, summary, history_text)
        web_context = format_web_results(web_search(query))
    else:
        query = ""
        web_context = ""

    # ---- Step 3: answer ----
    try:
        if patient and intent == "FACTUAL":
            prompt = f"""You are a warm health assistant for a cancer patient. Answer directly and briefly.

━━━ THEIR OWN RECORDS ━━━
{context}

━━━ RECENT CONVERSATION ━━━
{history_text}

━━━ PATIENT ASKS ━━━
{question}

RULES:
- Answer ONLY using their records above. 1-3 short sentences, no preamble, no re-explaining past topics.
- Do NOT add self-care tips, red flags, or sources — this is a simple factual lookup.
- If the records don't contain the answer, say so plainly and suggest they ask their care team.

Answer:"""

        elif patient and intent == "GENERAL":
            prompt = f"""You are a knowledgeable health assistant answering a general medical question
for a cancer patient. This question is NOT about their personal treatment — answer it generally using
the web information below, in plain, reassuring language.

━━━ REAL-WORLD MEDICAL INFORMATION (live web search: "{query}") ━━━
{web_context}

━━━ PATIENT ASKS ━━━
{question}

RULES:
- Answer using the web information, cited as [1], [2], etc.
- Do NOT reference their personal diagnosis, treatments, or medicines — this is a general question.
- Keep it clear and not overly long — a few short paragraphs.
- End with a "Sources:" list of the URLs actually used.
- If the web information is insufficient, say so honestly rather than guessing.

Answer:"""

        elif patient:
            prompt = f"""You are a warm, knowledgeable health assistant for a cancer patient, like a
caring nurse who has read their file. Speak to them directly ("you", "your").

━━━ THEIR OWN RECORDS ━━━
{context}

━━━ REAL-WORLD MEDICAL INFORMATION (live web search: "{query}") ━━━
{web_context}

━━━ RECENT CONVERSATION ━━━
{history_text}

━━━ PATIENT SAYS ━━━
{question}

HOW TO ANSWER
1. Start with one empathetic sentence.
2. ANALYSE THEIR FILE: look at their diagnosis, treatments and medicines. Say whether the symptom
   is a known side effect of THEIR treatment, e.g. "Since you are on <treatment from records>,
   skin rash is a common side effect because ...". Explain the WHY in simple words using the web
   information.
3. Say clearly when something is likely vs. uncertain. Never claim a certain diagnosis.
4. "What you can do at home": practical, evidence-based self-care from the web sources.
5. "Contact your care team today if:" bullet list of warning signs specific to this symptom.
6. One short encouraging sentence.
7. "Sources:" list only the URLs you actually used, e.g. [1] title - url.

RULES
- Facts about THEIR treatment, medicines, doses and dates come ONLY from THEIR RECORDS. Never invent them.
- General medical explanations may come from the web information (cite as [1], [2]).
- Mention drug options only as "ask your doctor whether X could help". Never tell them to start,
  stop or change a medicine or dose.
- If their records lack something (e.g. diagnosis says "Not specified yet"), say so naturally and
  still help using the web information. Do NOT refuse with a canned message.
- Keep it clear, in short paragraphs and bullets.

Answer:"""
        else:
            prompt = f"""You are a clinical assistant for hospital staff.

PATIENT RECORDS:
{context}

WEB INFORMATION (query: "{query}"):
{web_context}

QUESTION: {question}

Patient-specific facts (names, doses, dates) only from the records. General medical knowledge may
use the web information with [n] citations and a Sources list. Say when the records don't contain
something. Be concise.

Answer:"""

        answer = llm().invoke(prompt).content.strip()

    except Exception as e:
        print(f"LLM ERROR: {e}")
        return FALLBACK_MESSAGE

    # ---- Step 4: safety ----
    if patient and intent in ("SYMPTOM", "GENERAL"):
        answer = safety_check(answer)
        if intent == "SYMPTOM" and is_urgent(question):
            answer = (
                "⚠️ **What you describe can be serious during cancer treatment. "
                "Please call your care team or go to the nearest emergency department now, "
                "don't wait.**\n\n" + answer
            )
    return answer