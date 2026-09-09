import os
import tempfile
import streamlit as st
import re
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
def clean_text(text):
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ==========================
# Load Environment Variables
# ==========================
load_dotenv()
# ==========================
# Professional UI
# ==========================

st.markdown("""
<style>

.main {
    background-color: #0E1117;
}

.block-container{
    padding-top: 1rem;
    max-width: 1400px;
}

.header-box{
    background: linear-gradient(90deg,#1f2937,#111827);
    padding:20px;
    border-radius:15px;
    text-align:center;
    border:1px solid #374151;
    margin-bottom:20px;
}

.header-title{
    color:white;
    font-size:38px;
    font-weight:bold;
}

.header-sub{
    color:#cbd5e1;
    font-size:16px;
}

.chat-box{
    background:#111827;
    padding:15px;
    border-radius:12px;
    border:1px solid #374151;
}

.answer-box{
    background:#1e293b;
    padding:18px;
    border-radius:12px;
    border-left:5px solid #22c55e;
    margin-top:15px;
}

.pdf-box{
    background:#111827;
    padding:15px;
    border-radius:12px;
    border:1px solid #374151;
}

.upload-box{
    background:#1f2937;
    padding:15px;
    border-radius:12px;
    margin-bottom:15px;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="header-title">
        📄 AI Document Assistant
    </div>
    <div class="header-sub">
        Chat with your PDFs using AI + RAG + Gemini
    </div>
</div>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="AI Document Assistant",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI Document Assistant")
st.write("Upload a PDF and ask questions from the document.")

# ==========================
# API Key
# ==========================
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("GOOGLE_API_KEY not found in .env file")
    st.stop()

# ==========================
# Upload PDF
# ==========================
st.markdown('<div class="upload-box">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "📂 Upload PDF",
    type=["pdf"]
)

st.markdown('</div>', unsafe_allow_html=True
            )

if uploaded_file:

    # Save PDF temporarily
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as tmp_file:

        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    st.success("✅ PDF Uploaded Successfully")
    left_col, right_col = st.columns([1,2])
    

    # ==========================
    # Load PDF
    # ==========================
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    # ==========================
    # Split Documents
    # ==========================
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    docs = splitter.split_documents(documents)
    for doc in docs:
        doc.page_content = clean_text(doc.page_content)

    st.info(f"📑 Total Chunks Created: {len(docs)}")

    try:

        # ==========================
        # Local Embeddings
        # ==========================
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # ==========================
        # Vector Database
        # ==========================
        vectordb = Chroma.from_documents(
            documents=docs,
            embedding=embeddings
        )
        retriever = vectordb.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}

        )

    except Exception as e:
        st.error(f"Embedding Error: {e}")
        st.stop()

    # ==========================
    # Question Input
    # ==========================
    question = st.text_input(
        "Ask a Question about the PDF"
    )

    if question:

        with st.spinner("🔍 Searching Document..."):

            try:

                retrieved_docs = retriever.invoke(question)

                context = "\n\n".join(
                     [clean_text(doc.page_content) for doc in retrieved_docs]
                )

                prompt = f"""
You are an intelligent PDF assistant.

Answer ONLY using the provided context.

Rules:
1. Give a clean answer.
2. Do NOT return JSON.
3. Do NOT return Python objects.
4. Use bullet points when needed.
5. If answer is unavailable, return exactly:

No Information Available

CONTEXT:
{context}

QUESTION:
{question}
"""

                # ==========================
                # Gemini LLM
                # ==========================
                llm = ChatGoogleGenerativeAI(
                    model="gemini-3.5-flash",
                    temperature=0.2,
                    google_api_key=api_key
                )

                response = llm.invoke(prompt)

                # ==========================
                # Clean Output
                # ==========================
                answer = response.content

                if isinstance(answer, list):
                    answer = " ".join(
                        item.get("text", "")
                        for item in answer
                        if isinstance(item, dict)
                    )

                st.subheader("🤖 Answer")
                st.markdown(answer)

            
            except Exception as e:
                st.error(f"Error: {e}")