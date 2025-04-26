import random

from src.sampler import (
    GameSampler,
    GameNode
)
from src.game.taboo import TabooGame
from src.utils.visualizer import create_html_tree


if __name__ == '__main__':
    random.seed(50)

    game = TabooGame(config={"round_limit": 5})

    sampler = GameSampler(
        name=game.name,
        max_depth=5,
        max_degree=4
    )

    root_node = GameNode(
        sampler=sampler,
        game=game
    )

    sampler.sample_trajectories()

    sampler.save()

    create_html_tree(sampler.name, sampler.id)
