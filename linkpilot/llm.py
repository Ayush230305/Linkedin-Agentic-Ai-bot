import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "asi1").lower()

if PROVIDER == "asi1":
    BASE_URL = os.getenv("ASI1_BASE_URL", "https://api.asi1.ai/v1")
    API_KEY = os.getenv("ASI1_API_KEY", "")
    MODEL = os.getenv("ASI1_MODEL", "asi1")
elif PROVIDER == "openai":
    BASE_URL = None
    API_KEY = os.getenv("OPENAI_API_KEY", "")
    MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
else:
    raise ValueError(
        "Unsupported provider. Use asi1 or openai, or adapt the client "
        "for your provider's current API."
    )

if not API_KEY:
    raise RuntimeError(f"Missing API key for provider {PROVIDER}.")

client = OpenAI(
    api_key=API_KEY,
    **({"base_url": BASE_URL} if BASE_URL else {}),
)

MAX_CHARS = int(os.getenv("MAX_POST_CHARS", "2800"))

SYSTEM_PROMPT = """
You are LinkPilot, a careful LinkedIn writing assistant.

Write a professional, human-sounding LinkedIn post from the user's
instruction. Start with a specific, compelling hook. Use short paragraphs,
clear language, and a useful takeaway. Stay within the character limit.
Use 3-5 relevant hashtags only when appropriate.

Never invent facts, statistics, credentials, job titles, company names,
projects, results, quotes, or personal experiences. If a detail is missing,
omit it or ask the user for clarification. Do not claim the user did
something unless the instruction supports that claim.

Avoid engagement bait, fake personal stories, exaggerated claims, and
generic motivational filler. Return only the post text, without analysis
or quotation marks.
"""


def _complete(system: str, user: str, max_tokens: int = 1200) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        max_tokens=max_tokens,
    )
    result = response.choices[0].message.content
    if not result or not result.strip():
        raise RuntimeError("The LLM returned an empty response.")
    return result.strip()


def generate_post(instruction: str, tone: str = "professional") -> str:
    instruction = instruction.strip()
    if not instruction:
        raise ValueError("Instruction cannot be empty.")

    if len(instruction) > 4000:
        raise ValueError("Instruction is too long; limit it to 4000 characters.")

    draft = _complete(
        SYSTEM_PROMPT,
        f"Tone: {tone}\nCharacter limit: {MAX_CHARS}\n"
        f"User instruction:\n{instruction}",
    )

    if len(draft) > MAX_CHARS:
        draft = _complete(
            SYSTEM_PROMPT,
            f"Rewrite this post to fit within {MAX_CHARS} characters. "
            "Preserve only supported facts. Return only the final post.\n\n"
            + draft,
        )

    if len(draft) > MAX_CHARS:
        raise ValueError(
            f"Draft still exceeds the {MAX_CHARS}-character limit."
        )

    return draft


def critique_post(instruction: str, draft: str) -> str:
    critique_prompt = f"""
Review this proposed LinkedIn post.

Check:
1. Does it satisfy the original instruction?
2. Does it invent any facts or personal experiences?
3. Is the opening compelling without clickbait?
4. Is it readable and appropriately professional?
5. Is it within {MAX_CHARS} characters?
6. Are hashtags relevant and limited?

If it passes, return it unchanged. Otherwise, improve it.
Return only the final post, with no explanation.

Original instruction:
{instruction}

Draft:
{draft}
"""
    improved = _complete(
        "You are a strict LinkedIn post editor. Never add unsupported facts.",
        critique_prompt,
    )

    if len(improved) > MAX_CHARS:
        raise ValueError("Critic output exceeds the character limit.")

    return improved


def create_reviewed_post(
    instruction: str, tone: str = "professional"
) -> str:
    draft = generate_post(instruction, tone)
    try:
        return critique_post(instruction, draft)
    except Exception:
        # A failed or over-long critic pass should not throw away a good draft.
        return draft