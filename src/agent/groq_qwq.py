import asyncio
import os
import re
from typing import (
    Dict,
    List,
)

from groq import AsyncGroq
from loguru import logger

from utils.exceptions import BrainMalfunction


api_key = os.environ.get("GROQ_API_KEY")
MODEL = "qwen-qwq-32b"


async def complete_async(params):
    client = AsyncGroq(api_key=api_key)
    return await client.chat.completions.create(**params)


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

        response = asyncio.run(complete_async(params))
        output = response.choices[0].message.content

        reasoning_content = re.findall(
            r"(?<=<think>).*?(?=</think>)", output, re.DOTALL)[0].strip()
        content = re.sub(r"<think>.*?</think>",
                         "", output, flags=re.DOTALL).strip()

        output = f"<think>\n{reasoning_content}\n</think>\n{content}"
        logger.trace("output: " + repr(output))
    except:
        raise BrainMalfunction("GROQ API error")

    return reasoning_content, content, output
