from http.client import REQUEST_URI_TOO_LONG
from openai import OpenAI
from anthropic import Anthropic
import base64
import os
import json

TRANSLATION_PROMPT = \
"""
Your task is to translate a sample of 18th Century French text into English as accurately as possible for an academic research effort.

First, think through the problem step-by-step. Enclose your thinking in <thinking> tags.

When translating, follow these guidelines:
- Translate the text into English if it's 18th century French. If it's not in French, simply transcribe it as is.
- For ambiguous or unknown words, keep the original French in square brackets within your English translation.
- Always maintain the same whitespace including paragraph breaks and tables.
- Do not add any explanations, notes, or comments to your translation.

After you have finished thinking, provide your final output in <output> tags. For example:
<output>Your precise English translation or transcription, with [ambiguous French words] in brackets</output>

If the input is empty, return <output></output>
"""

OCR_PROMPT = \
"""
Your task is to accurately extract French text from this page of an 18th-century French journal.

This image is a greyscale scanned image of a journal page. This image may contain handwritten or printed text, along with pixellated noise.
Follow these steps to approach the task:

1. Analyze the image carefully, looking for any visible text.
2. Think through the problem step-by-step, enclosing your thinking in <thinking> </thinking> tags.
3. Always attempt to extract text, even if the image appears noisy. Do not mistake noise for captchas or other challenges.
4. Retain the layout of words on the page, especially whitespace, paragraph breaks, and any tables.
5. Attempt to transcribe all visible text, including common 18th-century abbreviations and ligatures.
6. Maintain the original spelling, even if it differs from modern French orthography.

After you have finished your analysis and thinking, provide your final output in the following format:

<output>Your transcribed text here</output>

Important notes:
- If no readable text is present, or the image contains only noise or illegible marks, return empty tags <output></output>
- Do not ever return errors or exceptions.
- Never deviate from the specified format.

Remember, your goal is to provide the most accurate transcription possible while adhering to the original layout and spelling of the 18th-century French text.

Here is the text to translate:
"""

FORMAT_PROMPT = \
"""
Your task is to convert a plain text extract with meaningful whitespace to a LaTeX-formatted text extract. The input text may be in French or English and contains meaningful whitespace, tables, and paragraph breaks.

Follow these instructions to convert the plain text to LaTeX format:

First, think through the problem step-by-step. Enclose your thinking in <thinking> tags.

1. Escape special characters:
   - Replace & with \&
   - Replace % with \%
   - Replace $ with \$
   - Replace # with \#
   - Replace _ with \_
   - Replace { with \{
   - Replace } with \}
   - Replace ~ with \textasciitilde
   - Replace ^ with \textasciicircum

2. Handle whitespace:
   - Replace single linebreaks with \\
   - Replace double linebreaks (paragraph breaks) with \\\[0.5em]
   - Preserve leading spaces using \hspace{} (1em is approximately equal to the width of the letter 'M')

3. Maintain layout:
   - Use \hspace{} to maintain horizontal spacing
   - Use \vspace{} to maintain vertical spacing
   - For tables, use the tabular environment and maintain column alignment

4. Output format:
   - After you have finished thinking, produce your final output wrapped in <output> tags like this: <output>LaTeX formatted text</output>
   - Do not include any package imports, document tags, or other frontmatter
   - Do not provide any explanations or error messages
   - If there is no text to format, return <output></output>

Convert the given plain text to LaTeX format following these instructions.

Here is the plain text to convert:
"""

def _encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_text(image_path, model:str):
    if model == "openai":
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        return _openai_extract_text(image_path, client)
    elif model == "claude":
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        return _claude_extract_text(image_path, client)
    else:
        raise ValueError(f"Invalid model: {model}")

def _extract_output(response_txt:str):
    start_idx = response_txt.find("<output>")
    if start_idx != -1:
        response_txt = response_txt[start_idx + len("<output>"):]
    end_idx = response_txt.find("</output>")
    if end_idx != -1:
        response_txt = response_txt[:end_idx]
    response_txt = response_txt.strip()
    return response_txt


def _openai_extract_text(image_path, client):
    base64_image = _encode_image(image_path)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{ "role": "user", "content": [{
                "type": "input_text",
                "text": OCR_PROMPT
            },
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{base64_image}",
            },
        ],
        }]
    )
    result = _extract_output(response.output_text)
    return result

def _openai_translate_text(text, client):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{ "role": "user", "content": [{
                "type": "input_text",
                "text": f"{TRANSLATION_PROMPT}\n\n{text}"
            }],
        }]
    )

    result = _extract_output(response.output_text)
    return result




def _claude_extract_text(image_path, client):
    base64_image = _encode_image(image_path)

    response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=20000,
    temperature=1,
    system="You are an advanced AI system specialized in transcribing 18th-century French handwriting from scanned images.",
    messages=[
        {
            "role": "user",
            "content": [
                {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                },
                {
                    "type": "text",
                    "text": OCR_PROMPT,
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<thinking>"
                }
            ]
        }
    ]
)



    log_txt = response.content[0].text
    result = _extract_output(response.content[0].text)
    return result, log_txt

def _claude_translate_text(french_text, client):
    full_text = f"{TRANSLATION_PROMPT}\n\n{french_text}"

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,
        temperature=1,
        system="You are an expert academic translator and historian specializing in 18th Century French.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": TRANSLATION_PROMPT + "\n\n" + french_text,
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<thinking>"
                }
            ]
        }
    ]
    )
    log_txt = response.content[0].text
    result = _extract_output(response.content[0].text)
    return result, log_txt


def translate_text(text: str, model:str):
    if model == "openai":
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        return _openai_translate_text(text, client)
    elif model == "claude":
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        return _claude_translate_text(text, client)
    else:
        raise ValueError(f"Invalid model: {model}")

def format_text(text: str, model:str):
    if model == "openai":
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        return _openai_format_text(text, client)
    elif model == "claude":
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        return _claude_format_text(text, client)
    else:
        raise ValueError(f"Invalid model: {model}")

def _claude_format_text(text: str, client):
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=20000,
        temperature=1,
        system="You are an advanced coding assistant specializing in LaTeX page layout.",
        messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": FORMAT_PROMPT + "\n\n" + f"<plain_text>{text}</plain_text>"
                }
            ]
        }
    ]
    )
    log_txt = response.content[0].text
    result = _extract_output(response.content[0].text)
    return result, log_txt