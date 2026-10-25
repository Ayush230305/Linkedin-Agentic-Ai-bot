import os
from openai import OpenAI

def prepare_post(process: str, draft: str, tone: str, audience: str, max_chars: int = 2800) -> str:
    api_key = os.getenv("ASI_ONE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ASI_ONE_API_KEY is not configured.")
    client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=api_key, timeout=45.0)
    system_prompt = f"""
You are LinkPilot, a reliable LinkedIn publishing assistant.
Transform the user's draft or idea into one useful, authentic LinkedIn post.
Respect the user's process instructions and never invent personal experiences, metrics, awards, employers, or claims.
Audience: {audience}
Tone: {tone}
Maximum length: {max_chars} characters.
Output only the final post text. Do not add explanations, markdown fences, or a title unless it belongs naturally in the post.
Use line breaks for readability. Avoid generic hype, engagement bait, and excessive hashtags.
"""
    response = client.chat.completions.create(
        model=os.getenv("ASI_ONE_MODEL", "asi1"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"MY PROCESS / RULES:\n{process}\n\nMY POST OR IDEA:\n{draft}"}
        ],
        temperature=0.6,
        max_tokens=1200,
    )
    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("ASI:One returned an empty response.")
    if len(text) > max_chars:
        # A second pass is safer than silently truncating mid-sentence.
        response = client.chat.completions.create(
            model=os.getenv("ASI_ONE_MODEL", "asi1"),
            messages=[
                {"role": "system", "content": f"Shorten the following LinkedIn post to at most {max_chars} characters. Preserve its meaning. Output only the revised post."},
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        text = (response.choices[0].message.content or "").strip()
    if len(text) > max_chars:
        raise RuntimeError(f"Agent output is still longer than {max_chars} characters. Shorten the draft manually.")
    return text
