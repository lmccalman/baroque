import base64
import json
import os
from time import sleep

import config as cfg


def _encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _extract_output(response_txt: str):
    start_idx = response_txt.find("<output>")
    if start_idx != -1:
        response_txt = response_txt[start_idx + len("<output>") :]
    end_idx = response_txt.find("</output>")
    if end_idx != -1:
        response_txt = response_txt[:end_idx]
    response_txt = response_txt.strip()
    return response_txt


def friendly_retries(func):
    def wrapper(*args, **kwargs):

        last_e = None
        result = None
        for _ in range(10):
            try:
                # Call the original function
                result = func(*args, **kwargs)
                break
            except Exception as e:
                print(f"Warning: {e}\n Retrying...")
                last_e = e
                sleep(10)

        if result is not None:
            return result
        else:
            raise last_e

    return wrapper


@friendly_retries
def extract_text(client, image_data):
    base64_image = base64.b64encode(image_data).decode("utf-8")

    max_tokens = 20000
    temperature = 1
    system = "You are an advanced AI system specialized in transcribing 18th-century French handwriting from scanned images."
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_image,
                    },
                },
                {
                    "type": "text",
                    "text": cfg.OCR_PROMPT,
                },
            ],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "<thinking>"}]},
    ]

    response = client.messages.create(
        model=cfg.MODEL_ID,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    )

    # retry with smaller model if refused
    if response.stop_reason != "end_turn":
        response = client.messages.create(
            model=cfg.LITE_MODEL_ID,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )

    log_txt = response.content[0].text
    result = _extract_output(response.content[0].text)
    return result, log_txt


@friendly_retries
def translate_text(client, french_text):
    response = client.messages.create(
        model=cfg.MODEL_ID,
        max_tokens=4000,
        temperature=1,
        system="You are an expert academic translator and historian specializing in 18th Century French.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cfg.TRANSLATION_PROMPT + "\n\n" + french_text,
                    }
                ],
            },
            {"role": "assistant", "content": [{"type": "text", "text": "<thinking>"}]},
        ],
    )
    log_txt = response.content[0].text
    result = _extract_output(response.content[0].text)
    return result, log_txt


def format_text(client, text: str):
    response = client.messages.create(
        model=cfg.MODEL_ID,
        max_tokens=20000,
        temperature=1,
        system="You are an advanced coding assistant specializing in LaTeX page layout.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cfg.FORMAT_PROMPT
                        + "\n\n"
                        + f"<plain_text>{text}</plain_text>",
                    }
                ],
            }
        ],
    )
    log_txt = response.content[0].text
    result = _extract_output(response.content[0].text)
    return result, log_txt


def _claude_analyse_text(full_text: str, client):
    response = client.messages.create(
        model=MODEL_ID,
        max_tokens=20000,
        temperature=1,
        system="You are an expert academic historian specialising in 18th century Europe.",
        thinking={"type": "enabled", "budget_tokens": 16000},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT1 + full_text + ANALYSIS_PROMPT2,
                    }
                ],
            }
        ],
    )
    log_txt = (
        "THINKING\n\n"
        + response.content[0].thinking
        + "\n\nRESPONSE\n\n"
        + response.content[1].text
    )
    result = _extract_output(response.content[1].text)
    return result, log_txt


def analyse_text(full_text: str):
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _claude_analyse_text(full_text, client)
