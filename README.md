# TribeIQ (EngageIQ) — Co-Living Community Optimization & Operational Intelligence Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Supported-47A248?style=flat&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA_NIM-LLM_Reranking-76B900?style=flat&logo=nvidia&logoColor=white)](https://build.nvidia.com/)

TribeIQ (EngageIQ) is an enterprise-grade co-living community management, executive intelligence, and event optimization platform built with Python, Streamlit, and MongoDB. It bridges real-time demographic analytics, occupancy forecasting, Master Event Planning, vendor procurement, and hybrid machine learning (heuristics combined with Large Language Model reranking via NVIDIA NIM `meta/llama-3.1-8b-instruct`) to maximize resident engagement and operational efficiency.

---

## 🌟 Key Features & Modules

### 1. 🏠 Personal & Executive Dashboard (`pages/1_🏠_Dashboard.py`)
* **Personalized Header**: Dynamic greeting (`👋 Hi, <username>`) for logged-in managers.
* **Actionable Task Manager**: Role-based task management filtering strictly manual Admin-created tasks (excluding template noise), with inline `➕ Add Task (Admin)` form, task assignment dropdowns, and `🗑️` single-click task deletion.
* **Operational Metrics**: Overview of active residents across monitored properties, event completion rates, pending procurement, active vendors, and occupancy timelines.

### 2. 👥 Property Profile & Demographics (`pages/2_👥_Property_Profile.py`)
* **Resident Analytics**: Visual distributions of age bands, gender ratios, tenure (day-level tracking), and professional occupation breakdowns.
* **Property Performance**: Comprehensive metrics per property to tailor engagement strategies to specific resident personas.

### 3. 🎯 Smart Event Recommendation Engine (`pages/3_🎯_Recommendations.py`)
* **Hybrid Reranking Pipeline**: Multi-phase recommendation pipeline matching heuristic candidate generation with LLM reasoning via NVIDIA NIM (`meta/llama-3.1-8b-instruct`).
* **Turnout & Attendance Forecasting**: Predictive modeling for turnout rate, confidence score, estimated budget, and optimal calendar execution dates.

### 4. 📝 Actual Event Logging & Outcome Tracking (`pages/4_📝_Log_Event.py`)
* **Persistent Predictions Sync**: Pick past forecasts from a dropdown to log actual turnout, feedback stars (0–5 rating), and actual budget spent.
* **Hyperlink Extraction**: Parses image/web links in event notes and stores them under dedicated `Image Data` columns.

### 5. 📊 Executive Intelligence & Analytics (`pages/5_📊_Analytics.py`)
* **Dual Dashboard Modes**: Toggle between **👔 Executive Dashboard** (surfacing top KPIs, Operational Health Index, AI Executive Insights, Intelligent Alerts, Budget Variance) and **🎯 Operational Analytics**.

### 6. ⚙️ Warden Settings & Integration (`pages/6_⚙️_Settings.py`)
* **API & System Controls**: Warden REST API sync status, database health checks, synchronization frequencies, and system preferences.

### 7. 🏪 Vendor Management & Procurement (`pages/7_🏪_Vendor_Management.py`)
* **Vendor Database**: Categorized vendor registry with contact management, status tracking, GST tax classification (12% / 18%), and material pricing.

### 8. 📅 Community Calendar (`pages/8_📅_Community_Calendar.py`)
* **Interactive Timeline**: Month-by-month event timeline, date adjustment capabilities, status tagging, and calendar preview exports.

### 9. 🗃️ Master Data Catalogs (`pages/9_🗃️_Master_Data.py`)
* **System Registries**: CRUD management for properties, event categories, material inventory, vendor categories, and external city-wide events.

### 10. 🤖 AI Community Copilot (`pages/10_🤖_AI_Community_Copilot.py`)
* **Conversational AI Assistant**: LLM-powered copilot answering community management queries, budget strategies, and resident engagement tips.

### 11. 👤 User Management & Role Permissions (`pages/11_👤_User_Management.py`)
* **Role-Based Access Control (RBAC)**: Manage platform users with role tiers (`Admin`, `SuperAdmin`, `Community Manager`, `Property Manager`, `Warden`).

### 12. 📋 Master Event Planner (`pages/12_📋_Master_Event_Planner.py`)
* **Workspace Workspace Execution**: Event workspace initialization, AI Risk Checklists, suggested vendor/material resources, Run-of-Show scheduling, and procurement task workflows.

---

## 🛠️ Tech Stack & Architecture

* **Frontend**: Streamlit with custom CSS themes (`ui/styles.py`)
* **Core Language**: Python 3.10+
* **Data Processing**: Pandas, NumPy
* **Data Storage & Persistence**: MongoDB (with automatic local CSV fallbacks: `data/tasks.csv`, `data/event_workspaces.csv`, etc.)
* **AI & LLM Engine**: LangChain, NVIDIA NIM HTTP API (`meta/llama-3.1-8b-instruct`)
* **Export Engines**: OpenPyXL (Excel), CSV

---

## 📂 Project Directory Structure

```
EngageIQ/
├── app.py                          # Streamlit application entry point & sidebar nav
├── HANDOVER.md                     # Comprehensive system handover document
├── README.md                       # Project overview & documentation
├── requirements.txt                # Python dependencies
├── data/                           # Fallback CSV datasets & system registries
│   ├── event_workspaces.csv        # Active event workspace records
│   ├── tasks.csv                   # Task management database
│   ├── run_of_show.csv             # Activity timeline logs
│   ├── planned_calendar.csv        # Scheduled calendar events
│   ├── event_history.csv           # Historical outcome logs
│   └── recommendation_history.csv  # Generated recommendation history
├── pages/                          # Streamlit application modules (1 to 12)
├── src/                            # Core backend logic & services
│   ├── analytics/                  # Executive Analytics aggregation engine
│   ├── auth/                       # Session manager & RBAC permission controls
│   ├── database/                   # MongoDB client & manager
│   ├── intelligence/               # Recommendation generator, forecaster, & AI copilot
│   ├── integrations/               # Eventbrite, Vendor, Stall, & Material DBs
│   ├── models/                     # Pydantic data schemas
│   ├── repositories/               # Data Access Objects (DAOs)
│   └── services/                   # Master Planner & business orchestration services
└── ui/                             # Global styling CSS and custom UI components
```

---

## 🚦 Quick Start & Setup

### 1. Prerequisites
* Python 3.10 or higher installed
* (Optional) MongoDB instance running on `localhost:27017`

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/shriyansh1903/TribeIQ-v1.git
cd TribeIQ-v1

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create a `.env` file in the root directory:
```ini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=engageiq_db
NVIDIA_API_KEY=your_nvidia_nim_api_key
```

### 4. Running the Platform
```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

---

## 🤝 Handover & Further Documentation

For complete technical specifications, database schemas, and service method reference, please refer to [HANDOVER.md](HANDOVER.md).
