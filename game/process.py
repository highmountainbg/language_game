import os
import pickle
import re
import time
import uuid
from threading import Thread
from typing import Optional

from loguru import logger

from utils.path_manager import *


class Process:
    def __init__(
            self,
            parent: 'Process',
            name: Optional[str] = None
    ):
        self.parent = parent
        self.id = str(uuid.uuid4())
        if name is None:
            self.name = f'{self.__class__.__name__}_{self.id}'
        else:
            self.name = name
        self.nxt = None
        self.payload = {}

        self.sub = []
        self.__name_to_sub = {}
        self.step = 0
        self.locked = False  # for concurrency

    @property
    def game(self):
        return self.parent.game

    def create_subprocess(
            self,
            process_class,
            name: Optional[str] = None,
            **kwargs
    ):
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
        return self.__name_to_sub.get(name)

    @property
    def active_subprocesses(self):
        return [sub for sub in self.sub if not sub.locked]

    @property
    def condition(self):
        return True

    def update_parent_payload(self):
        if self.parent is not None:
            self.parent.payload.update(self.payload)

    def execute_subprocess(self, sub: 'Process'):
        assert sub in self.sub
        self.game.curr = sub

    def execute_subprocesses_sequential(self):
        if len(self.sub) > 0:
            for prev, nxt in zip(self.sub, self.sub[1:]):
                prev.nxt = nxt
            self.game.curr = self.sub[0]

    def execute_subprocesses_loop(self):
        if len(self.sub) > 0:
            for prev, nxt in zip(self.sub, self.sub[1:]+[self.sub[0]]):
                prev.nxt = nxt
            self.game.curr = self.sub[0]

    def execute_subprocesses_concurrent(self):
        thread_pool = []
        for sub in self.active_subprocesses:
            t = Thread(target=sub.run_concurrent)
            thread_pool.append(t)
            t.start()

        for t in thread_pool:
            t.join()

        assert len(self.active_subprocesses) == 0

    def clear_subprocesses(self):
        self.sub = []
        self.__name_to_sub = {}

    def exit(self):
        self.clear_subprocesses()
        self.step = 0
        self.game.curr = self.nxt
        self.game.save()

    @property
    def sequence(self):
        return sorted([m for m in dir(self) if re.match(r'step_\d+', m) is not None]) + ['exit']

    def run(self):
        if self.step == 0 and not self.condition:
            self.game.curr = self.nxt
        elif self.step >= len(self.sequence):
            self.game.curr = self.nxt
        else:
            method = getattr(self, self.sequence[self.step])
            self.step += 1
            method()

    def run_concurrent(self):
        if self.step > 0 or self.condition:
            while self.step < len(self.sequence) - 1:
                method = getattr(self, self.sequence[self.step])
                self.step += 1
                method()
        self.locked = True


class Game(Process):
    def __init__(
            self,
            name,
            game_id
    ):
        super().__init__(
            parent=None,
            name=name
        )
        self.id = game_id
        self.branch = 0
        os.makedirs(self.data_dir, exist_ok=True)

    def __str__(self):
        return f'{self.name}_{self.id}'

    @property
    def data_dir(self):
        return get_game_data_dir(self.name, self.id, self.branch)

    @property
    def game(self):
        return self

    def save(self):
        with open(os.path.join(self.data_dir, f'game.pkl'), 'wb') as f:
            pickle.dump(self, f)
        logger.info(f"Game saved.")

    def exit(self):
        os.rename(os.path.join(self.data_dir, 'game.pkl'),
                  os.path.join(self.data_dir, 'game_finished.pkl'))
