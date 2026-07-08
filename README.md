# 🌐 Multi-language Course Content Translator Agent

> **AI-powered educational content translation** using IBM Watsonx.ai (Granite models) + RAG-enhanced context retrieval. Translates PDFs, PowerPoints, Word documents, and text notes into 17+ regional and international languages while preserving technical accuracy and pedagogical quality.

---

## ✨ Features

| Feature | Details |
|---|---|
| **AI Model** | IBM Watsonx.ai — `ibm/granite-4-h-small` (Granite chat completion) |
| **RAG Pipeline** | FAISS vector store + sentence-transformers (multilingual MiniLM) |
| **Knowledge Base** | NCERT, CBSE, UGC, NEP 2020 glossaries + curriculum frameworks |
| **Document Support** | PDF, PPTX, DOCX, TXT, Markdown (up to 25 MB) |
| **Languages** | Hindi, Marathi, Tamil, Telugu, Bengali, Gujarati, Kannada, Malayalam, Punjabi, Odia, Urdu + French, German, Spanish, Arabic, Chinese, Japanese |
| **Dashboard** | Upload tracking, translation history, language-wise usage stats |
| **Dark Mode** | Full dark/light theme toggle with local storage persistence |
| **Agent Instructions** | Single-file customization of tone, terminology, formatting rules |
| **Mobile** | Fully responsive Bootstrap 5 UI |

---

## 🗂️ Project Structure

```
.
├── run.py                         ← Application entry point
├── requirements.txt               ← Python dependencies
├── .env.example                   ← Environment variable template
│
└── app/
    ├── __init__.py                ← Flask app factory
    ├── models.py                  ← SQLAlchemy DB models (Document, Translation)
    ├── agent_instructions.py      ← ✏️  CUSTOMISE TRANSLATION BEHAVIOUR HERE
    │
    ├── routes/
    │   ├── main.py                ← Page routes (dashboard, translate, history)
    │   └── api.py                 ← REST API (upload, translate, stats, CRUD)
    │
    ├── rag/
    │   └── vector_store.py        ← FAISS vector store + RAG retrieval
    │
    ├── utils/
    │   ├── document_processor.py  ← PDF/PPTX/DOCX/TXT extraction + chunking
    │   └── watsonx_client.py      ← IBM Watsonx.ai API client wrapper
    │
    ├── templates/
    │   ├── base.html              ← Sidebar, topbar, dark mode, toasts
    │   ├── dashboard.html         ← Stats, recent docs, language chart
    │   ├── translate.html         ← Upload + translate UI
    │   ├── history.html           ← Translation history table
    │   ├── documents.html         ← Document card grid
    │   └── translation_detail.html← Full translation viewer
    │
    ├── data/
    │   ├── glossaries/
    │   │   └── academic_glossary.json  ← NCERT/CBSE terminology (Math, Science, CS, Econ, History)
    │   └── vector_store/          ← Auto-generated FAISS index (after first run)
    │
    └── static/
        └── uploads/               ← Uploaded document storage
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- IBM Cloud account with Watsonx.ai enabled
- A Watsonx.ai **Project ID**
- An **IBM Cloud API Key**

### 2. Clone & Setup

```bash
# Clone the repo
git clone https://github.com/your-org/multilang-translator-agent.git
cd multilang-translator-agent

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example env file
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
IBM_WATSONX_PROJECT_ID=your_project_id_here
FLASK_SECRET_KEY=generate_a_random_string_here
```

> ⚠️ **Never commit `.env` to version control.** It is already in `.gitignore`.

### 4. Run

```bash
python run.py
```

Open **http://localhost:5000** in your browser.

On first start, the app will:
1. Create the SQLite database (`instance/translator.db`)
2. Bootstrap the RAG vector store from `app/data/glossaries/academic_glossary.json`
3. Start serving the web UI

---

## 🔑 Getting IBM Watsonx Credentials

1. Log in to [IBM Cloud](https://cloud.ibm.com)
2. Navigate to **Watsonx** → **AI Studio** → create or open a project
3. Copy your **Project ID** from the project settings
4. Go to **Manage** → **Access (IAM)** → **API Keys** → create an API key
5. Paste both into your `.env` file

---

## ✏️ Customizing Agent Behaviour

All translation rules live in **`app/agent_instructions.py`**. No model fine-tuning needed.

| Section | Variable | What it controls |
|---|---|---|
| Tone & Style | `TONE_INSTRUCTIONS` | Formal/informal, voice, sentence structure |
| Terminology | `TERMINOLOGY_INSTRUCTIONS` | How to handle untranslatable terms, acronyms |
| Formatting | `FORMATTING_INSTRUCTIONS` | Markdown, tables, LaTeX, code blocks |
| By Subject | `SUBJECT_DOMAIN_RULES` | Math, Science, CS, History, Economics overrides |
| By Language | `LANGUAGE_SPECIFIC_RULES` | Script, register, board-specific vocabulary |
| RAG Usage | `RAG_INSTRUCTIONS` | How to use retrieved glossary context |

**Example:** To change the Hindi tone from formal to semi-formal:
```python
LANGUAGE_SPECIFIC_RULES = {
    "hi": """
        - Use a semi-formal tone suitable for high school students.
        - Use 'तुम' form instead of 'आप' for direct address.
    """,
    ...
}
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a document (multipart/form-data) |
| `POST` | `/api/translate` | Translate an uploaded document |
| `GET` | `/api/documents` | List all documents |
| `DELETE` | `/api/documents/<id>` | Delete a document |
| `GET` | `/api/translations` | List translation history |
| `GET` | `/api/translations/<id>` | Get a specific translation |
| `DELETE` | `/api/translations/<id>` | Delete a translation |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/test-connection` | Test Watsonx connection |

### Upload Example (curl)

```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@lecture_notes.pdf" \
  -F "subject_domain=mathematics"
