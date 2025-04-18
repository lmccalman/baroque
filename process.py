from openai import OpenAI
from anthropic import Anthropic
import base64
import os
import json


OPENAI_OCR_PROMPT2 = """
Read a greyscale scanned image containing 18th-century French handwriting, and output the French text as accurately as possible, preserving original spelling, punctuation, and whitespace (including paragraph breaks). Always produce JSON output in the exact format:

{ "text": "scanned text" }

If no readable text is present, or the image contains only noise or illegible marks, return:

{ "text": "" }

Do not return errors or exceptions. Do not mistake noise for captchas or other challenges. Attempt to transcribe all visible text, including common 18th-century abbreviations and ligatures where possible.
"""

CLAUDE_OCR_PROMPT = \
"""
You are an AI assistant tasked with performing Optical Character Recognition (OCR) on greyscale scans of 18th century French handwriting. Your goal is to extract the French text from these images and provide the results in a specific JSON format.

You will be provided with image data in the following format:

<image_data>
{{IMAGE_DATA}}
</image_data>

Process this image data to extract the French text, keeping in mind the following:

1. The images are greyscale scans of 18th century French handwriting.
2. There may be some pixel noise in the images, which should not be mistaken for captchas.
3. Focus on extracting legible French text from the handwriting.

When processing the image, follow these guidelines:

1. Use appropriate OCR techniques to recognize and extract the French text from the handwriting.
2. Ignore any pixel noise that doesn't appear to be part of the actual text.
3. If you encounter any difficulties in extracting text or if no text is found, set the 'text_found' flag to false in your output.

Your output must always be in JSON format with the following structure:

{
  "text_found": boolean,
  "text": string
}

Where:
- 'text_found' is a boolean indicating whether any text was successfully extracted (true) or not (false).
- 'text' is a string containing the extracted French text if any was found. If no text was found or there was an error, this should be an empty string.

Important notes:
1. Always provide your output in this exact JSON format.
2. Do not output anything additional outside of this JSON structure.
3. If there is an error or no text is extracted, set "text_found" to false and "text" to an empty string.
4. Never deviate from this JSON format under any circumstances.

Process the provided image data and return your results in the specified JSON format.
"""

OCR_PROMPT2 = """
You are an advanced AI system specialized in transcribing 18th-century French handwriting from scanned images. Your task is to accurately read and transcribe the text from a greyscale scanned image, preserving the original spelling, punctuation, and whitespace (including paragraph breaks).

Before providing the final transcription, please analyze the image content in detail. Wrap your analysis in <image_analysis> tags, addressing the following points:

1. Describe the overall quality and characteristics of the image.
2. Identify any specific challenges in reading the handwriting.
3. Note any unique 18th-century French writing features observed.
4. Outline your approach for transcribing difficult or ambiguous parts.

Instructions for transcription:
1. Carefully examine the entire image for any visible text.
2. Transcribe all readable text, maintaining the original spelling, even if it differs from modern French orthography.
3. Preserve all original punctuation.
4. Maintain the original whitespace, including paragraph breaks.
5. When possible, interpret and transcribe common 18th-century abbreviations and ligatures.
6. If you encounter illegible marks or noise in the image, do not mistake these for text or captchas.

If the image contains readable text, provide your transcription in the specified JSON format. If no readable text is present, or the image contains only noise or illegible marks, return an empty string as the text value.

Output Format:
Your final output must be in the following JSON format:

{
  "text": "Your transcribed text goes here, or an empty string if no readable text is found"
}

Remember to escape any special characters in the JSON string as needed.

Begin your analysis now, followed by the transcription in the required format.

Here is the scanned image data you need to analyze:
"""

OPENAI_OCR_PROMPT = (
    "You are an OCR agent specialized in extracting text from images that may contain French handwriting from the 18th century. You may encounter noisy or degraded images, including artifacts that resemble CAPTCHAs or pixel-level noise—do not assume they are CAPTCHAs unless explicitly stated.\n\n"
    "Your task is to:\n\n"
    "Extract all readable text from the image, whether handwritten or printed.\n\n"
    "If no text can be reliably found, return a structured response indicating so.\n\n"
    "Do not return any errors. Even in low-confidence or illegible scenarios, return an empty or null value with an appropriate text_found: false flag.\n\n"
    "You should always respond in the following strict JSON format:\n\n"
    "{\n"
    '  "text_found": true | false,\n'
    '  "text": "string containing extracted text, or null if not found"\n'
    "}\n\n"
    "Notes for processing:\n\n"
    "The image may be in French.\n\n"
    "Handwriting may be cursive or stylized.\n\n"
    "Pixel-level noise should not be misclassified as CAPTCHA or intentional obfuscation unless clearly labeled.\n\n"
    "Do your best to read partial or degraded characters; it's okay to be approximate, but prefer legibility."
)

