import base64
import pandas as pd
import io
import traceback
import logging
import pandas as pd

logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
from openai import OpenAI
from PIL import Image

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
    messages = [
        {"role": "system", "content": "You are a data extraction model."},
        {"role": "assistant", "content": f"data: ```{df.to_json()}```"},
        {
            "role": "user",
            "content": (
                "The data is a JSON dump of a cryptocurrency portfolio.\n"
                "Analyse it and identifying individual assets details.\n"
                "Extract the following informations:\n"
                "- Asset's name\n"
                "- Asset's numeric amount, without symbol (if applicable)\n"
                "- Asset's cryptocurrency symbol\n"
                "- Asset's fiat value (if applicable)\n"
                "Format the extracted data into a well-structured JSON format, ensuring that each asset is represented as an object within an array.\n"
                'If you can not find cryptocurrencies data in the image, return only the string "NO_DATA".'
            ),
        },
    ]
    return call_ai(messages, api_key)


def extract_from_img(bytes_data: bytes, api_key: str):

    type_image = get_image_type(bytes_data)
    if type_image is None:
        logger.debug("Invalid image.")
        return None, None
    else:
        logger.debug(f"Image type: {type_image}")

    base64_image = base64.b64encode(bytes_data).decode("utf-8")

    messages = [
        {"role": "system", "content": "You are a data extraction model."},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "The image is a screenshot of a cryptocurrency portfolio.\n"
                        "Analyse it and identifying individual assets details.\n"
                        "Extract the following informations:\n"
                        "- Asset's name\n"
                        "- Asset's numeric amount, without symbol (if applicable)\n"
                        "- Asset's cryptocurrency symbol\n"
                        "- Asset's fiat value (if applicable)\n"
                        "Format the extracted data into a well-structured JSON format, ensuring that each asset is represented as an object within an array.\n"
                        'If you can not find cryptocurrencies data in the image, return only the string "NO_DATA".'
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{type_image};base64,{base64_image}"
                    },
                },
            ],
        },
    ]
    return call_ai(messages, api_key)


def call_ai(messages: list, api_key: str):
    # Create an OpenAI object
    model = OpenAI(api_key=api_key)
    total_tokens = 0

    try:
        logger.debug("Processing ...")
        response = model.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        traceback.print_exc()
        return None, None

    message = response.choices[0].message
    total_tokens = response.usage.total_tokens
    logger.debug(f"Number of tokens used: {total_tokens}")

    if "NO_DATA" in message.content:
        logger.debug("Invalid image.")
        return None, total_tokens

    return message.content, total_tokens
