# from langchain.chat_models import ChatOpenAI
# from langchain_community.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains import create_retrieval_chain
from langchain import hub
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()


def generate(input_str, system_prompt=None, chat_history_func=None, retriever=None, temperature=0.7):
    """
    A function that routes the text generation process based on the provided parameters.

    Parameters:
    - input_str: The input string to generate text from.
    - system_prompt (str, optional): System prompt for text generation. Default is None.
    - chat_history_func (func, optional): Function to provide chat history. Default is None.
    - retriever (optional): Retriever for Retrival Augmented Generation (RAG). Default is None.
    - temperature (float, optional): Parameter controlling the randomness of the response generation. Default is 0.7.

    Returns:
    - The generated text based on the input and optional parameters.
    """
    if chat_history_func and retriever:
        return generate_with_docs_and_history(input_str, system_prompt, retriever, chat_history_func, temperature=temperature)
    elif chat_history_func:
        return generate_with_history(input_str, system_prompt, chat_history_func, temperature=temperature)
    elif retriever:
        return generate_with_docs(input_str, system_prompt, retriever, temperature=temperature)
    else:
        return generate_base(input_str, '' if system_prompt is None else system_prompt, temperature=temperature)


def generate_base(input_str, system_prompt, temperature=0.7):
    """
    Internal Function, used by generate() function. You likely want to use generate() instead.
    """
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt),
                                               MessagesPlaceholder(variable_name="history"),
                                               ("human", "{input}")])
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=temperature)
    chain = LLMChain(prompt=prompt, llm=llm)
    message = chain.invoke({"input": input_str, "history": []})
    return message["text"].strip()


def generate_with_docs(input_str, system_prompt, retriever, temperature=0.7):
    """
    Internal Function, used by generate() function. You likely want to use generate() instead.
    """
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=temperature)
    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
    retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)
    message = retrieval_chain.invoke({"input": input_str, "context": system_prompt})
    return message['answer'].strip()


def generate_with_history(input_str, system_prompt, chat_history_func, temperature=0.7):
    """
    Internal Function, used by generate() function. You likely want to use generate() instead.
    """
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt),
                                               MessagesPlaceholder(variable_name="history"),
                                               ("human", "{input}")])
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=temperature)
    chain = LLMChain(prompt=prompt, llm=llm)
    with_message_history = RunnableWithMessageHistory(chain, chat_history_func, input_messages_key='input',
                                                      history_messages_key='history', output_messages_key='text')
    message = with_message_history.invoke({"input": input_str}, config={'configurable': {'session_id': 'test'}})
    return message['text'].strip()


def generate_with_docs_and_history(input_str, system_prompt, retriever, chat_history_func, temperature=0.7):
    """
    Internal Function, used by generate() function. You likely want to use generate() instead.
    """
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=temperature)
    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    combine_docs_chain = create_stuff_documents_chain(llm, retrieval_qa_chat_prompt)
    retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)
    with_message_history = RunnableWithMessageHistory(retrieval_chain, chat_history_func, input_messages_key='input',
                                                      history_messages_key='chat_history', output_messages_key='answer')
    message = with_message_history.invoke({"input": input_str, "context": system_prompt},
                                          config={'configurable': {'session_id': 'test'}})
    return message['answer'].strip()

