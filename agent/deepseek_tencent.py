import json
import os

from loguru import logger
from tencentcloud.common.common_client import CommonClient
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile


class NonStreamResponse(object):
    def __init__(self):
        self.response = ""

    def _deserialize(self, obj):
        self.response = json.dumps(obj)


SecretId = os.environ.get("TENCENT_SECRET_ID")
SecretKey = os.environ.get("TENCENT_SECRET_KEY")
cred = credential.Credential(SecretId, SecretKey)
httpProfile = HttpProfile()
httpProfile.endpoint = "lkeap.tencentcloudapi.com"
httpProfile.reqTimeout = 40000  # 流式接口可能耗时较长
clientProfile = ClientProfile()
clientProfile.httpProfile = httpProfile
common_client = CommonClient(
    "lkeap",
    "2024-05-22",
    cred,
    "ap-guangzhou",
    profile=clientProfile
)


def generate(prompt: str):
    params = {
        "Model": "deepseek-r1",
        "Messages": [{'Role': 'user', 'Content': prompt}],
        "Stream": False,
        "Temperature": 0.6,
    }
    logger.trace(f"params: {params}")

    resp = common_client._call_and_deserialize(
        action="ChatCompletions",
        params=params,
        resp_type=NonStreamResponse
    )

    content = json.loads(resp.response)['Choices'][0]['Message']
    reasoning = content['ReasoningContent']
    answer = content['Content']
    logger.trace(f"reasoning: {reasoning}")
    logger.trace(f"answer: {answer}")
    return reasoning, answer
