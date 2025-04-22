import os
import random
from collections import deque
from typing import Optional, Deque

import pandas as pd
from loguru import logger

from game import Game
from utils.constants import (
    BRANCHABLE,
    UNBRANCHABLE,
    BRANCHED,
    UNPLAYED,
    PLAYED,
    PLAYING,
    FINISHED,
    RESUMED,
)
from utils.path_manager import (
    get_data_dir,
    copy,
    validate_dir,
    remove,
)
from utils.utils import (
    unique_identifier,
    read_pickle,
    save_pickle,
    read_json,
    save_json,
)


class GameNode:
    """
    A node in the game sampler.
    Each node represents a state of the game.
    The node contains the game object, its status,
    and the data from the current process.
    """

    def __init__(
            self,
            sampler: "GameSampler",
            parent: Optional["GameNode"] = None,
            game: Optional[Game] = None,
            mode: str = "sample",
    ):
        self.id = unique_identifier()

        self.parent = parent
        if parent is not None:
            self.parent.children.append(self)

        self.children = []

        self.sampler = sampler
        self.sampler.add_node(self)

        if mode == "sample":
            self.game = game

            self.branch_status = BRANCHABLE
            self.game_status = UNPLAYED
            self.data = {
                "result": {},
                "detail": [],
                "observable_state": None,
            }

            # for concurrent sampling
            self.one_old = {}

            if self.game is not None:
                self.offload_game()

            # self.sampler.update_sample_queue(self)
        else:
            self.display = {}

    def __str__(self):
        return f"Node {self.id}"

    def __bool__(self):
        return True

    @property
    def is_root(self):
        """
        A node is root if its parent is None.
        """
        return self.parent is None

    @property
    def root(self):
        """
        Returns the root node of the tree.
        """
        curr = self
        while curr.parent is not None:
            curr = curr.parent
        return curr

    @property
    def is_leaf(self):
        """
        A node is leaf if it has no children.
        """
        return len(self.children) == 0

    @property
    def level(self):
        """
        Returns the level of the node.
        Level of the node equals to the number of steps from the root.
        Level of the root is 0.
        """
        if self.is_root:
            return 0
        return self.parent.level + 1

    @property
    def depth(self):
        """
        Depth is defined as branches from root to node (excluding the node).
        """
        if self.parent is None:
            return 0
        elif self.parent.branch_status == BRANCHED:
            return self.parent.depth + 1
        else:
            return self.parent.depth

    @property
    def depth_remain(self):
        """
        Number of depths remaining.
        The number of branches along a trajectory cannot exceed max_depth of the sampler.
        The depth_remain of root is always max_depth of the sampler.
        The parent's depth_remain is copied to the child at initialization.
        After a node is branched, the depth_remain of its children is reduced by 1.
        A node cannot branch if its depth_remain is 0.
        """
        return self.sampler.max_depth - self.depth

    def remove_child(self, child: "GameNode"):
        """
        Remove a child from the node.
        """
        self.children.remove(child)
        child.parent = None

    def add_child(self, child: "GameNode"):
        """
        Add a child to the node.
        """
        if child.parent:
            child.parent.remove_child(child)
        self.children.append(child)
        child.parent = self

    @property
    def game_path(self):
        """
        Returns the path to the game pickle file.
        The path is constructed using the game directory and the node id.
        """
        return os.path.join(self.sampler.game_dir, f"{self.id}.pkl")

    def load_game(self):
        """
        Load the game from the pickle file.
        """
        self.game = read_pickle(self.game_path)
        # link the game to the node
        self.game.node = self
        # The game is resumed by setting the status to RESUMED.
        if self.is_root:
            self.game.status = PLAYING
        else:
            self.game.status = RESUMED
        self.game.init_logger()

    def record_game_data(self):
        if self.is_root:
            ...
        else:
            self.data["observable_state"] = self.game.observable_state

    def update_data(self):
        """
        Update the data of the node.
        The data is a dictionary of player id to score.
        The data is updated in the sampler.
        """
        self.sampler.data[self.id] = {
            "id": self.id,
            "parent_id": self.parent.id if self.parent is not None else None,
            "branch_status": self.branch_status,
            "game_status": self.game_status,
            "level": self.level,
            "data": self.data,
        }
        for k, v in self.data.items():
            self.sampler.data[self.id][k] = v

    def record_result(self):
        """
        Record the result of the game.
        The result is a dictionary of player id to score.
        The result is recorded in the node and its ancestors.
        """
        if self.game is None:
            self.load_game()
        result = self.game.result
        self.offload_game()
        curr = self
        while curr is not None:
            for k, v in result.items():
                result_dict = curr.data["result"]
                if k not in result_dict:
                    result_dict[k] = v
                else:
                    result_dict[k] += v
            curr.update_data()
            curr = curr.parent
        logger.info(f"Recorded result: {result}")

    def offload_game(self):
        """
        Offload the game to the pickle file, and update node data.
        An offloaded node is not to be played again.
        """
        self.record_game_data()
        self.game.node = None
        save_pickle(self.game, self.game_path)
        self.game = None
        self.update_data()

    def set_game(
            self,
            game: Optional[Game] = None,
            game_path: Optional[str] = None,
            offload: bool = True
    ):
        """
        Set the game of the node.
        If game_path is provided, load the game from the path.
        """
        if game_path is not None:
            remove(self.game_path)
            copy(game_path, self.game_path)
            self.game = read_pickle(game_path)
            self.game.node = self
            if offload:
                self.offload_game()
        elif game is not None:
            self.game = game.clone()
            self.game.node = self
            if offload:
                self.offload_game()
        else:
            raise ValueError("Either game or game_path must be provided.")

    def create_child(self):
        """
        Create a child node from the current node.
        """
        assert len(self.children) < self.sampler.max_degree

        child_node = GameNode(
            sampler=self.sampler,
            parent=self
        )
        # The game pickle file of the current node is copied to the child node.
        # The child node is not played yet, so its status remains UNPLAYED.
        child_node.set_game(
            game_path=self.game_path,
            offload=True
        )
        return child_node

    def create_concurrent_nodes(self):
        """
        Create a concurrent child node from the current node.
        """
        curr = self.parent
        detail = self.data["detail"]
        self.branch_status = UNBRANCHABLE
        for player_id, one_old_game in self.one_old.items():
            child_node = GameNode(
                sampler=self.sampler,
                parent=curr
            )
            child_node.data["detail"] = [
                x for x in detail if x["player"] == player_id]
            child_node.game_status = PLAYED

            curr.set_game(game=one_old_game, offload=True)

            curr = child_node

        curr.set_game(game_path=self.game_path, offload=True)
        if self.game_status == FINISHED:
            curr.game_status = FINISHED
        self.parent.remove_child(self)
        self.sampler.remove_node(self)
        return curr

    def roll_out(self):
        """
        Play the game from the node to the end.
        """
        curr = self
        while True:
            curr.play_and_save()
            if curr.one_old:
                curr = curr.create_concurrent_nodes()
            if curr.game_status == FINISHED:
                curr.record_result()
                return curr
            curr = curr.create_child()

    def expand(self):
        """
        Expand the node by creating a new branch.
        """
        result = []
        while len(self.children) < self.sampler.max_degree:
            result.append(self.create_child())
        self.branch_status = BRANCHED
        return result

    def get_upstream_branchable(self):
        """
        Get all upstream branchable nodes, until the nearest branch.
        nodes are sorted by depth, from leaf to root.
        """
        curr = self.parent
        result = []
        while curr is not None and curr.branch_status != BRANCHED:
            if curr.branch_status == BRANCHABLE:
                result.append(curr)
            curr = curr.parent
        return result

    def play_and_save(self):
        """
        Play the game to the next checkpoint.
        """
        self.load_game()
        self.game.play_to_next_checkpoint()

        if self.game.status == FINISHED:
            self.game_status = FINISHED
        else:
            self.game_status = PLAYED
        self.offload_game()


