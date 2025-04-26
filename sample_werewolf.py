import random

from src.sampler import (
    GameSampler
)
from src.game.werewolf import (
    WerewolfGame,
    game_config_1
)

from src.utils.visualizer import create_html_tree


if __name__ == '__main__':
    random.seed(0)

    game = WerewolfGame(config=game_config_1)

    sampler = GameSampler(
        name=game.name,
        max_depth=4,
        max_degree=3,
        game=game
    )
    sampler.sample_trajectories()
    sampler.save()

    create_html_tree(sampler.name, sampler.id)
