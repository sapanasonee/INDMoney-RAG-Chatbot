# Mutual Fund Chatbot New

**Milestone 1:** Facts-only FAQ assistant for 5 specific schemes. No advice; citations required; max 3 sentences per answer.

## Tech Stack

- **Backend:** FastAPI, ChromaDB, LangChain  
- **Frontend:** React (Vite), Tailwind CSS  

## Project Layout

```
/
├── .cursorrules          # No-advice + citation rules for code generation
├── backend/
│   ├── main.py           # FastAPI app + CORS
│   ├── requirements.txt
│   └── app/
├── frontend/             # Vite + React + Tailwind
│   ├── .env.production   # VITE_API_URL placeholder
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
└── README.md
```

## Approved Schemes (5)

1. HDFC Small Cap Fund  
2. HDFC Flexi Cap Fund  
3. SBI Contra Fund  
4. HDFC ELSS Tax Saver  
5. Parag Parikh Flexi Cap  

## Official Source URLs (12)

All answers must cite only from this list. Use these for RAG ingestion and response citations.

### HDFC Small Cap Fund
1. **Scheme overview (Regular)**  
   https://www.hdfcfund.com/product-solutions/overview/hdfc-small-cap-fund/regular  

2. **Scheme Information Document (SID) PDF**  
   https://files.hdfcfund.com/s3fs-public/SID/2025-05/SID%20-%20HDFC%20Small%20Cap%20Fund%20dated%20May%2030,%202025.pdf  

### HDFC Flexi Cap Fund
3. **Scheme page (Regular)**  
   https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/regular  

4. **Fund Facts PDF**  
   https://files.hdfcfund.com/s3fs-public/Others/2025-05/Fund%20Facts%20-%20HDFC%20Flexi%20Cap%20Fund_May%2025.pdf

### SBI Contra Fund
5. **Scheme details**  
   https://www.sbimf.com/sbimf-scheme-details/sbi-contra-fund-12  

6. **Scheme Information Document (SID) PDF**  
   https://www.sbimf.com/docs/default-source/lists/sid---sbi-contra-fund8ce474c1a5404a2b899f14f6f21a95dd.pdf  

7. **Fact sheet**  
   https://www.sbimf.com/docs/default-source/scheme-factsheets/sbi-contra-fund-factsheet-june-2025.pdf  
   *(Update filename if SBI publishes a new dated factsheet.)*

### HDFC ELSS Tax Saver
8. **Scheme page (Regular)**  
   https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/regular  

### Parag Parikh Flexi Cap
9. **Scheme landing page**  
   https://amc.ppfas.com/pltvf/  

10. **Key highlights of the scheme**  
    https://amc.ppfas.com/schemes/key-highlights-of-the-scheme/index.php  

11. **SID (Parag Parikh Flexi Cap Fund)**  
    https://amc.ppfas.com/downloads/parag-parikh-flexi-cap-fund/SID_PPFCF.pdf  
    *(Check AMC downloads page if link moves.)*

### AMFI (reference / NAV)
12. **AMFI India**  
    https://www.amfiindia.com  

---

## Run locally

**Backend** (runs on **port 8001** to avoid conflict with other apps on 8000)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```
Or from `backend/`: run **`run_backend.bat`** (Windows) or **`./run_backend.sh`** (Mac/Linux).
Set `GOOGLE_API_KEY` in `backend/.env` or the environment for the `/chat` endpoint (Gemini). The vector store is preloaded at startup so the first chat is fast.

**Phase 1 Ingestion (scraper)**  
From `backend/`, install Playwright browsers once, then run the scraper:
```bash
cd backend
playwright install chromium
python scraper.py
```
Output: `backend/data/processed_schemes.json` (scheme facts and how-to steps with `source_url` for citations).

**Phase 2 Vector Search**  
From `backend/`, build the ChromaDB index (run after Phase 1):
```bash
cd backend
python vector_store.py
```
Optional: `python vector_store.py --rebuild` to clear and re-index. Index is stored at `backend/data/chroma_db/`.  
*If you see ChromaDB/Pydantic errors, use Python 3.11 or 3.12 for the backend.*

**Chat API**  
Set `GOOGLE_API_KEY` in `backend/.env` or the environment for the `/chat` endpoint (Gemini). Without it, `POST /chat` returns 503.

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL` in `frontend/.env.production` (or `.env.local` for dev) to your backend base URL for production builds.