class GameSampler:
    """
    A tree-like sampler of gameplay,
    consisting of nodes representing game states and store game data.
    """

    def __init__(
            self,
            name: str,
            max_depth: int,
            max_degree: int = 2,
            sample_id: Optional[str] = None
    ):
        self.name = name
        self.id = sample_id if sample_id is not None else unique_identifier()
        self.max_depth = max_depth
        self.max_degree = max_degree
        self.nodes = {}
        self.sample_queue: Deque['GameNode'] = deque()
        self.data = {}
        self.curr = None

        save_json(self.config, os.path.join(self.data_dir, 'config.json'))

    @property
    def root(self):
        """
        Returns the root node of the tree.
        If the root node is not set, return None.
        """
        if self.nodes:
            return list(self.nodes.values())[0].root
        return None

    def remove_node(self, node: "GameNode"):
        if node.id in self.nodes:
            del self.nodes[node.id]
            del self.data[node.id]
        if node in self.sample_queue:
            self.sample_queue.remove(node)

    @property
    def data_dir(self):
        """
        Returns the data directory for the sampler.
        """
        return get_data_dir(self.name, self.id)

    @property
    def game_dir(self):
        """
        Returns the directory where game data is stored.
        """
        return validate_dir(os.path.join(self.data_dir, ".game"))

    @property
    def config(self):
        """
        Returns the configuration of the game sampler.
        """
        return {
            "name": self.name,
            "sample_id": self.id,
            "max_depth": self.max_depth,
            "max_degree": self.max_degree
        }

    def add_node(self, node: GameNode):
        """
        Add a node to the sampler.
        If the node is the root, add it to the sample queue.
        """
        self.nodes[node.id] = node
        if node.is_root:
            self.sample_queue.appendleft(node)

    def update_sample_queue(self, node: GameNode):
        """
        Update the sample queue with the given node.
        If the node is the root, create a child add it to the sample queue.
        """
        if node.is_root:
            self.sample_queue.append(node.create_child())

    def sample_branching_points(self, node: GameNode):
        """
        Randomly select nodes to branch from the upstream branchable nodes.
        The number of branching points is limited by the depth_remain of the node.
        The nodes are sorted by depth, from leaf to root.
        """
        if node.depth_remain == 0:
            return []

        logger.info(f"Sampling branching points from node {node}")

        nodes = node.get_upstream_branchable()

        if len(nodes) <= node.depth_remain:
            branching_points = nodes
        else:
            branching_points = random.sample(nodes, node.depth_remain)

        branching_points.sort(key=lambda x: x.level)

        return branching_points

    def sample_trajectories(self):
        """
        Sample game trajectories.
        """
        # The sampling process is as follows:
        # Repeat steps 1-5 until the sample queue is empty.
        while self.sample_queue:
            # step 1. Take a node from the sample queue.
            curr = self.sample_queue.pop()
            # step 2. Roll out the game from the node to the end.
            leaf = curr.roll_out()
            # step 3. Sample branching points from the leaf node.
            branching_points = self.sample_branching_points(leaf)
            for branching_point in branching_points:
                # step 4. Expand the branching points to create new nodes.
                to_be_played = branching_point.expand()
                # step 5. Add the new nodes to the sample queue.
                self.sample_queue.extendleft(to_be_played)
        logger.success("Sampling finished.")

    def save(self):
        """
        Save the game sampler to a file.
        The game sampler is saved to a directory with the following structure:
        ├── data
        │   ├── game_name
        │   │   ├── game_id
        │   │   │   ├── config.json
        │   │   │   ├── archive.json
        │   │   │   ├── data.csv
        │   │   │   ├── game
        │   │   │   │   ├── node_id.pkl
        │   │   │   │   ├── ...
        """
        save_pickle(self, os.path.join(self.data_dir, "sampler.pkl"))
        save_json(self.data, os.path.join(self.data_dir, 'archive.json'))
        df = pd.DataFrame(self.data).T
        df.to_csv(os.path.join(self.data_dir, 'data.csv'))


