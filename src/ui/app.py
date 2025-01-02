import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from hmac import compare_digest
from config import settings

def check_password():
    def password_entered():
        if compare_digest(st.session_state["password"], settings.PASSWORD):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect")
    return False


def main():
    """
    Entrypoint for the Streamlit multipage app.
    Uses st.Page to define the two pages: Library and Detail.
    """

    document_library_page = st.Page(
        "ui_pages/document_liabrary.py",
        title="Document Library",
        default=True,
    )
    document_detail_page = st.Page(
        "ui_pages/document_detail.py",
        title="Document Detail",
    )
    chat_page = st.Page(
        "ui_pages/chat.py",
        title="Chat",
    )

    page = st.navigation(
        [document_library_page, document_detail_page, chat_page], position="hidden"
    )
    page.run()


if __name__ == "__main__":
    if not check_password():
        st.stop()

    main()