TRANSLATION_PROMPT = (
    "You are working as an academic historian. Translate the following text from "
    "18th century French to English, preserving the original meaning and intent. "
    "Output as plain text and retainthe original whitespace. If there is no text, "
    "return an empty string."
)

TRANSLATION_PROMPT2 = \
"""
You are a highly skilled translator specializing in 18th century French texts. Your task is to translate the given text into English for academic historical research, maintaining maximum precision. Follow these steps:

1. Carefully read and analyze the provided French text.

2. Wrap your analysis of the translation process inside <translation_process> tags in your thinking block. Consider:
   - The overall context and tone of the text
   - List out key vocabulary, idiomatic expressions, and period-specific language
   - Potential challenges in translation and multiple translation options for challenging phrases
   - Your approach to maintaining accuracy

3. Translate the text into English if it's 18th century French. If it's not in French, simply transcribe it as is.

4. For ambiguous or unknown words, keep the original French in square brackets within your English translation.

5. Maintain the tone, style, and any specialized terminology of the original text as much as possible.

6. Do not add any explanations, notes, or comments to your translation outside of the <translation_process> section.

7. If the input is empty, ensure that your output contains an empty string.

Your final output must be in the following JSON format:
{"text": "your translation or transcription here"}

Example output structure:

<translation_process>
[Your detailed analysis of the text and translation process]
</translation_process>

{"text": "Your precise English translation or transcription, with [ambiguous French words] in brackets"}

Important: Your response should consist of the translation process analysis in the thinking block, followed by the JSON object containing only the translation or transcription. Do not include any other text, explanations, or error messages, and do not duplicate any of the work you did in the thinking block.
Here is the french text you need to translate:
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

def _delete_to_tag(response_txt:str, tag:str):
    end_idx = response_txt.find(tag)
    if end_idx != -1:
        response_txt = response_txt[end_idx + len(tag):]
    response_txt = response_txt.strip()
    return response_txt

def _clean_output(response_txt:str):
    response_txt = _delete_to_tag(response_txt, "</image_analysis>")
    response_txt = _delete_to_tag(response_txt, "</translation_process>")
    if response_txt.startswith("```json"):
        response_txt = response_txt[len("```json"):].strip()
    if response_txt.endswith("```"):
        response_txt = response_txt[:-len("```")].strip()

    print(f"response_txt pre JSON: {response_txt}")
    try:
        result = json.loads(response_txt)
        return result["text"]
    except:
        return ""

def _openai_extract_text(image_path, client):
    base64_image = _encode_image(image_path)
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{ "role": "user", "content": [{
                "type": "input_text",
                "text": OCR_PROMPT2
            },
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{base64_image}",
            },
        ],
        }]
    )
    result = _clean_output(response.output_text)
    print(f"Image {image_path} extracted text: {result}")
    return result

def _openai_translate_text(text, client):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[{ "role": "user", "content": [{
                "type": "input_text",
                "text": f"{TRANSLATION_PROMPT2}\n\n{text}"
            }],
        }]
    )
    result = _clean_output(response.output_text)
    return result


def _claude_extract_text(image_path, client):
    base64_image = _encode_image(image_path)
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": OCR_PROMPT2
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                    },
                ],
            },
            {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<image_analysis>"
                }
            ]
        }
        ],
    )
    result = _clean_output(response.content[0].text)
    print(f"Image {image_path} extracted text: {result}")
    return result

def _claude_translate_text(french_text, client):
    full_text = f"{TRANSLATION_PROMPT2}\n\n{french_text}"
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": full_text
                    },
                ],
            },
            {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "<translation_process>"
                }
            ]
        }
        ],
    )
    result = _clean_output(response.content[0].text)
    return result


def translate_text(text: str, model:str):
    if model == "openai":
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        return _openai_translate_text(text, client)
    elif model == "claude":
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        return _claude_translate_text(text, client)
    else:
        raise ValueError(f"Invalid model: {model}")

    if len(text) < 1:
        return ""
    response = client.responses.create(
        instructions=TRANSLATION_PROMPT,
        model="gpt-4o",
        input=text
    )
    return response.output_text