def reconstruct_game_node(
        node_id: str,
        archive: dict,
        sampler: GameSampler,
        mode: str
) -> GameNode:
    """
    Reconstruct a game node from the archive.
    If the node is already in the sampler, return it.
    Otherwise, create a new node and add it to the sampler.
    """
    # Check if the node is already in the sampler
    # If it is, do nothing
    if node_id in sampler.nodes:
        return

    # Otherwise, create a new node and add it to the sampler
    node = GameNode(
        sampler=sampler,
        mode=mode
    )
    node.id = node_id
    value = archive[node_id]
    data = value["data"]
    if mode == "sample":
        node.data = data
    elif mode == "display":
        node.display["result"] = data["result"]
        node.display["observable_state"] = data["observable_state"]
        assert len(data["detail"]) <= 1
        if data["detail"]:
            node.display.update(data["detail"][-1])

    sampler.nodes[node_id] = node

    # Set the parent of the node
    parent_id = value["parent_id"]

    if parent_id is None:
        # If the parent is None, the node is the root
        pass

    elif parent_id in sampler.nodes:
        # If the parent is already in the sampler,
        # set the parent of the node to the parent in the sampler
        parent = sampler.nodes[parent_id]
        node.parent = parent
        parent.children.append(node)

    else:
        # Otherwise, reconstruct the parent node
        # and set the parent of the node to it
        parent = reconstruct_game_node(
            node_id=parent_id,
            archive=archive,
            sampler=sampler,
            mode=mode
        )
        node.parent = parent
        parent.children.append(node)
    return node


def reconstruct_game_sampler(
        archive: dict,
        config: dict,
        mode: str = "sample"
) -> GameSampler:
    """
    Reconstruct a game sampler from the archive.
    """
    assert mode in ["sample", "display"]
    sampler = GameSampler(
        name=config["name"],
        max_depth=config["max_depth"],
        max_degree=config["max_degree"],
        sample_id=config["sample_id"]
    )
    for node_id in archive.keys():
        reconstruct_game_node(node_id, archive, sampler, mode)
    return sampler


def reconstruct_game_sampler_for_sampling(path: str) -> GameSampler:
    """
    Reconstruct a game sampler given the game name and id.
    The game name and id are used to locate game directory.
    The game directory should contain the archive and config files.
    """
    config = read_json(os.path.join(path, 'config.json'))
    archive = read_json(os.path.join(path, 'archive.json'))
    sampler = reconstruct_game_sampler(archive, config)
    return sampler


def reconstruct_game_sampler_for_display(path: str) -> GameSampler:
    """
    Reconstruct a game sampler given the game name and id.
    The game name and id are used to locate game directory.
    The game directory should contain the archive and config files.
    """
    config = read_json(os.path.join(path, 'config.json'))
    archive = read_json(os.path.join(path, 'archive.json'))
    sampler = reconstruct_game_sampler(archive, config, mode="display")
    return sampler
