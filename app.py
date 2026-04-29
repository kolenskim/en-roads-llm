"""Streamlit web UI for the En-ROADS climate scenario tool."""
import os, sys
import streamlit as st

from enroads_core import (
    parse_scenario, build_url, ACTIONS, PRESETS,
    agent_chat, SYSTEM_PROMPT, TOOLS
)

st.set_page_config(page_title="En-ROADS Scenario Builder", page_icon="🌍", layout="wide")
st.title("🌍 En-ROADS Climate Scenario Builder")
st.caption("Translate natural language climate policies into [En-ROADS](https://en-roads.climateinteractive.org/) simulator scenarios")

# --- Load API key from Streamlit secrets ---
api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
model = st.secrets.get("ENROADS_MODEL", "gpt-4o-mini") if hasattr(st, "secrets") else "gpt-4o-mini"
agent_available = bool(api_key)

# --- Sidebar ---
with st.sidebar:
    st.header("📋 Presets")
    preset = st.selectbox("Load a preset scenario", ["(none)"] + list(PRESETS.keys()))
    if agent_available:
        st.divider()
        st.success("✅ AI Advisor is available")
    else:
        st.divider()
        st.info("AI Advisor requires OPENAI_API_KEY in app secrets")

# --- Tabs ---
tab_direct, tab_agent = st.tabs(["📝 Direct Builder", "🤖 AI Advisor"])

# === Direct Builder ===
with tab_direct:
    user_input = st.text_area(
        "Describe your climate scenario in plain English:",
        placeholder='e.g. "ban coal, maximum renewables, high carbon price, plant trees"',
        height=100,
    )
    st.markdown("**Keywords:** tax, subsidize, ban, phase out, encourage · slight, moderate, high, very high, maximum")

    if preset != "(none)":
        params = dict(PRESETS[preset])
        changes = [{"name": a["name"], "param": a["param"], "default": a["default"], "value": params[a["param"]]}
                   for a in ACTIONS if a["param"] in params]
    elif user_input:
        changes = parse_scenario(user_input)
        params = {c["param"]: c["value"] for c in changes}
    else:
        changes, params = [], {}

    if changes:
        st.subheader("📊 Scenario Parameters")
        cols = st.columns(3)
        for i, c in enumerate(changes):
            with cols[i % 3]:
                v = params[c["param"]]
                st.metric(c["name"], f"{v}", f"{v - c['default']:+g} from baseline")
        url = build_url(params)
        st.divider()
        st.subheader("🔗 Open in En-ROADS")
        st.markdown(f"[**Click here to view this scenario in the simulator →**]({url})")
        st.code(url, language=None)
    elif user_input:
        st.warning("No recognized climate actions. Try: coal, renewables, carbon tax, deforestation, electric vehicles")

# === AI Advisor ===
with tab_agent:
    if not agent_available:
        st.info("The AI Advisor requires an OpenAI API key. Add `OPENAI_API_KEY` to this app's Streamlit secrets to enable it.")
    else:
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["ENROADS_MODEL"] = model
        from openai import OpenAI

        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if "display" not in st.session_state:
            st.session_state.display = []

        for msg in st.session_state.display:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask about climate policy, current events, or scenario ideas..."):
            st.session_state.display.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                with st.spinner("Researching and reasoning..."):
                    try:
                        client = OpenAI(api_key=api_key)
                        response = agent_chat(client, st.session_state.messages)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        st.session_state.display.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"Error: {e}")

        if st.button("Clear conversation"):
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.session_state.display = []
            st.rerun()