```

### Translate Example (curl)

```bash
curl -X POST http://localhost:5000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": 1,
    "target_language_code": "hi",
    "target_language_name": "Hindi",
    "subject_domain": "mathematics"
  }'
```

---

## 🧠 RAG Architecture

```
Upload PDF/PPTX/DOCX
        │
        ▼
┌─────────────────────┐
│  Document Extractor │  (PyMuPDF / python-pptx / python-docx)
└────────┬────────────┘
         │ text chunks
         ▼
┌─────────────────────┐
│   FAISS Vector Store│◄─── Academic Glossary (NCERT/CBSE/UGC)
│  (sentence-trans.)  │◄─── Curriculum Frameworks (NEP 2020)
└────────┬────────────┘
         │
    [Translation Request]
         │
         ▼
┌─────────────────────────────────────────────┐
│  Query vector store with source text        │
│  → Retrieve top-5 relevant glossary chunks  │
│  → Build RAG context string                 │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│  Build prompt: system_prompt + RAG_context  │
│              + source_text                  │
│  ─────────────────────────────────────      │
│  IBM Watsonx Granite (chat completion)      │
└──────────────────────┬──────────────────────┘
                       │ translated text
                       ▼
                  Saved to DB + returned to UI
```

---

## 🌍 Supported Languages

| Code | Language | Script |
|---|---|---|
| `hi` | Hindi | Devanagari |
| `mr` | Marathi | Devanagari |
| `ta` | Tamil | Tamil |
| `te` | Telugu | Telugu |
| `bn` | Bengali | Bengali |
| `gu` | Gujarati | Gujarati |
| `kn` | Kannada | Kannada |
| `ml` | Malayalam | Malayalam |
| `pa` | Punjabi | Gurmukhi |
| `or` | Odia | Odia |
| `ur` | Urdu | Nastaliq |
| `fr` | French | Latin |
| `de` | German | Latin |
| `es` | Spanish | Latin |
| `ar` | Arabic | Arabic |
| `zh` | Chinese (Simplified) | Han |
| `ja` | Japanese | Kanji/Kana |

---

## 🐳 Docker Deployment (Optional)

```dockerfile
# Dockerfile (create in project root)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "run.py"]
```

```bash
docker build -t translator-agent .
docker run -p 5000:5000 --env-file .env translator-agent
```

---

## ☁️ IBM Cloud Code Engine Deployment

```bash
# Build and push image
ibmcloud ce application create \
  --name translator-agent \
  --image icr.io/your-namespace/translator-agent:latest \
  --port 5000 \
  --env-from-secret watsonx-secrets \
  --min-scale 1
```

---

## 📝 A Note on Model Selection

During development, multiple IBM Granite chat models were evaluated (`ibm/granite-3-3-8b-instruct`, `ibm/granite-3-1-8b-base`) before settling on **`ibm/granite-4-h-small`**, which is the model actively supported and verified working in this Watsonx.ai project environment for chat completion. `meta-llama/llama-3-3-70b-instruct` is used as an automatic fallback in case of quota limits or temporary model unavailability, ensuring the translation pipeline stays functional end-to-end.

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `IBM_API_KEY` | — | IBM Cloud API Key (**required**) |
| `IBM_WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | Watsonx endpoint |
| `IBM_WATSONX_PROJECT_ID` | — | Your Watsonx project ID (**required**) |
| `FLASK_SECRET_KEY` | — | Flask session secret (**required**) |
| `FLASK_ENV` | `development` | `production` for deployment |
| `TRANSLATION_MODEL` | `ibm/granite-4-h-small` | Watsonx model ID |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence transformer model |
| `MAX_CONTENT_LENGTH_MB` | `25` | Max upload file size |
| `VECTOR_STORE_PATH` | `app/data/vector_store` | FAISS index location |

---

## 📋 Requirements

See [`requirements.txt`](requirements.txt) for the full list.

Key dependencies:
- `flask` + `flask-sqlalchemy` — Web framework + ORM
- `ibm-watsonx-ai` — IBM Watsonx SDK
- `sentence-transformers` + `faiss-cpu` — RAG embedding + retrieval
- `PyMuPDF` — PDF text extraction
- `python-pptx` — PowerPoint extraction
- `python-docx` — Word document extraction
- `python-dotenv` — Environment variable management

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/add-language-xx`
3. Add the language to `SUPPORTED_LANGUAGES` in `app/routes/main.py`
4. Add language-specific rules to `LANGUAGE_SPECIFIC_RULES` in `app/agent_instructions.py`
5. Add glossary terms in `app/data/glossaries/academic_glossary.json`
6. Submit a pull request

---

## 📄 License

MIT License — see `LICENSE` for details.

---

*Built with IBM Watsonx.ai · Granite (`granite-4-h-small`) · FAISS · Flask · Bootstrap 5*