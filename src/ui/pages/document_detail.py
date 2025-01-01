import streamlit as st

from src.services.section_service import get_section_service


st.title("Document Detail Page")

# If no doc selected, prompt user to go back
if "selected_doc" not in st.session_state:
    st.warning("No document selected. Please return to the library.")
    if st.button("Go to Library"):
        st.switch_page("pages/document_liabrary.py")
    st.stop()

doc = st.session_state["selected_doc"]
section_service = get_section_service()
sections = section_service.get_sections_by_book_id(doc.id)

# --- Header / Document Overview ---
st.subheader(f"Document: {doc.title}")
st.write("**Metadata**")
col1, col2 = st.columns(2)
with col1:
    st.write(f"- **Date Uploaded**: {doc.created_at}")
    st.write(f"- **Pages**: {doc.metadata.pages}")
with col2:
    st.write(f"- **Size**: {doc.metadata.doc_size} MB")
    # st.write(
    #     f"- **Sections Detected**: {doc['metadata'].get('sections_detected', 'N/A')}"
    # )

if st.button("Return to Library"):
    st.switch_page("pages/document_liabrary.py")

if st.button("Chat about this Document"):
    st.switch_page("pages/chat.py")


st.divider()

# --- Section Management ---
st.write("## Section Management")

with st.expander("Create sections with AI"):
    with st.form("create_sections_form"):
        st.write(
            "Please provide the following information to automatically create sections:"
        )

        col1, col2 = st.columns(2)
        with col1:
            start_page = st.number_input("Content Start Page", min_value=1, value=1)
            content_end_page = st.number_input("Content End Page", min_value=1, value=1)
        with col2:
            preface_start = st.number_input("Preface Start Page", min_value=1, value=1)
            preface_end = st.number_input("Preface End Page", min_value=1, value=1)

        st.write("Example section titles (helps AI understand the document structure)")
        example_titles = []
        for i in range(3):
            title = st.text_input(f"Example Title {i+1}", key=f"example_title_{i}")
            if title:
                example_titles.append(title)

        submit_button = st.form_submit_button("Create Sections")
        if submit_button and example_titles:
            try:
                new_sections = section_service.create_sections_magically(
                    book_id=doc.id,
                    example_titles=example_titles,
                    start_page=start_page,
                    content_end_page=content_end_page,
                    preface_start_page=preface_start,
                    preface_end_page=preface_end,
                )
                st.success(f"Successfully created {len(new_sections)} sections!")
                st.rerun()
            except Exception as e:
                st.error(f"Error creating sections: {str(e)}")
        elif submit_button:
            st.warning("Please provide at least one example title")


for section in sections:
    with st.expander(f"Section {section.order}: {section.name}", expanded=False):
        # Display current start/end pages
        st.write(f"**Start Page**: {section.start_page}")
        st.write(f"**End Page**: {section.end_page}")

        # --- Update Form Below ---
        with st.form(f"edit_section_form_{section.id}"):
            st.write("### Update Section")
            new_name = st.text_input(
                label="New Name", value=section.name, key=f"name_{section.id}"
            )
            new_start_page = st.number_input(
                label="New Start Page",
                min_value=1,
                value=section.start_page,
                key=f"start_page_{section.id}",
            )
            new_end_page = st.number_input(
                label="New End Page",
                min_value=new_start_page,
                value=section.end_page,
                key=f"end_page_{section.id}",
            )

            submitted = st.form_submit_button("Update Section")
            if submitted:
                try:
                    updated_sec = section_service.update_section(
                        section_id=section.id,
                        new_name=new_name,
                        new_start_page=new_start_page,
                        new_end_page=new_end_page,
                    )
                    st.session_state[f"update_success_{section.id}"] = True
                except Exception as e:
                    st.error(f"Error updating section: {str(e)}")

        # If updated successfully, show message and rerun
        if st.session_state.get(f"update_success_{section.id}", False):
            st.success("Section updated successfully!")
            del st.session_state[f"update_success_{section.id}"]
            st.rerun()

        # --- Two Columns for Chat & Remove ---
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("Chat about this Section", key=f"chat_{section.id}"):
                st.session_state["current_doc_title"] = doc.title
                st.session_state["current_section_title"] = section.name
                st.switch_page("pages/chat.py")

        with col2:
            if st.button("🗑️ Remove", key=f"delete_{section.id}", help="Delete section"):
                try:
                    section_service.delete_section(section.id)
                    st.success(f"Section '{section.name}' deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting section: {str(e)}")

