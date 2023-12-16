import base64
import json
import argparse
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image


def image_b64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')
    
def get_image_type(image_path):
    try:
        with Image.open(image_path) as img:
            return img.format.lower()
    except IOError as e:
        print(e)
        return None

def extract_crypto(image_path):
    # Create an OpenAI object
    model = OpenAI()
    total_tokens = 0

    type_image = get_image_type(image_path)
    if type_image is None:
        print('Invalid image.')
        return None, None 
    else:
        print(f'Image type: {type_image}')
    
    base64_image = image_b64(image_path)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "The image contains the content of a cryptocurrency wallet. Extract from the image the amount of each tokens and return the result as a raw json object without extra informations. If you can find any cryptocurrency data in the image, return the string 'NO_DATA'."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{type_image};base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    try:
        print('Processing image...')
        response = model.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=1024,
        )
    except Exception as e:
        print(e)
        return None, None 

    message = response.choices[0].message
    nbr_tokens = response.usage.total_tokens
    total_tokens += nbr_tokens
    print(f'Number of tokens used: {nbr_tokens}')

    if 'NO_DATA' in message.content:
        print('Invalid image.')
        return None, None

    messages = [
        {
        "role": "assistant",
        "content": message.content
        }
    ]

    messages.append({
        "role": "user",
        "content": "Convert to a raw well formated JSON object."
    })

    try:
        print('Converting to JSON...')
        response = model.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        print(e)
        return None, None 
        
    message = response.choices[0].message
    nbr_tokens = response.usage.total_tokens
    total_tokens += nbr_tokens
    print(f'Number of tokens used: {nbr_tokens}')

    message_json = json.loads(message.content)

    return message_json, total_tokens

if __name__ == "__main__":
    load_dotenv()

    # Créer un objet ArgumentParser
    parser = argparse.ArgumentParser(description='Description du programme')

    # Ajouter les arguments attendus
    parser.add_argument('-f', '--file', type=str, help='Chemin vers le fichier')

    # Parser les arguments
    args = parser.parse_args()

    message_json, tokens = extract_crypto(args.file)
    print(f"Ouput: {message_json}")
    print(f"Tokens used: {tokens}")
