import streamlit as st
import uuid
from typing import Dict, Any

from src.models.book import BookDocument
from src.services.book_service import get_book_service

st.set_page_config(page_title="Document Library", page_icon=":books:")

if "documents" not in st.session_state:
    st.session_state["documents"] = []

st.title("Document Library")

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
book_service = get_book_service()

col_file, col_title = st.columns([0.6, 0.4])
with col_file:
    uploaded_file = st.file_uploader(
        "Select a PDF file", type=["pdf"], label_visibility="collapsed"
    )
with col_title:
    custom_title = st.text_input("Document Title", "")

upload_button = st.button("Upload Document")

if upload_button:
    if not uploaded_file:
        st.warning("Please select a PDF file to upload.")
    elif not custom_title.strip():
        st.warning("Please provide a valid document title.")
    else:
        try:
            file_data = uploaded_file.read()
            new_doc = book_service.upload_book(
                file_data=file_data,
                title=custom_title.strip(),
                type="pdf",
                user_id=DEMO_USER_ID,
            )

            st.success(f"Successfully uploaded “{custom_title}”!")
        except ValueError as ve:
            st.error(f"Upload failed: {ve}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

st.write("---")

all_books = book_service.get_books_by_user_id(user_id=DEMO_USER_ID)

# --- Documents List / Library ---
if len(all_books) == 0:
    st.info("No documents uploaded yet. Upload a PDF to get started!")
    st.stop()

# Search / Filter (simple approach)
search_query = st.text_input("Search by title", "")


# Filter docs by search query
def matches_search(doc: BookDocument, query: str) -> bool:
    return query.lower() in doc.title.lower()


filtered_docs = [doc for doc in all_books if matches_search(doc, search_query)]

st.write(f"### Documents ({len(filtered_docs)})")
if not filtered_docs:
    st.warning("No documents match your search.")
    st.stop()

# Display each document as a card or row
for doc in filtered_docs:
    with st.expander(f"**{doc.title}**", expanded=False):
        st.write(f"**Date Uploaded:** {doc.created_at}")
        st.write(f"**Pages:** {doc.metadata.pages}")
        st.write(f"**Size:** {doc.metadata.doc_size} MB")
        # st.write(
        #     f"**Sections Detected:** {doc['metadata'].get('sections_detected', 'N/A')}"
        # )

        # Quick action buttons
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("View / Edit", key=f"view_{doc.id}"):
                # Store the selected document ID in session_state
                st.session_state["selected_doc"] = doc
                st.switch_page("pages/document_detail.py")
        with colB:
            if st.button("Start Q&A", key=f"qa_{doc.id}"):
                # For demonstration, treat Q&A similarly (go to detail page, or start a chat session)
                # st.session_state["selected_doc_id"] = doc.id
                st.session_state["selected_doc"] = doc
                st.switch_page("pages/chat.py")
        with colC:
            if st.button("Delete", key=f"del_{doc.id}"):
                book_service.delete_book(doc.id)
                st.warning(f"Document '{doc.title}' has been deleted.")
                st.rerun()
