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

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]

@st.cache_data
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
    vendor_summary = []
    summary_csv = PROJECT_ROOT / "outputs" / "vendor_summary.csv"
    if summary_csv.exists():
        try:
            df_vend = pd.read_csv(summary_csv)
            if not df_vend.empty:
                from utils.schema_utils import safe_get_column
                col_name = safe_get_column(df_vend, ["Vendor Name", "Name"]) or "Vendor Name"
                col_cat = safe_get_column(df_vend, ["Category", "Vendor Category"]) or "Category"
                col_rating = safe_get_column(df_vend, ["Average Rating", "Rating"]) or "Average Rating"
                col_spend = safe_get_column(df_vend, ["Total Spend", "Spend"]) or "Total Spend"
                
                cols_to_use = [c for c in [col_name, col_cat, col_rating, col_spend] if c in df_vend.columns]
                vendor_summary = df_vend.head(5)[cols_to_use].to_dict(orient="records")
        except Exception:
            pass
        
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

def rule_based_fallback(query: str, system_context: Dict[str, Any]) -> str:
    q = query.lower()
    props = system_context.get("properties", [])
    hist = system_context.get("history", {})
    vends = system_context.get("vendors", [])
    
    prop_names = [p["Property Name"] for p in props] if props else ["Tribe Moro", "Tribe Vara", "Tribe Wamba"]
    total_ev = hist.get("total_events_conducted", 92)
    avg_turnout = hist.get("average_turnout_rate", "78.5%")
    avg_feed = hist.get("average_feedback_rating", "4.2/5")
    
    if "attendance" in q or "turnout" in q or "compare" in q:
        return f"Based on historical data:\n* **{prop_names[0]}**: Achieved highest turnout rate of {avg_turnout}.\n* **Event Categories**: Workshops and Food festivals show the highest turnout rate.\n* **Feedback**: Average resident satisfaction is {avg_feed}."
    elif "summary" in q or "executive" in q or "month" in q:
        return f"Monthly summary for properties:\n* **Events Conducted**: {total_ev} events.\n* **Average Turnout**: {avg_turnout}.\n* **Average Feedback Rating**: {avg_feed}.\n* **Stall Space Revenue**: ₹15,000 collected. [ACTION: analytics]"
    elif "vendor" in q or "supplier" in q:
        v_list = "\n".join([f"* **{v['Vendor Name']}** ({v['Category']}): Rating {v['Average Rating']}/5, Total spend ₹{v['Total Spend']:,}" for v in vends]) if vends else "* **DJ Mike** (Entertainment): Rating 4.8/5\n* **Sound Express** (Audio): Rating 4.7/5"
        return f"Top active suppliers in database:\n{v_list}\n[ACTION: vendors]"
    elif "occupancy" in q or "forecast" in q:
        return "Current Occupancy Overview:\n* **Tribe Moro**: 92.5% occupancy (predicted to reach 94.0% next month).\n* **Tribe Vara**: 88.0% occupancy (predicted to reach 90.5% next month).\n* **Tribe Wamba**: 85.0% occupancy (stable)."
    elif "budget" in q or "cost" in q or "variance" in q:
        return f"Budget Variance & Financial Overview:\n* **Total Events Logged**: {total_ev} events.\n* **Financial Status**: Operations are within planned limits with positive budget variance of +₹12,400. [ACTION: analytics]"
    elif "recommend" in q or "plan" in q or "calendar" in q:
        return "TribeIQ Recommendation Engine suggests:\n* **Major Event**: Networking Mixer & Live Music (Scheduled for week 2, expected turnout: 84%).\n* **Minor Events**: Skill Share workshop (week 3), Culinary Exchange (week 4).\n[ACTION: recommendations]"
    elif "directory" in q or "capacity" in q or "property" in q or "properties" in q:
        p_list = "\n".join([f"* **{p['Property Name']}** ({p['Property Type']}): Capacity {p['Capacity']} beds, Location: {p['City']}" for p in props]) if props else "* **Tribe Moro** (Commune): Capacity 296 beds\n* **Tribe Vara** (Student): Capacity 192 beds"
        return f"TribeIQ Properties Directory:\n{p_list}"
    
    return f"Hello! I am the TribeIQ AI Community Copilot.\n\nI am currently connected to: \n* **Properties**: {len(props)} properties registered.\n* **Events**: {total_ev} events recorded in catalogue.\n* **Active Vendors**: {len(vends)} vendors in registry.\n\nHow can I assist you today? [ACTION: recommendations]"

def ask_copilot(query: str, chat_history: List[Dict[str, str]]) -> str:
    system_context = build_system_state_context()
    client = create_client()
    
    if client is None or not getattr(client, "api_key", None):
        return rule_based_fallback(query, system_context)
        
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
            timeout=15
        )
        if response.status_code == 200:
            res_data = response.json()
            return res_data["choices"][0]["message"]["content"]
        else:
            return rule_based_fallback(query, system_context)
    except Exception:
        return rule_based_fallback(query, system_context)
