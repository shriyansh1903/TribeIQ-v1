# TribeIQ: Co-Living Community Optimization & Recommendation Engine

TribeIQ is an intelligent, data-driven co-living community management and event recommendation platform built with Python and Streamlit. It leverages real-time demographical analytics, occupancy forecasting, and hybrid machine learning models (combining heuristics and Large Language Model reranking via NVIDIA NIM) to help property managers optimize resident engagement and maximize event attendance.

---

## 🚀 Key Features

### 1. Unified Dashboard
* **Dynamic Property Metrics**: Instantly review total active residents, bed capacity, current occupancy rate, average resident tenure (in days), and average event feedback rating.
* **Database Management**: Integrated drag-and-drop file uploader in the sidebar to upload a new `Residents.csv` spreadsheet, validate columns, and automatically run cleaning and profiling pipelines.
* **Timezone Consistency**: Powered by robust Indian Standard Time (IST, UTC+5:30) date handling to prevent ±1% to 2% date offsets due to server UTC time differences.

### 2. Property Profiles & Demographics
* **Resident Analytics**: Deep-dive charts showing age distributions, gender ratios, dominant age bands, and occupation breakdowns.
* **Tenure Metrics**: Track how long residents are staying with precise day-level tenure tracking.

### 3. Smart Event Recommendations
* **Hybrid Reranking Engine**: Utilizes local rules combined with the high-performance **`meta/llama-3.1-8b-instruct`** model over NVIDIA NIM to rank event candidates.
* **Execution Forecasting**: Predicts active residents, turnout rates, attendance counts, and confidence scores for suggested events.
* **What-If Date Simulation**: Test event predictions on any target date or forecast the best execution dates for a specific calendar month.

### 4. Persistent Predictions & Outcome Logging
* **Prediction History (`data/predictions_history.csv`)**: Every recommendation or forecast generated is saved persistently to disk.
* **Dropdown Selection**: Pick a previously generated forecast from a dropdown list to log outcomes, auto-filling all forecast parameters in the form.
* **Automated Turnout Calculation**: Turnout rate percentage is automatically calculated as `(Actual Attendee Count / Total Active Residents) * 100` on form submission.
* **Feedback Stars Selectbox**: Visually select satisfaction scores from 0 to 5 stars (supporting quarter, half, and full stars).
* **Hyperlink Detection**: Automatically parses Google Drive or web hyperlinks inside the **Notes** box and saves them to a dedicated **`Image Data`** column.

### 5. Analytics & History Management
* **Interactive Reporting**: Visualize historical event performance, turnout rates, and satisfaction metrics over time.
* **Excel Export**: Download the entire event history database as an Excel spreadsheet (`.xlsx`) at any time.
* **Danger Zone Operations**: Selectively delete a single event log or completely clear all event history with built-in safety checkboxes.

---

## 🛠️ Tech Stack & Architecture

* **Frontend Framework**: Streamlit (with customized CSS templates to preserve sidebar responsiveness)
* **Data Processing**: Pandas, NumPy
* **LLM Engine**: LangChain, NVIDIA NIM HTTP API (`meta/llama-3.1-8b-instruct` - optimized for sub-20 second response times)
* **Excel Engine**: OpenPyXL

---

## 📂 Project Directory Structure

```
TribeIQ/
├── app.py                      # Main landing page & database uploader shell
├── data/                       # Principal datasets
│   ├── Residents.csv           # Resident database
│   ├── event_history.csv       # Outcome logs database
│   └── predictions_history.csv # Persistent prediction history database
├── outputs/                    # Processed pipeline exports
├── pages/                      # Streamlit application subpages
│   ├── 1_🏠_Dashboard.py
│   ├── 2_👥_Property_Profile.py
│   ├── 3_🎯_Recommendations.py
│   ├── 4_📝_Log_Event.py
│   └── 5_📊_Analytics.py
├── src/                        # Core backend intelligence
│   ├── feature_engineering.py  # Resident profiling calculations
│   ├── profile_generator.py    # Demographical profile builds
│   ├── intelligence/           # LLM, recommendations, & forecasters
│   └── learning/               # Continuous-learning feedback loop
├── ui/                         # Global styling and reusable components
└── test_*.py                   # Validation and integration test suite
```

---

## 🏁 Getting Started

### 1. Installation & Environment Setup
Clone the repository and install dependencies inside a Python virtual environment:
```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. API Credentials
Create a `.env` file in the root directory and add your NVIDIA API key to enable LLM-based event ranking:
```env
NVIDIA_API_KEY=your_nvidia_nim_api_token_here
```

### 3. Run the Application
Launch the Streamlit server locally:
```bash
streamlit run app.py
```

---

## 🧪 Running Tests
Verify database cleaning, profiling, LLM connections, forecasting, and UI data-bridge calculations:
```powershell
python test_page_imports.py
python test_frontend_backend_integration.py
python test_occupancy_attendance.py
```
