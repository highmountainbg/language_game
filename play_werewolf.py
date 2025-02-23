import os
import sys
from datetime import datetime

from loguru import logger

from config.werewolf_config import game_1
from game.werewolf import WerewolfGame
from utils.path_manager import get_game_data_dir
from utils.utils import load_pickle
from template.werewolf_template import WEREWOLF_GAME_NAME


if __name__ == '__main__':
    for _ in range(10):
        game_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        game_data_dir = get_game_data_dir(WEREWOLF_GAME_NAME, game_id, 0)

        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
        logger.add(os.path.join(game_data_dir, 'info.log'),
                format="{message}", level="INFO")
        logger.add(os.path.join(game_data_dir, 'trace.log'), level="TRACE")

        game_save_file = os.path.join(game_data_dir, 'game.pkl')
        game_archive_file = os.path.join(game_data_dir, 'game_finished.pkl')

        if os.path.exists(game_save_file):
            game = load_pickle(game_save_file)
            logger.info(f"Game loaded.")

        else:
            game = WerewolfGame(
                game_id=game_id,
                config=game_1
            )
        game.play()
