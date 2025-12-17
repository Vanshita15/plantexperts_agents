import os
from typing import Optional
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

def call_llm(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    temperature: float = 0.1,
    max_tokens: int = 1200,
) -> str:
    """Route chat completion to the right provider based on model string.

    Supported:
    - Together: default for models that look like Together-hosted (e.g. 'Qwen/...', 'meta-llama/...')
    - OpenAI: models starting with 'gpt-'
    - Anthropic (Claude): models starting with 'claude-'
    - Gemini: models starting with 'gemini-'
    """

    if not model:
        raise ValueError("model is required")

    m = model.strip()

    # OpenAI
    if m.startswith("gpt-"):
        api_key = os.getenv("OPENAI_API_KEY")
        print("---------------------------------------->",api_key)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")
        api_key = api_key.strip().strip('"').strip("'")
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=m,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    # Anthropic (Claude)
    if m.startswith("claude-"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
        try:
            import anthropic
        except Exception as e:
            raise RuntimeError("Missing dependency 'anthropic'. Install it to use Claude models.") from e

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=m,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        # msg.content is a list of content blocks
        parts = []
        for block in getattr(msg, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return ("".join(parts)).strip()

    # Gemini
    if m.startswith("gemini-"):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) not set in environment")
        try:
            import google.generativeai as genai
        except Exception as e:
            raise RuntimeError(
                "Missing dependency 'google-generativeai'. Install it to use Gemini models."
            ) from e

        genai.configure(api_key=api_key)
        try:
            gm = genai.GenerativeModel(model_name=m, system_instruction=system_prompt)
            resp = gm.generate_content(
                user_message,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
        except TypeError:
            # Older SDK versions may not support system_instruction
            gm = genai.GenerativeModel(model_name=m)
            resp = gm.generate_content(
                f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_message}",
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
        return (getattr(resp, "text", None) or "").strip()

    # Together (default)
    from together import Together

    client = Together()
    resp = client.chat.completions.create(
        model=m,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()
