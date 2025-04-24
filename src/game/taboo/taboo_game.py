import json
import os
import random
import re

from loguru import logger

from agent import (
    Player,
    Tool,
)
from .taboo_template import (
    TABOO_GAME_NAME,
    TABOO_INFO,
)
from ..process import (
    Game,
    Process,
    checkpoint,
)


def choose_a_word():
    with open(os.path.join(os.path.dirname(__file__), "all_target_words.txt"), "r") as f:
        words = f.read().splitlines()
    return random.choice(words)


GAME_STILL_GOING = "GAME_STILL_GOING"
ATTACKER_WON = "ATTACKER_WON"
DEFENDER_WON = "DEFENDER_WON"
DRAW = "DRAW"


class Guess(Tool):
    def __init__(self):
        super().__init__(
            name="guess_the_word",
            description="Guess the word.",
            parameters={
                "type": "object",
                "properties": {
                    "guess": {
                        "type": "str",
                        "description": "Guess the word the attacker is trying to make you say."
                    }
                },
                "required": ["guess"]
            }
        )
        self.output_format = bool

    @staticmethod
    def parse_result(content: str) -> str:
        tool_calls = re.findall(
            r'(?<=<tool_call>).*?(?=</tool_call>)', content, re.DOTALL
        )
        assert len(tool_calls) == 1
        tool_call_json = json.loads(tool_calls[0])
        assert tool_call_json["name"] == "guess_the_word"
        return tool_call_json["arguments"]["guess"]


class Attacker(Player):
    """
    Werewolf game player class.
    """

    def __init__(self, game: "WerewolfGame", player_id: int):
        super().__init__(game=game, player_id=player_id)
        self.role = "attacker"

    def __str__(self):
        return "attacker"


class Defender(Player):
    """
    Werewolf game player class.
    """

    def __init__(self, game: "TabooGame", player_id: int):
        super().__init__(game=game, player_id=player_id)
        self.role = "defender"
        self.tools = [Guess]

    def __str__(self):
        return "defender"


class Moderator(Player):
    """
    Moderator class for the Werewolf game.
    """

    def __init__(self, game: "TabooGame"):
        super().__init__(game=game, player_id=0)
        self.role = "moderator"

    def __str__(self):
        return "moderator"

    def judge_attacker(self, text: str):
        if self.game.word in text:
            self.speak(f'Attacker said the word "{self.game.word}"!')
            self.game.defender_win()

    def judge_defender(self, text: str):
        try:
            guess = Guess.parse_result(text)
            if guess == self.game.word:
                self.speak("Correct guess.")
                self.game.defender_win()
            else:
                self.speak("Incorrect guess.")
                self.game.guesses_remaining -= 1
                if self.game.guesses_remaining == 0:
                    self.speak("No guesses remaining.")
                    self.game.attacker_win()
        except Exception:
            if self.game.word in text:
                self.speak(f'Defender said the word "{self.game.word}"!')
                self.game.attacker_win()

            if self.game.round == self.game.round_limit:
                self.speak("Round limit reached.")
                self.game.draw()


class AttackerAct(Process):
    """
    Attacker action class for the taboo game.
    """

    @checkpoint
    def speak(self):
        self.game.round += 1

        content = self.game.attacker.think_and_speak()
        self.game.moderator.judge_attacker(content)

    @property
    def sequence(self):
        return [
            self.speak
        ]


class DefenderAct(Process):
    """
    Defender action class for the taboo game.
    """

    @checkpoint
    def speak(self):
        content = self.game.defender.think_and_speak()
        self.game.moderator.judge_defender(content)

    @property
    def sequence(self):
        return [
            self.speak
        ]


class TabooGame(Game):
    info = TABOO_INFO
    name = TABOO_GAME_NAME

    def __init__(self, config):
        super().__init__(
            name=self.name,
            language=config.get("language", "en")
        )

        self.moderator = Moderator(game=self)
        self.attacker = Attacker(game=self, player_id=1)
        self.defender = Defender(game=self, player_id=2)

        self.word = config.get("word", choose_a_word())
        self.round_limit = config.get("round_limit", 10)
        self.guesses_remaining = config.get("guesses_allowed", 1)
        self.add_info()
        self.round = 0

    def add_info(self):
        self.info += f"The defender can only guess the word {self.guesses_remaining} time(s). If the defender runs out of guesses without guessing the word correctly, the defender loses.\n"
        self.info += f"The game is limited to {self.round_limit} turns. If nobody wins after {self.round_limit} turns, the game is drawn.\n"

    @property
    def observable_state(self):
        return f"Round: {self.round}."

    @property
    def players(self):
        return [
            self.attacker,
            self.defender
        ]

    def attacker_win(self):
        self.result = {
            'attacker_win': 1,
            'defender_win': 0,
            'draw': 0
        }
        self.moderator.speak("The attacker wins.")
        self.curr.nxt = self

    def defender_win(self):
        self.result = {
            'attacker_win': 0,
            'defender_win': 1,
            'draw': 0
        }
        self.moderator.speak("The defender wins.")
        self.curr.nxt = self

    def draw(self):
        self.result = {
            'attacker_win': 0,
            'defender_win': 0,
            'draw': 1
        }
        self.moderator.speak("The game is a draw.")
        self.curr.nxt = self

    def initialize(self):
        logger.info(f"initiate {self}")

        system = "You are playing a game.\n" + self.info
        detail = {
            "system": system,
            "word": self.word,
        }
        self.record_detail(detail)

        self.attacker.initialize_system(system)
        self.defender.initialize_system(system, include_tools=True)

        self.moderator.speak(
            msg="You are the defender.",
            audience=self.defender
        )
        self.moderator.speak(
            msg=f'You are the attacker. The word is "{self.game.word}".',
            audience=self.attacker
        )

    def attack_defend_loop(self):
        self.create_subprocess(AttackerAct)
        self.create_subprocess(DefenderAct)
        self.execute_subprocesses_loop()

    @property
    def sequence(self):
        return [
            self.initialize,
            self.attack_defend_loop,
            self.save
        ]
