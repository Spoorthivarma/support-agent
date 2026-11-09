"""
Optional web chat UI for the same agent.  Run:  streamlit run app.py
Shows the tool calls the agent makes, so you can SEE it thinking and acting.
"""

import streamlit as st

from agent import SYSTEM_PROMPT, run_agent

st.set_page_config(page_title="ShopEasy Support Agent", page_icon="🛍️")
st.title("🛍️ ShopEasy Support Agent")
st.caption("Try: “Where is order 1001?” · “Can I cancel 1003?” · “My earbuds from 1001 arrived broken”")

# Conversation memory lives in the browser session
if "memory" not in st.session_state:
    st.session_state.memory = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.chat = []  # (role, text, tool_steps) for display

for role, text, steps in st.session_state.chat:
    with st.chat_message(role):
        for s in steps:
            st.info(s)
        st.write(text)

if prompt := st.chat_input("Ask about your order..."):
    st.session_state.chat.append(("user", prompt, []))
    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.memory.append({"role": "user", "content": prompt})
    steps = []
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            answer = run_agent(st.session_state.memory, on_step=steps.append)
        for s in steps:
            st.info(s)
        st.write(answer)
    st.session_state.chat.append(("assistant", answer, steps))
