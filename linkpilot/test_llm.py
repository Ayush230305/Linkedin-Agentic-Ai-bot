
from llm import create_reviewed_post

instruction = (
    "Write a LinkedIn post about what I learned while building a "
    "small Python project. Do not invent results or achievements."
)

print(create_reviewed_post(instruction, tone="clear and conversational"))

