import json
import os
import pickle
import random
import sys
import uuid
from typing import List, Dict

from loguru import logger


def order_str(elements: List[str]) -> str:
    return "、".join(str(x) for x in elements)


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


def init_game_logger(game):
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    logger.add(os.path.join(game.data_dir, 'info.log'),
               format="{message}", level="INFO")
    logger.add(os.path.join(game.data_dir, 'trace.log'), level="TRACE")


def unique_identifier():
    return str(uuid.uuid4()).replace("-", "")


def save_pickle(obj, path):
    with open(path, 'wb') as f:
        pickle.dump(obj, f)


def read_pickle(path):
    with open(path, 'rb') as f:
        obj = pickle.load(f)
    return obj


def save_json(obj, path):
    with open(path, 'w') as f:
        json.dump(obj, f, ensure_ascii=False)


def read_json(path):
    with open(path, 'r') as f:
        return json.load(f)
