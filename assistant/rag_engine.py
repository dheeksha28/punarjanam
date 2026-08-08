from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from django.conf import settings
from patients.models import Patient

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

FALLBACK_MESSAGE = "I'm having trouble connecting to the AI assistant right now. Please try again in a moment, or reach out to your care team directly if this is urgent."


def build_patient_documents(patient=None):
    documents = []
    patients = [patient] if patient else Patient.objects.all()
    for p in patients:
        text = f"Patient: {p.name}, Age: {p.age}, Gender: {p.get_gender_display()}, Diagnosis: {p.diagnosis}.\n"
        if p.doctor_name:
            text += f"Assigned Doctor: {p.doctor_name}.\n"
        for treatment in p.treatments.all():
            text += f"Treatment: {treatment.get_treatment_type_display()} - {treatment.treatment_name}. "
            text += f"Sessions completed: {treatment.completed_sessions}/{treatment.total_sessions}. "
            if treatment.next_session_date:
                text += f"Next session: {treatment.next_session_date}. "
            text += f"Notes: {treatment.notes}\n"
        for medicine in p.medicines.all():
            times_str = ", ".join([t.strftime('%I:%M %p') for t in medicine.schedule_times()])
            text += f"Medicine: {medicine.medicine_name}, Dosage: {medicine.dosage}, Frequency: every {medicine.frequency_hours} hours, Schedule times today: {times_str}, Notes: {medicine.notes}\n"
        documents.append(text)
    return documents


def build_vector_store(patient=None):
    documents = build_patient_documents(patient)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents(documents)

    vectorstore = Chroma.from_documents(
        chunks,
        embedding_model,
        persist_directory="chroma_db"
    )
    return vectorstore


def verify_answer(answer, context):
    try:
        llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name="llama-3.1-8b-instant")

        verify_prompt = f"""You are a strict medical fact-checker. Compare the DRAFT ANSWER against the SOURCE RECORDS below.

SOURCE RECORDS (the only true facts):
{context}

DRAFT ANSWER:
{answer}

TASK:
- Check if the draft answer mentions any specific medicine name that does NOT appear in the source records.
- If it does, rewrite the answer removing or correcting that specific claim, replacing it with "I don't see that medicine in your records" where relevant.
- If the answer only uses information present in the records (or general safe advice not tied to a specific unlisted medicine), return it UNCHANGED.
- Do not add any new information. Only remove or correct unsupported medicine claims.

Return ONLY the final corrected answer text, nothing else — no explanation, no preamble.

Corrected answer:"""

        response = llm.invoke(verify_prompt)
        return response.content
    except Exception:
        # If verification fails, fall back to the unverified draft rather than breaking the page
        return answer


def get_answer(question, patient=None):
    try:
        vectorstore = build_vector_store(patient)
        relevant_docs = vectorstore.similarity_search(question, k=5)
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
    except Exception:
        return FALLBACK_MESSAGE

    try:
        llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name="llama-3.1-8b-instant")

        if patient:
            prompt = f"""You are a warm, caring medical assistant speaking directly to a patient going through cancer treatment. Use "you" and "your" — never refer to them by name in third person.

Here are the patient's own records — this is the ONLY information you know about them:
{context}

The patient asks: {question}

STRICT RULES:
- ONLY mention medicines, treatments, or details that appear EXACTLY in the records above. Never invent, assume, or guess a medicine name, dosage, or detail that isn't explicitly written there.
- If the records don't contain a medicine or detail relevant to their question, say so clearly.
- If they mention a symptom, only connect it to medicines actually listed above — do not name any medicine that isn't in the records.
- You may use general medical knowledge about symptom management (e.g., mouth ulcers from chemo) as long as you don't invent specific medicines not in their records.
- Always include when they should contact their care team urgently, if relevant to the symptom.

FORMAT (follow this structure):
1. Start with one warm, brief sentence acknowledging how they feel.
2. If there are self-care tips, list them as short bullet points starting with "- " (one per line).
3. If relevant, add a short line: "If the pain/discomfort is severe, your care team may prescribe:" followed by bullet points.
4. Add a line: "Contact your care team today if:" followed by bullet points of warning signs, if relevant to the symptom.
5. End with ONE short follow-up question to understand their situation better, and a brief encouraging note.

Keep bullet points short (under 12 words each). Do not write dense paragraphs.

Answer:"""
        else:
            prompt = f"""You are a medical records assistant helping hospital staff. Use ONLY the patient records provided below to answer — do not use any outside medical knowledge to fill gaps.

Records:
{context}

Question: {question}

STRICT RULES:
- Only state facts, medicines, dates, or details that appear EXACTLY in the records above.
- If the records don't contain enough information to answer fully, say so explicitly rather than guessing or inferring.
- Never invent a medicine, dosage, doctor name, or date that isn't literally present in the records.
- If multiple patients are relevant, be clear about which patient each fact belongs to.

Answer:"""

        response = llm.invoke(prompt)
        draft_answer = response.content
    except Exception:
        return FALLBACK_MESSAGE

    if patient:
        return verify_answer(draft_answer, context)
    return draft_answer