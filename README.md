# Autonomous Trade Assistant Agent

A full-stack AI-powered assistant for energy & commodity (gas) trading. This app combines a React frontend with a FastAPI backend using Azure AI Foundry and Databricks Delta Lake for real-time trade insights.

---

## 🔧 Project Structure
# 🧠 Autonomous Trade Agent Assistant

A full-stack AI-powered assistant for front-office gas trading, built using **React**, **FastAPI**, **Azure AI Foundry**, and **Databricks Delta Lake**. The assistant leverages tool-augmented agents to provide real-time trade insights, PnL breakdowns, and other analytics across front, middle, and back-office perspectives.

---

## 📁 Project Structure

```bash
autonomusagents/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── agentfactory.py      # Core logic for AI agent setup (Azure AI Foundry)
│   │   ├── tools.py             # Databricks tools (Delta query, PnL fetch, etc.)
│   │   ├── config.py            # Configurations (uses environment variables)
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx              # UI container
│   │   ├── components/          # Chat + Graph Components
│   │   ├── services/            # API client
│   │   └── utils/
│   └── package.json
│
├── .gitignore
├── README.md
└── .env.example

| Layer       | Technology                          |
| ----------- | ----------------------------------- |
| Frontend    | React.js, Tailwind, Axios           |
| Backend     | FastAPI, Azure Identity, AI Foundry |
| Auth        | Azure AD (frontend)                 |
| LLM Agent   | Azure AI Foundry + Tool Functions   |
| Data Access | Databricks SQL + Delta Tables       |


---
## 🚀 Features
- ✅ AI Agent using Azure AI Foundry
- ✅ Tool-augmented reasoning to query Databricks Delta tables
- ✅ Session-aware `thread_id` management
- ✅ Secure Databricks SQL access with token auth
- ✅ React-based frontend with Azure AD login
- ✅ Real-time trade data analysis: deal structure, volume, PnL, and exposure

---

## 🛠️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/autonomusagents.git
cd autonomusagents

2. Backend Setup
Ensure Python 3.9+ and virtualenv are installed.
cd backend
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt

Set up .env or use app/config.py to configure:
PROJECT_ENDPOINT
DATABRICKS_ACCESS_TOKEN
Other Azure credentials (via DefaultAzureCredential)
uvicorn app.main:app --reload

3. Frontend Setup
Requires Node.js 18+

bash
cd frontend
npm install
npm run dev   # Or: npm run start
The app will be available at http://localhost:3000

Environment Configuration
Add .env files in both backend/ and frontend/ (if needed):

backend/.env
ini
PROJECT_ENDPOINT=https://<your-ai-project>.openai.azure.com
DATABRICKS_ACCESS_TOKEN=...

frontend/.env
ini
VITE_BACKEND_URL=http://localhost:8000
VITE_CLIENT_ID=<azure-ad-client-id>
VITE_TENANT_ID=<azure-tenant-id>

Key Python Dependencies
azure-ai-foundry
fastapi
uvicorn
requests
databricks-sql-connector
Install using:

bash
pip install -r requirements.txt

Trade Tables (Delta Lake)
Used tables (Unity Catalog):

entity_trade_header
entity_trade_leg
entity_trade_profile
entity_pnl_detail

These contain hierarchical trade data for physical and financial gas trading.

Authentication- TBD


Example Use Cases
"What’s the realized PnL for deal 19400?"
"Compare physical vs financial exposure for deal 19400."
"List counterparties with high regulatory exposure this quarter."

Testing
You can use Postman or curl to test backend:

bash
curl http://localhost:8000/agent/prompt -X POST \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user@example.com", "prompt": "What is the PnL for deal 19400?"}'


TODO
 Implement retry logic for Databricks API errors
 Improve tool metadata descriptions
 Add CI/CD (GitHub Actions or Azure Pipelines)

 License
MIT License — © 2025 [Girish Kumar]
---

Let me know if you want it customized further for:
- Project name
- Real GitHub repo link
- Specific tools or endpoints you added

I can also generate a **`requirements.txt`**, `.env.template`, or full API reference if needed.