from typing import Literal
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from config import settings
from langsmith import traceable

from models.chat_session import ChatMessageType


class SectionInfo(BaseModel):
    title: str
    page_number: int


class SectionInfoList(BaseModel):
    sections_info: list[SectionInfo]


class Question(BaseModel):
    question: str


class QuestionList(BaseModel):
    questions: list[Question]


class UserMessageRouterOutput(BaseModel):
    type: Literal[
        ChatMessageType.ANSWER.value,
        ChatMessageType.HELP.value,
        ChatMessageType.OTHER.value,
    ]


class UserAnswerEvaluationOutput(BaseModel):
    feedback: str
    score: float


class UserExplanationGenerationOutput(BaseModel):
    explanation: str


@traceable(name="section-info")
def get_section_info(content: str, example_titles: list[str]) -> SectionInfoList:
    llm = ChatOpenAI(
        model="gpt-4o", api_key=settings.OPENAI_API_KEY
    ).with_structured_output(SectionInfoList)

    example_titles_str = "\n".join(
        [f"{i + 1}. {title}" for i, title in enumerate(example_titles)]
    )
    prompt = PromptTemplate(
        template="""
        You are an expert at extracting structured data from text. Given the content of a document, your task is to extract information about the chapters or sections within it.

        - A section is defined as a part of the document with a clear title and an indication of the page where it begins.
        - Your output should include the title of each section or chapter and the corresponding starting page number.
        - Sections should not be a lot of, they can start with Chapter or any other, wisely extract if from the table of contents. Not sub-sections, only the main sections.

        Here is the table of contents of the document:

        {content}

        Here are some examples of section titles:

        {example_titles_str}

        Based on this content, extract the following information:
        1. The name of each chapter or section.
        2. The page number where each chapter or section starts.

        Provide the output as a structured list of SectionInfo objects, where each object contains:
        - `title`: The name of the section or chapter include it without chapter number or any other prefix.
        - `page_number`: The page number where it begins.

        Ensure the output is well-structured and corresponds to the given content. If no chapters or sections are found, return an empty list.
    """
    )
    return llm.invoke(
        prompt.format(content=content, example_titles_str=example_titles_str)
    )


@traceable(name="section-questions")
def generate_questions(content: str, num_questions: int) -> QuestionList:
    llm = ChatOpenAI(
        model="gpt-4o", api_key=settings.OPENAI_API_KEY
    ).with_structured_output(QuestionList)
    prompt = PromptTemplate(
        template="""
        You are an expert in generating thought-provoking, insightful, and educational questions from a text. 
        Your goal is to create {num_questions} questions 
        that uncover the most critical ideas, concepts, and implications presented in the text. 
        
        These questions should:

        1. **Core Understanding**: Identify and focus on the main themes, principles, or ideas outlined in the content.
        2. **Critical Thinking**: Encourage analysis, evaluation, and interpretation of the material.
        3. **Practical Application**: Explore how the concepts can be applied in real-world scenarios or other relevant contexts.
        4. **Connections**: Draw links between the content and broader concepts, interdisciplinary ideas, or prior knowledge.
        5. **Clarifications**: Address any potentially confusing or ambiguous parts to deepen understanding.
        6. **Creative Exploration**: Inspire further thought or exploration beyond the text itself.

        Ensure a variety of question types (e.g., open-ended, reflective, scenario-based, problem-solving, 
        or concept-clarifying) to cater to different levels of engagement. 

        Input Content:
        {content}

        """
    )
    return llm.invoke(prompt.format(content=content, num_questions=num_questions))


@traceable(name="improve_question")
def improve_question(question: str, feedback: str) -> Question:
    llm = ChatOpenAI(
        model="gpt-4o", api_key=settings.OPENAI_API_KEY
    ).with_structured_output(Question)

    # Enhanced prompt for improved performance
    prompt = PromptTemplate(
        template="""
        You are a professional linguist and expert in question refinement. 
        Your role is to improve the clarity, precision, 
        and quality of the given question while incorporating the provided feedback.
        
        Guidelines:
        1. Retain the core intent and meaning of the original question.
        2. Address the specific feedback points directly and comprehensively.
        3. Optimize for clarity, conciseness, and appropriate tone.

        Input:
        Original Question:
        {question}

        Feedback on Question:
        {feedback}

        Task:
        Improve the above question based on the feedback, ensuring it is more effective, 
        clear, and adheres to the provided guidelines.
        """
    )

    return llm.invoke(prompt.format(question=question, feedback=feedback))


