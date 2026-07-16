import pandas as pd
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Database imports
from integrations.vendor_db import load_vendors
from integrations.stall_db import load_stalls
from integrations.material_db import load_materials
from integrations.calendar_db import load_calendar_events
from integrations.master_data_db import get_properties_df
from intelligence.llm_client import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def build_system_state_context() -> Dict[str, Any]:
    # 1. Properties
    df_prop = get_properties_df()
    properties_summary = []
    if not df_prop.empty:
        properties_summary = df_prop[["Property Name", "Property Type", "Capacity", "City", "Status"]].to_dict(orient="records")
        
    # 2. Event History
    history_csv = PROJECT_ROOT / "data" / "event_history.csv"
    history_summary = {}
    if history_csv.exists():
        try:
            df_hist = pd.read_csv(history_csv)
            if not df_hist.empty:
                history_summary = {
                    "total_events_conducted": len(df_hist),
                    "average_turnout_rate": f"{df_hist['Attendance %'].mean():.1f}%" if "Attendance %" in df_hist.columns else "N/A",
                    "average_feedback_rating": f"{df_hist['Average Feedback'].mean():.2f}/5" if "Average Feedback" in df_hist.columns else "N/A",
                    "top_categories": df_hist.groupby("Category")["Attendance %"].mean().sort_values(ascending=False).head(3).to_dict() if "Category" in df_hist.columns and "Attendance %" in df_hist.columns else {},
                    "recent_events": df_hist.tail(5)[["Date", "Property", "Event Name", "Category", "Attendance %"]].to_dict(orient="records")
                }
        except Exception:
            pass
            
    # 3. Vendors
    df_vend = load_vendors()
    vendor_summary = []
    if not df_vend.empty:
        vendor_summary = df_vend.head(5)[["Vendor Name", "Category", "Average Rating", "Total Spend"]].to_dict(orient="records")
        
    # 4. Stalls
    df_stalls = load_stalls()
    stall_summary = {
        "total_stalls": len(df_stalls) if not df_stalls.empty else 0,
        "total_revenue": float(df_stalls["Rental Amount"].sum()) if not df_stalls.empty and "Rental Amount" in df_stalls.columns else 0.0
    }
    
    # 5. Materials
    df_mats = load_materials()
    material_summary = {
        "total_spend": float(df_mats["Total Cost"].sum()) if not df_mats.empty and "Total Cost" in df_mats.columns else 0.0,
        "categories": df_mats["Category"].unique().tolist() if not df_mats.empty and "Category" in df_mats.columns else []
    }
    
    # 6. Calendar
    df_cal = load_calendar_events()
    calendar_summary = []
    if not df_cal.empty:
        calendar_summary = df_cal.head(5)[["Date", "Property", "Event Name", "Status", "Event Type"]].to_dict(orient="records")
        
    return {
        "properties": properties_summary,
        "history": history_summary,
        "vendors": vendor_summary,
        "stalls": stall_summary,
        "materials": material_summary,
        "calendar": calendar_summary
    }

def ask_copilot(query: str, chat_history: List[Dict[str, str]]) -> str:
    client = create_client()
    if client is None:
        return "NVIDIA API Key is not configured in Settings or .env file. Please check connection."
        
    system_context = build_system_state_context()
    
    system_prompt = f"""
You are the AI Community Copilot for TribeIQ.
Your role is to act as an executive-level assistant answering questions from the community team using the provided system data.

SYSTEM CURRENT STATE DATA:
{json.dumps(system_context, indent=2)}

Rules:
1. Always base your answers strictly on the SYSTEM CURRENT STATE DATA.
2. If data is unavailable, clearly state: "The requested data is currently not loaded in the TribeIQ databases."
3. Never fabricate or hallucinate metrics.
4. Keep responses concise, professional, and executive-friendly. Use bullet points for comparisons.
5. If the user wants to take action (e.g. "Create a recommendation", "Plan next month's calendar", "Show vendor", "Show analytics"), add a short, clear hint at the end like: "[ACTION: recommendations]", "[ACTION: calendar]", "[ACTION: vendors]", or "[ACTION: analytics]" so the UI can render helper links.
"""

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    # Add recent history context
    for msg in chat_history[-6:]:
        messages.append(msg)
    messages.append({"role": "user", "content": query})
    
    try:
        payload = {
            "model": client.model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.2,
            "top_p": 0.9,
            "stream": False
        }
        import requests
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {client.api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=45
        )
        if response.status_code == 200:
            res_data = response.json()
            return res_data["choices"][0]["message"]["content"]
        else:
            return f"Error communicating with AI model: HTTP {response.status_code}. {response.text[:200]}"
    except Exception as e:
        return f"Request failed: {e}"
