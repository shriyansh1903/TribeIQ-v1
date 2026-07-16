import streamlit as st
import time
from intelligence.copilot_orchestrator import ask_copilot
from ui.styles import load_css

st.set_page_config(
    page_title="TribeIQ - AI Community Copilot",
    page_icon="🤖",
    layout="wide"
)

load_css()

st.title("🤖 AI Community Copilot")
st.write("Ask operational questions about properties, attendance history, budgets, vendors, or request next month's community schedule planning.")

# Chat history initialization
if "copilot_chat_history" not in st.session_state:
    st.session_state["copilot_chat_history"] = []

# Suggested Prompts
suggested_prompts = [
    "Which event category has the highest attendance?",
    "What events generated the highest revenue?",
    "Which vendors perform best?",
    "Show property directory and capacities.",
    "Recommend planned calendar schedule overview."
]

st.write("#### 💡 Suggested Prompts")
cols_prompts = st.columns(len(suggested_prompts))
clicked_prompt = None

for idx, prompt_text in enumerate(suggested_prompts):
    with cols_prompts[idx]:
        if st.button(prompt_text, key=f"sugg_{idx}", use_container_width=True):
            clicked_prompt = prompt_text

st.write("---")

# Render chat history
for msg in st.session_state["copilot_chat_history"]:
    role_icon = "👤" if msg["role"] == "user" else "🤖"
    role_name = "You" if msg["role"] == "user" else "Copilot"
    
    with st.chat_message(msg["role"]):
        st.markdown(f"**{role_name}**")
        st.write(msg["content"])
        
        # Check for smart action tokens
        content = msg["content"]
        if "[ACTION: recommendations]" in content:
            st.markdown("[🎯 Launch Smart Recommendations](Smart_Recommendations)")
        if "[ACTION: calendar]" in content:
            st.markdown("[📅 Open Community Calendar](Community_Calendar)")
        if "[ACTION: vendors]" in content:
            st.markdown("[🏪 Open Vendor Management](Vendor_Management)")
        if "[ACTION: analytics]" in content:
            st.markdown("[📊 Open Analytics](Analytics)")

# Input
user_query = st.chat_input("Ask the TribeIQ Copilot...")

# If clicked suggested prompt
if clicked_prompt:
    user_query = clicked_prompt

if user_query:
    # 1. User Message
    st.session_state["copilot_chat_history"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown("**You**")
        st.write(user_query)
        
    # 2. Copilot Response (with typing simulation spinner)
    with st.chat_message("assistant"):
        st.markdown("**Copilot**")
        with st.spinner("AI Community Copilot is thinking..."):
            # Call orchestrator
            response = ask_copilot(user_query, st.session_state["copilot_chat_history"])
            
            # Simulated typing delay
            time.sleep(0.8)
            
            st.write(response)
            
            # Check and display interactive smart actions links
            if "[ACTION: recommendations]" in response:
                st.markdown("[🎯 Launch Smart Recommendations](Smart_Recommendations)")
            if "[ACTION: calendar]" in response:
                st.markdown("[📅 Open Community Calendar](Community_Calendar)")
            if "[ACTION: vendors]" in response:
                st.markdown("[🏪 Open Vendor Management](Vendor_Management)")
            if "[ACTION: analytics]" in response:
                st.markdown("[📊 Open Analytics](Analytics)")
                
            st.session_state["copilot_chat_history"].append({"role": "assistant", "content": response})
            st.rerun()

st.write("")
if st.button("🧹 Clear Chat History", key="clear_chat"):
    st.session_state["copilot_chat_history"] = []
    st.rerun()
