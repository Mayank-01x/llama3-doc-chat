import streamlit as st
import requests

API_URL = "http://localhost:8000/api"

st.set_page_config(page_title="AI Doc Q&A", layout="wide")

st.title("🤖 AI Document Q&A")

st.info("ℹ️ If the app just started, wait a few seconds for backend to load.")

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar upload
with st.sidebar:
    st.header("📄 Upload Document")

    uploaded_file = st.file_uploader(
        "Upload PDF, DOCX, TXT, MD",
        type=["pdf", "docx", "txt", "md"]
    )

    if uploaded_file:
        with st.spinner("Processing document..."):
            try:
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue())
                }
                res = requests.post(f"{API_URL}/upload", files=files)

                if res.status_code == 200:
                    st.success(res.json().get("message"))
                else:
                    st.error("Upload failed")

            except requests.exceptions.ConnectionError:
                st.error("🚫 Backend not ready. Please wait a few seconds.")
                st.stop()

    st.markdown("---")
    st.caption("Powered by LLaMA 3 + RAG")

# Chat UI
st.subheader("💬 Ask Questions")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask something about your document..."):

    # User message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # Assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    f"{API_URL}/query",
                    json={"question": prompt}
                )

                data = res.json()
                answer = data.get("answer", "No response")

                # Simulated streaming
                for chunk in answer.split():
                    full_response += chunk + " "
                    message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)

                # Sources
                if data.get("sources"):
                    with st.expander("📚 Sources"):
                        for src in data["sources"]:
                            st.write(src)

            except requests.exceptions.ConnectionError:
                full_response = "🚫 Backend not available. Please start the server."
                message_placeholder.markdown(full_response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response
    })