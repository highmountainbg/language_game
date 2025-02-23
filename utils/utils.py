import json
import pickle
import random
import re
from typing import List, Dict

from utils.exceptions import OutputFormatError


def read_json(path):
    with open(path, 'w') as f:
        return json.load(f)


def order_str(elements: List[str]) -> str:
    return "、".join(str(x) for x in elements)


def format_int(s: str) -> int:
    try:
        return int(re.findall('\d+', s)[-1])
    except:
        raise OutputFormatError


def format_bool(s: str) -> bool:
    try:
        matches = re.findall('true|false', s.lower())
        if matches[-1] == 'true':
            return True
        elif matches[-1] == 'false':
            return False
    except:
        raise OutputFormatError


def trim_str(s: str) -> str:
    s = s.strip()
    while '\n\n' in s:
        s = s.replace('\n\n', '\n')
    return s


def one_line_str(s: str) -> str:
    s = s.strip()
    s = s.replace('\n', '')
    return s


def random_select(elements: List[str], n: int) -> List[str]:
    return random.sample(elements, n)


def load_pickle(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def write_jsonl_single_line(data: Dict, path: str, mode):
    with open(path, mode, encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


def write_jsonl_multi_line(data: List[Dict], path: str, mode):
    for d in data:
        write_jsonl_single_line(d, path, mode)
