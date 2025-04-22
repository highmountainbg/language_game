import asyncio
import json
import os
from typing import (
    Dict,
    List,
)

import aiohttp
from loguru import logger

from utils.exceptions import BrainMalfunction


url = "https://api.deepseek.com/chat/completions"
api_key = os.environ.get("DEEPSEEK_API_KEY")
MODEL = "deepseek-reasoner"


async def complete_async(params):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=params) as response:
            return await response.text()


def generate(messages: List[Dict[str, str]]):
    try:
        params = {
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "temperature": 1.0,
            "response_format": {"type": "text"},
        }
        logger.trace(f"params: {params}")

        response_text = asyncio.run(complete_async(params))
        data = json.loads(response_text)
        message = data['choices'][0]['message']

        reasoning_content = message.get('reasoning_content')
        content = message.get('content')

        output = f"<think>\n{reasoning_content}\n</think>\n{content}"
        logger.trace("output: " + repr(output))
    except:
        raise BrainMalfunction("DeepSeek API error")

    return reasoning_content, content, output
