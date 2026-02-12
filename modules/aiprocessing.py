import base64
import io
import json
import logging
import re
import traceback

import pandas as pd
from anthropic import Anthropic
from PIL import Image

logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def get_image_type(image: bytes):
    try:
        image_file = io.BytesIO(image)
        with Image.open(image_file) as img:
            return img.format.lower()
    except IOError as e:
        logger.debug(e)
        return None


def extract_from_df(df: pd.DataFrame, api_key: str):
    system_prompt = (
        "You are a data extraction model. You must return ONLY valid JSON, "
        "with no markdown formatting, no code blocks, and no explanatory text. "
        "Return just the raw JSON object."
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"data: ```{df.to_json()}```\n\n"
                "The data is a JSON dump of a cryptocurrency portfolio.\n"
                "Analyse it and identifying individual assets details.\n"
                "Extract the following informations:\n"
                "{\n"
                '  "assets": [\n'
                "    {\n"
                '      "name": "Bitcoin",\n'
                '      "amount": 0.5,\n'
                '      "symbol": "BTC",\n'
                '      "value": 15000.00\n'
                "    },\n"
                "    {\n"
                '      "name": "Ethereum",\n'
                '      "amount": 2.5,\n'
                '      "symbol": "ETH",\n'
                '      "value": 4500.50\n'
                "    }\n"
                "  ]\n"
                "}\n"
                'If no cryptocurrency data is found, return exactly: {"assets": []}\n'
                "Rules:\n"
                "- amount and value must be valid floats without currency symbols\n"
                "- symbol must be uppercase\n"
                "- name must be the full name of the cryptocurrency\n"
                "- Return ONLY the JSON object, nothing else\n"
            ),
        },
    ]
    return call_ai(messages, api_key, system_prompt)


def extract_from_img(bytes_data: bytes, api_key: str):
    type_image = get_image_type(bytes_data)
    if type_image is None:
        logger.debug("Invalid image.")
        return None, None
    else:
        logger.debug("Image type: %s", type_image)

    base64_image = base64.b64encode(bytes_data).decode("utf-8")

    system_prompt = (
        "You are a data extraction model. You must return ONLY valid JSON, "
        "with no markdown formatting, no code blocks, and no explanatory text. "
        "Return just the raw JSON object."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": f"image/{type_image}",
                        "data": base64_image,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "The image is a screenshot of a cryptocurrency portfolio.\n"
                        "Analyse it and identifying individual assets details.\n"
                        "Extract the following informations and format them exactly like this example:\n"
                        "{\n"
                        '  "assets": [\n'
                        "    {\n"
                        '      "name": "Bitcoin",\n'
                        '      "amount": 0.5,\n'
                        '      "symbol": "BTC",\n'
                        '      "value": 15000.00\n'
                        "    },\n"
                        "    {\n"
                        '      "name": "Ethereum",\n'
                        '      "amount": 2.5,\n'
                        '      "symbol": "ETH",\n'
                        '      "value": 4500.50\n'
                        "    }\n"
                        "  ]\n"
                        "}\n"
                        'If no cryptocurrency data is found, return exactly: {"assets": []}\n'
                        "Rules:\n"
                        "- amount and value must be valid floats without currency symbols\n"
                        "- symbol must be uppercase\n"
                        "- name must be the full name of the cryptocurrency\n"
                        "- Return ONLY the JSON object, nothing else\n"
                    ),
                },
            ],
        },
    ]
    return call_ai(messages, api_key, system_prompt)


def call_ai(messages: list, api_key: str, system_prompt: str = ""):
    # Create an Anthropic client
    client = Anthropic(api_key=api_key)
    total_tokens = 0

    try:
        logger.debug("Processing ...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )
    except Exception as e:
        logger.error("API call failed: %s", str(e))
        traceback.print_exc()
        return None, None

    # Extract text content from response
    content_text = ""
    for block in response.content:
        if block.type == "text":
            content_text += block.text

    total_tokens = response.usage.input_tokens + response.usage.output_tokens
    logger.debug("Number of tokens used: %d", total_tokens)
    logger.debug("Raw response content: %s", content_text[:200])

    if not content_text or "NO_DATA" in content_text:
        logger.debug("Invalid or empty response.")
        return None, total_tokens

    # Try to extract JSON from the response
    # Claude may wrap JSON in markdown code blocks or add explanatory text
    try:
        # First, try to parse the content directly as JSON
        parsed_json = json.loads(content_text)
        formatted_json = json.dumps(parsed_json)
        logger.debug("Successfully parsed JSON directly")
        return formatted_json, total_tokens
    except json.JSONDecodeError:
        # If that fails, try to extract JSON from markdown code blocks
        logger.debug("Direct JSON parse failed, trying to extract from markdown")

        # Look for JSON in markdown code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", content_text, re.DOTALL
        )
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1))
                formatted_json = json.dumps(parsed_json)
                logger.debug("Successfully extracted JSON from markdown block")
                return formatted_json, total_tokens
            except json.JSONDecodeError:
                pass

        # Look for JSON object without code blocks
        json_match = re.search(r'\{.*"assets"\s*:.*?\}', content_text, re.DOTALL)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(0))
                formatted_json = json.dumps(parsed_json)
                logger.debug("Successfully extracted JSON from text")
                return formatted_json, total_tokens
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON response. Content: %s", content_text)
        return None, total_tokens
