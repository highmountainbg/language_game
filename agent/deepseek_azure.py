import os
import re

from loguru import logger
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.inference.models import UserMessage


endpoint = "https://DeepSeek-R1-ehrxo.eastus2.models.ai.azure.com"
key = os.environ.get("AZURE_DEEPSEEK_R1_SECRET_KEY")


def complete(params):
    client = ChatCompletionsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )
    return client.complete(params)


def print_stream(result):
    """
    Prints the chat completion with streaming.
    """
    for update in result:
        if update.choices:
            print(update.choices[0].delta.content, end="")


def generate(prompt: str):
    params = {
        'messages': [UserMessage(content=prompt)],
        'temperature': 0.6,
        'top_p': 0.95,
        'stream': False
    }
    logger.info(f"params: {params}")

    response = complete(params)
    content = response.choices[0]['message']['content']
    logger.info(f"content: {content}")

    reasoning = re.findall('(?<=<think>).*(?=</think>)', content, re.DOTALL)[0]
    answer = re.findall('(?<=</think>).*', content, re.DOTALL)[0]

    return reasoning, answer


if __name__ == '__main__':
    print(generate("hello"))
