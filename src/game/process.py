import os
import pickle
import sys
from copy import deepcopy
from threading import Thread
from typing import Optional

from loguru import logger

from utils.constants import (
    PLAYING,
    PAUSED,
    RESUMED,
    FINISHED,
)
from utils.path_manager import get_data_dir
from utils.utils import unique_identifier


class Process:
    """
    This class represents a process in the game.
    A process is a part of a game, can have subprocesses.
    """

    def __init__(
            self,
            parent: 'Process',
            name: Optional[str] = None
    ):
        self.parent = parent
        self._id = unique_identifier()
        if name is None:
            self.name = f'{self.__class__.__name__}_{self._id}'
        else:
            self.name = name
        self.nxt = None
        self.payload = {}

        self.sub = []
        self.__name_to_sub = {}
        self.step = 0
        self.locked = False  # for concurrency

    def __str__(self):
        result = []
        curr = self
        while not isinstance(curr, Game):
            result.append(curr.__class__.__name__)
            curr = curr.parent
        result.append(f"Round {self.game.round}")
        return " -> ".join(result[::-1])

    @property
    def step_str(self):
        """
        Returns the current step of the process.
        """
        assert self.step >= 0
        assert self.step <= len(self.sequence)

        if self.step == len(self.sequence):
            method = "exit"
        else:
            method = self.sequence[self.step].__name__

        return f'{self} -> {method}'

    @property
    def game(self):
        """
        Returns the game object this process is attached to.
        """
        return self.parent.game

    def create_subprocess(
            self,
            process_class,
            name: Optional[str] = None,
            **kwargs
    ):
        """
        Create a subprocess of the given class,
        and add it to the list of subprocesses.
        """

        sub = process_class(
            parent=self,
            name=name,
            **kwargs
        )
        self.sub.append(sub)

        assert sub.name not in self.__name_to_sub
        self.__name_to_sub[sub.name] = sub

        sub.parent = self
        sub.nxt = self
        if sub.game is None:
            sub.game = self.game

        return sub

    def find_subprocess(
            self,
            name: str
    ):
        """
        Find a subprocess by its name.
        """
        return self.__name_to_sub.get(name)

    @property
    def active_subprocesses(self):
        """
        Return a list of active subprocesses.
        A subprocess is considered active if it is not locked.
        """
        return [sub for sub in self.sub if not sub.locked]

    def update_parent_payload(self):
        """
        Update the parent process's payload with the current process's payload.
        This is used to pass data from the subprocess to the parent process.
        """
        if self.parent is not None:
            self.parent.payload.update(self.payload)

    def clear_subprocesses(self):
        """
        Clear all subprocesses.
        This is used to reset the subprocesses when necessary.
        """
        self.sub = []
        self.__name_to_sub = {}

    def exit(self):
        """
        This method is called when the process is finished.
        It clears all subprocesses and sets the current process to the next process.
        """
        self.clear_subprocesses()
        self.step = 0
        self.game.curr = self.nxt

    @property
    def sequence(self):
        """
        Returns a list of all the steps in the process in order.
        This is used to run the process in a specific order.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} should implement sequence property")

    def execute_subprocess(self, sub: 'Process'):
        """
        Set the current process to the subprocess.
        """
        assert sub in self.sub
        self.game.curr = sub

    def execute_subprocesses_sequential(self):
        """
        Line up the subprocesses in a chain,
        and point the current process to the first subprocess.
        """
        if len(self.sub) > 0:
            for prev, nxt in zip(self.sub, self.sub[1:]):
                prev.nxt = nxt
            self.game.curr = self.sub[0]

    def execute_subprocesses_loop(self):
        """
        Line up the subprocesses in a loop,
        the last subprocess points to the first subprocess,
        and point the current process to the first subprocess.
        """
        if len(self.sub) > 0:
            for prev, nxt in zip(self.sub, self.sub[1:]+[self.sub[0]]):
                prev.nxt = nxt
            self.game.curr = self.sub[0]

    def execute_subprocesses_concurrent(self):
        """
        Use threads to run all subprocesses concurrently.
        After all subprocesses are finished, returns to the main process.
        """
        thread_pool = []
        for sub in self.active_subprocesses:
            t = Thread(target=sub.run_concurrent)
            thread_pool.append(t)
            t.start()

        for t in thread_pool:
            t.join()

        assert len(self.active_subprocesses) == 0

    def run_current_step(self):
        """
        Run the current step of the process.
        """
        # Get the method corresponding to the current step
        method = self.sequence[self.step]
        # Increment the step counter
        method()
        self.step += 1

    def run(self):
        """
        This method is called to run the entire process.
        """
        if self.step == len(self.sequence):
            self.exit()
        else:
            self.run_current_step()

    def run_concurrent(self):
        """
        This method is called to run the process as a concurrent subprocess.
        """
        if self.step == len(self.sequence):
            return
        else:
            self.run_current_step()

        self.locked = True


def checkpoint(func):
    """
    Decorator to create a checkpoint in the game.
    When this decorator is applied, the first time the function is called,
    it will pause the game for the sampler to save the current state.
    The second time the function is called, it will resume the game,
    and actually run the function.
    """

    def wrapper(self: Process, *args, **kwargs):
        wrapper.__name__ = func.__name__

        if self.game.node is None:
            func(self, *args, **kwargs)
        elif self.game.status == PLAYING:
            self.game.status = PAUSED
            self.step -= 1
        elif self.game.status == RESUMED:
            self.game.status = PLAYING
            func(self, *args, **kwargs)

    return wrapper


def concurrent_checkpoint(func):
    """
    Decorator to create a checkpoint in the game for concurrent processes.
    This decorator is used to pause the game and save the current state.
    """

    def wrapper(self: Process, *args, **kwargs):
        wrapper.__name__ = func.__name__

        if self.game.node is None:
            func(self, *args, **kwargs)

        elif self.game.status == PLAYING:
            self.game.status = PAUSED
            self.step -= 1

        else:
            self.game.status = PLAYING
            orig_game = self.game.clone()
            active_players = [
                p.involved[0].id for p in self.game.curr.active_subprocesses]
            func(self, *args, **kwargs)
            for i, orig_sub in enumerate(orig_game.curr.sub):
                if orig_sub.involved[0].id not in active_players:
                    continue
                one_old_game = self.game.clone()
                sub = one_old_game.curr.sub[i]
                sub.step = 0
                sub.locked = False
                orig_player = orig_sub.involved[0]
                new_player = one_old_game.id_to_player[orig_player.id]
                new_player.memory = orig_player.memory
                self.game.node.one_old[orig_player.id] = one_old_game

    return wrapper


class Game(Process):
    """
    This class represents a game.
    A game is a special process that runs the entire game.
    """

    def __init__(
            self,
            name: str
    ):
        super().__init__(
            parent=None,
            name=name
        )
        self.curr = self

        # for sampling
        self.status = PLAYING
        self.node = None
        self.result = {}

    def __str__(self):
        return f'{self.name}_{self.id}'

    @property
    def id(self):
        """
        Returns the ID of the game.
        If the game is being sampled, returns the ID of the sampler;
        otherwise, returns the ID of the game.
        """
        if self.node is not None:
            return self.node.sampler.id
        return self._id

    @property
    def players(self):
        """
        Returns the players in the game.
        """
        raise NotImplementedError(
            "Game class should implement players property")

    @property
    def data_dir(self):
        """
        Returns the directory where the game data is stored.
        """
        return get_data_dir(self.name, self.id)

    def init_logger(self):
        """
        Initialize the logger for the game.
        The logger is used to log the game events and data.
        """
        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
        logger.add(os.path.join(self.data_dir, 'info.log'),
                   format="{message}", level="INFO")
        logger.add(os.path.join(self.data_dir, 'trace.log'), level="TRACE")

    @property
    def game(self):
        """
        Returns self.
        Overrides the game property in the Process class.
        """
        return self

    @property
    def observable_state(self):
        """
        Returns the observable state of the game.
        This is used to get the current state of the game.
        """
        raise NotImplementedError(
            "Game class should implement observable_state property")

    def clone(self):
        """
        Clone the game object.
        This method is used to create a copy of the game object.
        If the game is being sampled, it will not clone the node.
        The cloned game object will not be attached to a sampler.
        """
        node = self.node
        self.node = None
        result = deepcopy(self)
        self.node = node

        return result

    def record_detail(self, data):
        """
        Record the detail of a prompt by the agent.
        This method is used to save the prompt and the generated content.
        """
        if self.node is not None:
            self.node.data["detail"].append(data)

    def save(self):
        """
        If the game is being sampled, puts the current process into the sampler.
        Otherwise, it saves the game to a file.
        """
        if self.node is None:
            with open(os.path.join(self.data_dir, 'game.pkl'), 'wb') as f:
                pickle.dump(self, f)
            logger.info("Game saved.")

    def exit(self):
        """
        This method is called when the game is finished.
        Saves the game, and renames the file to 'game_finished.pkl'.
        """

        self.status = FINISHED
        self.curr = None
        logger.remove()

        if os.path.exists(os.path.join(self.data_dir, 'game.pkl')):
            os.rename(os.path.join(self.data_dir, 'game.pkl'),
                      os.path.join(self.data_dir, 'game_finished.pkl'))

    def play(self):
        """
        Start or resume playing the game.
        """
        while self.curr is not None:
            self.curr.run()
        self.save()

    def play_to_next_checkpoint(self):
        """
        Play the game until the next checkpoint.
        """
        while self.curr is not None and self.status in (PLAYING, RESUMED):
            self.curr.run()