@traceable(name="user_message_router")
def determine_message_type(message: str, question: str) -> UserMessageRouterOutput:
    llm = ChatOpenAI(
        model="gpt-4o", api_key=settings.OPENAI_API_KEY
    ).with_structured_output(UserMessageRouterOutput)

    prompt = PromptTemplate(
        template="""
        You are an expert message classifier specializing in educational interactions. Your task is to analyze user messages and classify them into specific response types.

        CONTEXT:
        - You are processing messages from a learning environment where users can either:
        1. Attempt to answer a question
        2. Ask for help/explanation
        3. Send other types of messages

        TASK:
        Analyze the user's message in relation to the given question and classify it into one of these categories:
        - answer: When the user is attempting to provide an answer to the question
        - help: When the user is asking for clarification, hints, or explanation
        - other: When the message doesn't fit either category above

        INPUT:
        Question: {question}
        User Message: {message}

        RULES:
        1. Focus on the intent and structure of the message
        2. Look for question marks and help-seeking language for help classification
        3. Look for answer-like statements and direct responses for answer classification
        4. When in doubt, prefer other classification

        OUTPUT REQUIREMENTS:
        - Respond with exactly one classification (answer, help, or other)
        - Be consistent and deterministic in classification
        - Consider the context of both the question and the message

        EXAMPLES:
        Question: "What is photosynthesis?"
        - "I think it's the process where plants convert sunlight to energy" → answer
        - "Can you explain this in simpler terms?" → help
        - "When is the next class?" → other
        """
    )

    return llm.invoke(prompt.format(question=question, message=message))


def evaluate_answer(answer: str, question: str, section_content: str) -> str:
    llm = ChatOpenAI(
        model="gpt-4o", api_key=settings.OPENAI_API_KEY
    ).with_structured_output(UserAnswerEvaluationOutput)

    prompt = PromptTemplate(
        template="""
        You are an expert educational evaluator specializing in providing constructive feedback on student answers.
        Your task is to evaluate the answer comprehensively and provide detailed, actionable feedback.

        EVALUATION CRITERIA:
        1. Accuracy (How correct is the answer based on the section content?)
        2. Completeness (Does it cover all key points?)
        3. Understanding (Does it demonstrate deep comprehension?)
        4. Clarity (Is it well-articulated and logically structured?)

        Question:
        {question}

        Student Answer:
        {answer}

        Reference Content:
        {section_content}

        INSTRUCTIONS:
        1. Score the answer from 0 to 10, where:
           - 9-10: Exceptional, comprehensive answer
           - 7-8: Strong answer with minor gaps
           - 5-6: Adequate but needs improvement
           - 3-4: Partial understanding shown
           - 0-2: Significant misconceptions or gaps

        2. Provide structured feedback including:
           - Key strengths of the answer
           - Specific areas for improvement
           - Missing key concepts
           - Practical suggestions for enhancement
           - Correct information for any misconceptions

        Remember to:
        - Be encouraging and constructive
        - Provide specific examples from the reference content
        - Explain why certain points are important
        - Suggest concrete steps for improvement
        """
    )

    return llm.invoke(
        prompt.format(answer=answer, question=question, section_content=section_content)
    )


def generate_explanation(message: str, question: str, section_content: str) -> str:
    llm = ChatOpenAI(
        model="gpt-4o", api_key=settings.OPENAI_API_KEY
    ).with_structured_output(UserExplanationGenerationOutput)

    prompt = PromptTemplate(
        template="""
        You are an expert educational explainer specializing in providing clear, engaging, and comprehensive explanations.
        Your goal is to help students understand concepts thoroughly by combining information from the reference content
        and your general knowledge when appropriate.

        GUIDELINES:
        1. First, address the specific aspects the user is asking about in their message
        2. Use the reference content as the primary source of information
        3. Supplement with general knowledge when:
           - Additional context would enhance understanding
           - Real-world examples would clarify the concept
           - Connecting to related concepts would deepen learning
        4. Structure your explanation with:
           - A clear introduction of the concept
           - Step-by-step breakdown of complex ideas
           - Relevant examples and analogies
           - Connection to practical applications
        5. Use simple language while maintaining accuracy
        6. Include visual descriptions or metaphors when helpful

        Question:
        {question}

        User Message:
        {message}

        Reference Content:
        {section_content}

        RESPONSE FORMAT:
        - Begin with a direct answer to the user's specific query
        - Follow with detailed explanation
        - Include examples or analogies
        - End with a brief summary or key takeaway

        Remember to:
        - Stay focused on the user's specific needs
        - Balance depth with clarity
        - Make complex concepts accessible
        - Encourage further understanding
        """
    )

    return llm.invoke(
        prompt.format(
            message=message, question=question, section_content=section_content
        )
    )
