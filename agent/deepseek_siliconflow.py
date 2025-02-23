import asyncio
import aiohttp
import json
import os

from loguru import logger

from utils.exceptions import BrainError


url = "https://api.siliconflow.cn/v1/chat/completions"
key = os.environ.get("SILICONFLOW_SECRET_KEY")

# model = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
# model = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
model = "Pro/deepseek-ai/DeepSeek-R1"


async def complete_async(params):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=params) as response:
            return await response.text()


def generate(prompt: str):
    try:
        input_messages = [{"role": "user", "content": prompt}]
        params = {
            "model": model,
            "messages": input_messages,
            "stream": False,
            "temperature": 1.0,
            "response_format": {"type": "text"},
        }
        logger.trace(f"params: {params}")

        response_text = asyncio.run(complete_async(params))
        data = json.loads(response_text)
        message = data['choices'][0]['message']

        reasoning_content = message['reasoning_content']
        content = message['content']

        output = f"<think>\n{reasoning_content}\n</think>\n\n{content}"
        logger.trace("output: " + repr(output))
    except:
        raise BrainError

    return reasoning_content, content, input_messages, output


if __name__ == '__main__':
    print(generate("hello"))
