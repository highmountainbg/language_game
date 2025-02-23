import os

root_dir = os.path.join(os.path.dirname(__file__), '..')
data_dir = os.path.join(root_dir, 'data')

def get_game_data_dir(game_name: str, game_id: str, branch: int = 0) -> str:
    return os.path.join(data_dir, game_name, game_id, str(branch))
