import json
import re

from utils.exceptions import (
    BadChoice,
    NoToolCall,
    TooManyToolCalls,
    InvalidToolCall,
    WrongToolName
)


class Tool:
    def __init__(
            self,
            name: str,
            description: str,
            parameters: dict
    ):
        self.type = "tool"
        self.name = name
        self.description = description
        self.parameters = parameters
        self.output_format = str

    @property
    def schema(self):
        return {
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    def __str__(self):
        return json.dumps(self.schema, ensure_ascii=False)

    def parse_result(self):
        """
        Parse the result of the tool execution.
        :param result: The result of the tool execution.
        :return: The parsed result.
        """
        raise NotImplementedError("parse_result method not implemented")


class SelectOnePlayer(Tool):
    def __init__(self, choices: list = None, abstain: bool = False):
        super().__init__(
            name="select_a_player",
            description="Select a player from the game and output the id. "
            "If abstenation is allowed, output 0.",
            parameters={
                "type": "object",
                "properties": {
                    "player_id": {
                        "type": "int",
                        "description": "The id of the player to select."
                    }
                },
                "required": ["player_id"]
            }
        )
        self.choices = choices if choices is not None else []
        self.abstain = abstain
        self.output_format = int

    def parse_result(self, result: str):
        """
        Parse the result of the tool execution.
        :param result: The result of the tool execution.
        :return: The parsed result.
        """
        # Find the player with the given id and return it
        try:
            chosen_id = int(result)
        except ValueError:
            raise InvalidToolCall('Output is not an integer!')

        if chosen_id == 0:
            if self.abstain:
                return None
            else:
                raise BadChoice("Abstain is not allowed!")

        for player in self.choices:
            if player.id == chosen_id:
                return player

        raise BadChoice(
            'Choice not possible!'
            f'Expected choice from {set(self.choices)}, got "{chosen_id}"'
        )


class DecideBinary(Tool):
    def __init__(self):
        super().__init__(
            name="decide_binary",
            description="Decide a binary choice and output the result.",
            parameters={
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "boolean",
                        "description": "The decision to make."
                    }
                },
                "required": ["decision"]
            }
        )
        self.output_format = bool

    def parse_result(self, result: str):
        """
        Parse the result of the tool execution.
        :param result: The result of the tool execution.
        :return: The parsed result.
        """
        # Find the player with the given id and return it
        decision = result.lower()
        if decision == "false":
            return False
        elif decision == "true":
            return True
        else:
            raise InvalidToolCall(
                'Choice not possible!'
                f'Expected choice from {set([True, False])},'
                f'got "{result}"'
            )
