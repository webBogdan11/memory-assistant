import streamlit as st

from services.book_service import get_book_service
from services.chat_service import get_chat_service

st.set_page_config(
    page_title="Book Q&A Session", page_icon=":question:", layout="centered"
)

st.title("Book Q&A Session")

if "selected_doc" not in st.session_state:
    st.warning("No document selected. Please return to the library.")
    if st.button("Go to Library"):
        st.switch_page("pages/document_liabrary.py")
    st.stop()

doc = st.session_state.get("selected_doc")
DOC_TITLE = doc.title

book_service = get_book_service()
sections = book_service.get_book_sections(doc.id, with_questions=True)

st.subheader(f"Document: {DOC_TITLE}")

if st.button("Return to Document"):
    st.switch_page("pages/document_detail.py")

if st.button("Return to Library"):
    st.switch_page("pages/document_liabrary.py")

section_names = [sec.name for sec in sections]
chosen = st.multiselect("Sections", options=section_names, default=section_names[:1])
active_chat_session = st.session_state.get("chat_session_active", False)

if not active_chat_session:
    if st.session_state.get("session_summary"):
        with st.container():
            session_summary = st.session_state.get("session_summary")
            st.markdown("### Session Summary")
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Overall Score", f"{session_summary.overall_score:.1f}")
                st.metric(
                    "Questions Completed",
                    f"{session_summary.number_of_answered_questions}/{session_summary.number_of_questions}",
                )

            with col2:
                completion_rate = (
                    session_summary.number_of_answered_questions
                    / session_summary.number_of_questions
                    * 100
                )
                st.metric("Completion Rate", f"{completion_rate:.1f}%")

            st.markdown("#### Sections Covered")
            for title in session_summary.section_titles:
                st.markdown(f"- {title}")

    start_quiz = st.button("Start Q&A Session")
    if start_quiz:
        section_ids = [sec.id for sec in sections if sec.name in chosen]
        chat_service = get_chat_service()
        chat_service.init_chat_session(
            user_id=doc.user_id,
            document_id=doc.id,
            section_ids=section_ids,
        )
        st.session_state["chat_service"] = chat_service
        st.session_state["chat_session_active"] = True
        st.session_state["session_summary"] = None
        st.rerun()

if active_chat_session:
    finish_quiz = st.button("Finish Q&A Session")
    if finish_quiz:
        st.session_state["chat_session_active"] = False
        chat_service = st.session_state["chat_service"]
        chat_service.finish_chat_session()
        st.info("Q&A Session finished")
        session_summary = chat_service.make_session_summary()
        st.session_state["session_summary"] = session_summary
        st.rerun()

    chat_service = st.session_state["chat_service"]

    total_questions = len(chat_service.questions)
    answered_questions = len(chat_service.get_assistant_feedback_scores())

    if total_questions > 0:
        answered_fraction = answered_questions / total_questions
    else:
        answered_fraction = 0

    st.progress(answered_fraction)
    st.caption(f"Answered {answered_questions} out of {total_questions} questions")

    messages = chat_service.get_history_messages()

    if len(messages) == 0:
        next_question = chat_service.get_next_question()
        with st.chat_message("assistant"):
            st.markdown(next_question.question)
    else:
        for message in messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Input here"):
        with st.chat_message("user"):
            st.markdown(prompt)

        result = chat_service.process_user_message(prompt)

        if result == "__ALL_DONE__":
            st.session_state["chat_session_active"] = False

            chat_service.finish_chat_session()

            session_summary = chat_service.make_session_summary()
            st.session_state["session_summary"] = session_summary

            st.info("All questions answered. Q&A Session finished automatically!")

            st.rerun()
        else:
            with st.chat_message("assistant"):
                st.markdown(result)
