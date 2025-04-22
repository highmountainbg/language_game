import os
import shutil


root_dir = os.path.join(os.path.dirname(__file__), '../..')
data_dir = os.path.join(root_dir, 'data')


def validate_dir(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def get_data_dir(name: str, _id: str) -> str:
    directory = os.path.join(data_dir, name, _id)
    return validate_dir(directory)


def copy(src: str, dst: str):
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy(src, dst)


def remove(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
