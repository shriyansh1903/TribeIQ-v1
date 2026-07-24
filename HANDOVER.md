# TribeIQ (EngageIQ) — Project Handover & System Architecture Document

**System Version:** v1.2  
**Date:** July 24, 2026  
**Repository:** `shriyansh1903/TribeIQ-v1`  
**Platform:** Streamlit / Python 3.10+ / MongoDB / Pandas  

---

## 📋 Executive Overview

TribeIQ (EngageIQ) is an intelligent co-living community management and event recommendation platform built for property managers, community wardens, and executive stakeholders. It combines real-time resident demographical profiling, occupancy forecasting, Master Event Planning, Eventbrite integration, and continuous-learning feedback loops.

---

## 🏗️ Core Architecture & Component Map

### 1. Application Layer (`pages/`)
* **`1_🏠_Dashboard.py`**: Personal dashboard greeting (`👋 Hi, <username>`), actionable manual task management (Admin task creation, status updates, deletion, task assignment without template noise), occupancy metrics, and operational quick links.
* **`2_👥_Property_Profile.py`**: Demographical profiling, resident age distributions, tenure metrics, and occupation breakdowns per property.
* **`3_🎯_Recommendations.py`**: Smart recommendation engine powered by heuristic rules and LLM re-ranking via NVIDIA NIM (`meta/llama-3.1-8b-instruct`).
* **`4_📝_Log_Event.py`**: Outcome logging for actual event turnouts, ratings, notes, and Google Drive image link extractions.
* **`5_📊_Analytics.py`**: Dual-mode analytics workspace (Executive Intelligence Dashboard & Operational Analytics breakdown).
* **`6_⚙️_Settings.py`**: Warden settings, REST API configurations, theme settings, and data sync frequency controls.
* **`7_🏪_Vendor_Management.py`**: Vendor database, category filters, contact details, GST classifications, and procurement logs.
* **`8_📅_Community_Calendar.py`**: Event scheduling, date adjustments, status tagging, and month-level timeline previews.
* **`9_🗃️_Master_Data.py`**: Management of properties, event categories, external events, vendor types, and material catalogs.
* **`12_📋_Master_Event_Planner.py`**: Detailed event workspaces, AI planning assistant insights, risk checklists, vendor procurement tracking, Run-of-Show schedules, and task delegation.

### 2. Backend Services & Repositories (`src/`)
* **`src/analytics/executive_analytics.py`**: Aggregates top-level executive KPIs, composite Operational Health Scores, AI insights, intelligent alerts, budget variance, and department productivity scores.
* **`src/services/master_planner_service.py`**: Central orchestration service for event workspaces, task lifecycle management, workspace metadata auto-recalculation, and Run-of-Show management.
* **`src/auth/session_manager.py`**: Authentication handling, session persistence, role permissions (`Admin`, `SuperAdmin`, `Community Manager`, `Property Manager`, `Warden`), and login enforcement.
* **`src/integrations/eventbrite/`**: Eventbrite integration for events, orders, attendees repositories, and auto-sync schedulers.
* **`src/database/mongodb.py` & `src/database/db_manager.py`**: MongoDB database connection manager with automatic CSV file fallback.

---

## 🔑 Key Recent Enhancements & Bug Fixes

1. **Dashboard Personalization & Header Update**:
   - Header updated to dynamically display `👋 Hi, <username>` based on the logged-in session.
2. **Actionable Tasks & Admin Controls**:
   - **Filtered Task Summary**: Actionable tasks widget on the dashboard strictly filters to show manual admin-created tasks, excluding auto-filled event workspace template clutter.
   - **Admin Task Creation**: Added `➕ Add Task (Admin)` inline form on the dashboard with department, due date, and user assignment options.
   - **Task Deletion**: Added individual `🗑️` delete buttons for Admins with instant cascade cleanup in MongoDB and local data storage.
   - **Robust Fallbacks**: Fixed `workspace_id` and `event_id` handling for general administrative tasks (`GENERAL_OPERATIONS`) to prevent `KeyError` exceptions.
3. **Executive Analytics Engine Bug Fix**:
   - Resolved `'Series' object has no attribute 'lower'` error in `executive_analytics.py` by converting pandas Series calls to string accessor `.str.lower()`.
4. **Dual Data Persistence**:
   - Unified MongoDB storage with zero-downtime fallback to CSV data files (`data/tasks.csv`, `data/event_workspaces.csv`, `data/run_of_show.csv`, etc.).

---

## 🛠️ Data Storage Schema & Directory Layout

```
EngageIQ/
├── app.py                          # Streamlit application entry point
├── HANDOVER.md                     # System handover document
├── README.md                       # Project documentation
├── data/                           # Data storage (CSV fallback & seed data)
│   ├── event_workspaces.csv        # Event workspace records
│   ├── tasks.csv                   # Task management records
│   ├── run_of_show.csv             # Workspace activity timelines
│   ├── planned_calendar.csv        # Calendar schedule logs
│   ├── event_history.csv           # Historical event turnout logs
│   └── recommendation_history.csv  # Generated recommendation logs
├── pages/                          # Streamlit page modules (1-12)
├── src/                            # Backend python packages
│   ├── analytics/                  # Executive aggregation & KPIs
│   ├── auth/                       # Authentication & session state
│   ├── database/                   # MongoDB client & manager
│   ├── integrations/               # Eventbrite, Vendor, Stall & Material DBs
│   ├── models/                     # Pydantic data schemas
│   ├── repositories/               # Data access objects (DAOs)
│   └── services/                   # Business domain orchestration services
└── ui/                             # Global styling CSS and reusable components
```

---

## 🚀 Operations & Deployment Guide

### Local Development Setup
1. **Activate Virtual Environment**:
   ```bash
   .venv\Scripts\activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Launch Application**:
   ```bash
   streamlit run app.py
   ```

### MongoDB Environment Configuration (`.env`)
```ini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=engageiq_db
NVIDIA_API_KEY=your_nvidia_nim_api_key
```

---

## 📌 Pending & Recommended Next Steps

1. **User Notification System**: Implement real-time in-app notifications when an Admin assigns a task to a Community Manager.
2. **Eventbrite Webhook Handler**: Add webhook listener endpoints for instant registration updates from Eventbrite.
3. **Role-Based Task Filters**: Add quick filter toggles on the Master Event Planner page to filter tasks by department (`Procurement`, `Marketing`, `Operations`).

---
*Handover Document updated and verified.*
