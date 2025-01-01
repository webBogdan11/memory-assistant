import streamlit as st
import sys
import os


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root)


def main():
    """
    Entrypoint for the Streamlit multipage app.
    Uses st.Page to define the two pages: Library and Detail.
    """

    document_library_page = st.Page(
        "pages/document_liabrary.py",
        title="Document Library",
        default=True,
    )
    document_detail_page = st.Page(
        "pages/document_detail.py",
        title="Document Detail",
    )
    chat_page = st.Page(
        "pages/chat.py",
        title="Chat",
    )

    page = st.navigation(
        [document_library_page, document_detail_page, chat_page], position="hidden"
    )
    page.run()


if __name__ == "__main__":
    print(project_root)
    main()