st.write("#### Add New Section")

with st.form("add_new_section"):
    new_section_title = st.text_input("Section Title")
    col1, col2, col3 = st.columns(3)
    with col1:
        new_start_page = st.number_input("Start Page", min_value=1, value=1)
    with col2:
        new_end_page = st.number_input("End Page", min_value=1, value=1)
    with col3:
        new_order = st.number_input(
            "Order (optional)",
            min_value=-1,
            value=-1,
            help="Leave as -1 to add to the end",
        )

    submit_new = st.form_submit_button("Add Section")
    if submit_new:
        if new_section_title and new_start_page <= new_end_page:
            try:
                section_service.add_section_to_book(
                    book_id=doc.id,
                    start_page=new_start_page,
                    end_page=new_end_page,
                    title=new_section_title,
                    order=new_order,  # Will use the user-specified order or -1 as default
                )
                st.success("Section added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding section: {str(e)}")
        else:
            st.error(
                "Please provide a title and ensure start page is less than or equal to end page"
            )

st.divider()

# --- Question Generation Panel ---
st.write("## Question Management")

if not sections:
    st.info("No sections available yet. Please create or add sections above.")
    st.stop()

section_options = {f"{sec.order}: {sec.name}": sec for sec in sections}
default_selection = list(section_options.keys())[0]
selected_section_label = st.selectbox(
    "Select a section to work with:", options=section_options.keys(), index=0
)
selected_section = section_options[selected_section_label]

st.markdown(f"**Selected Section**: {selected_section.name}")

questions = section_service.get_questions_by_section_id(selected_section.id)
st.write(f"### Existing Questions for Section *{selected_section.name}*")

if not questions:
    st.info("No questions found in this section.")
else:
    for q_item in questions:
        with st.expander(f"Question: {q_item.question}", expanded=False):
            # Show question details + allow editing
            st.write(f"**Question text**: {q_item.question}")

            # -- Update Question Form --
            with st.form(f"update_question_form_{q_item.id}"):
                updated_text = st.text_input(
                    "Update Question Text",
                    value=q_item.question,
                    key=f"q_text_{q_item.id}",
                )
                update_submitted = st.form_submit_button("Update Question")

            if update_submitted:
                try:
                    section_service.update_question(
                        question_id=q_item.id,
                        section_id=selected_section.id,
                        question=updated_text,
                        type="general",
                    )
                    st.success("Question updated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating question: {str(e)}")

            with st.form(f"ai_modify_question_{q_item.id}"):
                feedback_text = st.text_input(
                    "Enter feedback or context for AI improvement",
                    key=f"feedback_{q_item.id}",
                )
                modify_submitted = st.form_submit_button("Improve with AI")

            if modify_submitted:
                try:
                    section_service.modify_question_magically(
                        question_id=q_item.id,
                        section_id=selected_section.id,
                        feedback=feedback_text,
                    )
                    st.success("Question improved using AI!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error improving question: {str(e)}")

            # -- Delete Question --
            if st.button("Delete Question", key=f"del_q_{q_item.id}"):
                try:
                    section_service.delete_question(
                        question_id=q_item.id, section_id=selected_section.id
                    )
                    st.success("Question deleted successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting question: {str(e)}")

st.write("### Generate Questions with AI")
num_q = st.number_input(
    "Number of questions to generate", min_value=1, max_value=20, value=3, step=1
)
if st.button("Generate Questions"):
    with st.spinner("Generating questions..."):
        try:
            new_questions = section_service.generate_questions_magically(
                selected_section.id, num_questions=num_q
            )
            st.success(f"Generated {len(new_questions)} new question(s)!")
            st.rerun()
        except Exception as e:
            st.error(f"Error generating questions: {str(e)}")

st.write("### Add a New Question")
with st.form("add_question_form"):
    new_question_text = st.text_input("Question Text")
    add_submitted = st.form_submit_button("Add Question")

if add_submitted:
    if new_question_text.strip():
        try:
            section_service.add_question(
                section_id=selected_section.id,
                question=new_question_text,
                type="general",
            )
            st.success("Question added successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error adding question: {str(e)}")
    else:
        st.warning("Please enter a valid question text.")
