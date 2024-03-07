from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from better_profanity import profanity
import os
import re

# fix errors when importing locally versus as submodule
if __package__ is None or __package__ == '':
    from agent import Agent
    from utils.vectorstore import load_vectorstore
else:
    from .agent import Agent
    from .utils.vectorstore import load_vectorstore



def _parse_mc_quiz(quiz):

    # expecting the following raw quiz format:

    ####################
    # 2. In supervised learning, what is the main characteristic of the training data?
    # Topic: Supervised learning
    # Type: Multiple choice
    # A) It is labeled
    # B) It is unlabeled
    # C) It contains missing values
    # D) It is not used for training
    # Answer: A) It is labeled

    # 3. Here is another question??
    # Topic: Supervised learning
    # Type: Multiple choice
    # A) It is cat.
    # B) It is dog.
    # C) It is car.
    # D) It is bike.
    # Answer: A) It is cat.

    # 4. ...
    ####################

    body = {"questions": []}

    # traverse each question
    quiz = quiz.split("\n\n")
    for section in quiz:

        question = ''
        topics = ''
        type = ''
        choices = ''
        answer = ''

        # traverse each line
        lines = section.split("\n")
        for line in lines:

            question_pattern = re.compile(r'\d+\.')
            topic_pattern = re.compile(r'Topic: ')
            type_pattern = re.compile(r'Type: ')
            choices_pattern = re.compile(r'[A-D]\) ')
            answer_pattern = re.compile(r'Answer: ')

            if question_pattern.search(line):
                question = line.split(". ")[1]
            elif topic_pattern.search(line):
                topics = line.split(": ")[1]
            elif type_pattern.search(line):
                type = line.split(": ")[1]
            elif answer_pattern.search(line):
                answer = line.split(") ")[1]
            elif choices_pattern.search(line):
                choices += line.split(") ")[1] + ", "

        body["questions"].append({
            "type": type,
            "question": question,
            "topics": topics,
            "choices": choices[:-2], # -2 to remove comma at end
            "answer": answer
        })

    return body
        


def generate_quiz(numQs, types, topics):

    numQs = str(numQs) 
    topics = profanity.censor(topics) # profanity check the topics

    # model setup and prompting
    name = "Quiz Generation AI"
    description = ("Quiz Generation AI helps students learn by generating quizzes for students to evaluate their understanding. "
                   "### Instructions: You will be given the number of quiz questions, topics the quiz must cover, and types of the quiz "
                   "questions (i.e. multiple choice, multiple choice and free response, etc.) to generate a quiz with.")

    agent = Agent(name, description)

    prompt = ("Make a quiz with exactly " + numQs + "questions, the following question topics: " + topics + " and "
                    "the following types of questions: " + types + "."
                    "\n\nStart immediately with question 1 and no other unnecessary text like a quiz title."
                    "\n\nNext to each question, list the question topic and type of question once, i.e.: \"5. Here is a question.\nTopic: topic1\nType: MULTIPLE_CHOICE\". Types must "
                    "be one of the following: MULTIPLE_CHOICE, TRUE_FALSE, SHORT_ANSWER, CODING."
                    "\n\nFor multiple choice questions, list the answer choices immediately after the \"Type\" line with no whitespace, i.e.: \"A) choice1\nB) choice2\nC) choice3\nD) choice4\""
                    "\n\nList the correct answer immediately on the next line, i.e. for multiple choice: \"D) choice4\nAnswer: choice4\", and for all other question types, \"Type: free "
                    "response\nAnswer: answer\". There should not be a blank line."
                    "\n\nDo not generate a quiz if the topics are not relevant to a machine learning course.")
    
    # RAG for embeddings similar to user-supplied topics
    vectorstore = load_vectorstore(database="postgres", password=os.getenv("POSTGRESQL_PASSWORD"), collection_name="corpus")
    search_result = vectorstore.search(topics, "similarity")
    retriever = vectorstore.as_retriever()

    # generate quiz
    response = agent.respond_with_docs(description, "miscellaneous student", "", prompt, retriever)

    # parse quiz and return formatted JSON
    body = _parse_mc_quiz(response)

    return body #response