import streamlit as st
import openai


# hide_pages(["main_UI.py"])
# CSS for the custom box
css = """
<style>
    .custom-box {
        background-color: #AFEEEE;  /* Teal background color for the message box */
        color: #000000;  /* Black text color */
        padding: 20px;  /* Padding inside the message box */
        margin-top: 20px;  /* Margin above the message box */
        margin-bottom: 5px;  /* Smaller bottom margin for visual separation from the input box */
        border-radius: 10px;  /* Rounded corners for the message box */
        height: 500px;
        width: 700px;
        overflow: scroll;
    }
    .stTextInput, .stButton {
        margin-top: -20px;  /* Negative margin to pull the message box up closer */
    }
</style>
"""

# Inject CSS with Markdown for styling
st.markdown(css, unsafe_allow_html=True)
st.title("💵FinGPT")

# Title and content within a custom styled box
st.markdown(f"""
    <div class="custom-box">
        Welcome to FinGPT! Feel free to ask any investment questions you have and relax—we're here to guide you every step of the way!
            
        {"".join(f'<p><b>{msg["role"]}:</b> {msg["content"]}</p>' for msg in st.session_state.get("messages", []))}
    </div>
""", unsafe_allow_html=True)


# Initialize session state for messages if not present
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if st.session_state["messages"]:
    st.markdown(
        "<div class=\"message-box\">" +
        "".join(f"<p><b>{msg['role']}:</b> {msg['content']}</p>" for msg in st.session_state["messages"]) +
        "</div>", unsafe_allow_html=True
    )

# Handle chat input and response using OpenAI
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Handle chat input and response using OpenAI
if prompt := st.chat_input():
    openai_api_key = st.secrets["openai_api_key"]  # Assuming the API key is securely stored
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    client = openai(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=st.session_state.messages)
    msg = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)
