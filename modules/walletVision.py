import base64
import json
import argparse
import io
import traceback
import logging
from dotenv import load_dotenv
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


def extract_crypto(bytes_data, api_key):
    # Create an OpenAI object
    model = OpenAI(api_key=api_key)
    total_tokens = 0

    type_image = get_image_type(bytes_data)
    if type_image is None:
        logger.debug("Invalid image.")
        return None, None
    else:
        logger.debug(f"Image type: {type_image}")

    base64_image = base64.b64encode(bytes_data).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "The image contains the content of a cryptocurrency wallet. Extract from the image the amount of each tokens and return the result as a raw json object without extra informations. If you can find any cryptocurrency data in the image, return the string 'NO_DATA'.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{type_image};base64,{base64_image}"
                    },
                },
            ],
        }
    ]

    try:
        logger.debug("Processing image...")
        response = model.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=1024,
        )
    except Exception as e:
        traceback.print_exc()
        return None, None

    message = response.choices[0].message
    nbr_tokens = response.usage.total_tokens
    total_tokens += nbr_tokens
    logger.debug(f"Number of tokens used: {nbr_tokens}")

    if "NO_DATA" in message.content:
        logger.debug("Invalid image.")
        return None, None

    messages = [{"role": "assistant", "content": message.content}]

    messages.append(
        {"role": "user", "content": "Convert to a raw well formated JSON object."}
    )

    try:
        logger.debug("Converting to JSON...")
        response = model.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        traceback.print_exc()
        return None, None

    message = response.choices[0].message
    nbr_tokens = response.usage.total_tokens
    total_tokens += nbr_tokens
    logger.debug(f"Number of tokens used: {nbr_tokens}")

    message_json = json.loads(message.content)

    return message_json, total_tokens


if __name__ == "__main__":
    load_dotenv()

    # Créer un objet ArgumentParser
    parser = argparse.ArgumentParser(description="Description du programme")

    # Ajouter les arguments attendus
    parser.add_argument("-f", "--file", type=str, help="Chemin vers le fichier")

    # Parser les arguments
    args = parser.parse_args()

    with open(args.file, "rb") as f:
        message_json, tokens = extract_crypto(f.read())
        logger.debug(f"Ouput: {message_json}")
        logger.debug(f"Tokens used: {tokens}")
