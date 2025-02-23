import random
from typing import List, Union, Dict, Optional

from loguru import logger

from agent.player import Player
from game.process import Game, Process
from template.werewolf_template import *
from utils.utils import *


class WerewolfGamePlayer(Player):
    def __init__(self, game: "WerewolfGame", player_id: int):
        super().__init__(game=game, player_id=player_id)
        self.role = None
        self.alive = True

    @property
    def is_sheriff(self):
        return self == self.game.sheriff

    def __bool__(self):
        return self.alive


class Moderator(WerewolfGamePlayer):
    def __init__(self, game: "WerewolfGame"):
        super().__init__(game=game, player_id=0)
        self.role = "裁判"
        self.alive = True

    def __str__(self):
        return "裁判"


class Werewolf(WerewolfGamePlayer):
    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "狼人"
        self.team = "狼人"
        self.teammates = self.game.werewolves


class Townsfolk(WerewolfGamePlayer):
    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "平民"
        self.team = "村民"


class Seer(WerewolfGamePlayer):
    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "预言家"
        self.team = "村民"


class Witch(WerewolfGamePlayer):
    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "女巫"
        self.team = "村民"
        self.healing_remain = True
        self.poison_remain = True


class Hunter(WerewolfGamePlayer):
    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "猎人"
        self.team = "村民"


def get_role(role_str: str) -> WerewolfGamePlayer:
    str_to_role = {
        "werewolf": Werewolf,
        "seer": Seer,
        "witch": Witch,
        "townsfolk": Townsfolk,
        "hunter": Hunter
    }
    assert role_str in str_to_role
    return str_to_role.get(role_str)


class WerewolfGameProcess(Process):
    def __init__(
        self,
        parent: Union["WerewolfGame", "WerewolfGameProcess"],
        name: Optional[str] = None,
        involved: Union[WerewolfGamePlayer,
                        List[WerewolfGamePlayer], None] = None,
        **kwargs
    ):
        super().__init__(parent=parent, name=name)
        if involved is None:
            self.involved = self.alive_players
        elif type(involved) != list:
            self.involved = [involved]
        else:
            self.involved = involved

    @property
    def players(self):
        return self.game.players

    @property
    def moderator(self):
        return self.game.moderator

    @property
    def werewolves(self):
        return self.game.werewolves

    @property
    def villagers(self):
        return self.game.villagers

    @property
    def townsfolks(self):
        return self.game.townsfolks

    @property
    def seer(self):
        return self.game.seer

    @property
    def witch(self):
        return self.game.witch

    @property
    def hunter(self):
        return self.game.hunter

    @property
    def alive_players(self):
        return self.game.alive_players

    @property
    def dead_players(self):
        return self.game.dead_players


class Kill(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cause = kwargs.get('cause')

    def announce_death(
        self,
        deaths: List[WerewolfGamePlayer]
    ):
        if deaths:
            self.moderator.speak(
                f"{order_str(sorted(deaths, key=lambda x: x.id))}死亡。")
        else:
            self.moderator.speak("无人死亡。")

        if self.game.reveal_upon_death:
            for dead in deaths:
                self.moderator.speak(f"{dead}是{dead.role}。")

    def step_1(self):
        self.announce_death(self.cause.keys())

        for dead in sorted(self.cause.keys(), key=lambda x: self.cause.get(x)):
            self.create_subprocess(
                Die,
                involved=dead,
                cause=self.cause.get(dead)
            )
        self.execute_subprocesses_sequential()


class HunterKill(WerewolfGameProcess):
    @property
    def condition(self):
        return self.hunter is not None and not self.hunter.alive

    def step_1(self):
        self.moderator.speak(
            "你要对谁开枪？输出目标序号，不开枪输出0。",
            audience=self.hunter
        )

    def step_2(self):
        target = self.hunter.select_one_player()
        if target is not None:
            self.moderator.speak(f"{self.hunter}猎人开枪击杀{target}。")
            self.payload['hunter_kill'] = target

    def step_3(self):
        target = self.payload.get('hunter_kill')
        if target:
            kill = self.create_subprocess(
                Kill,
                cause={target: 'hunter kill'}
            )
            self.execute_subprocess(kill)


class SheriffSuccession(WerewolfGameProcess):
    @property
    def condition(self):
        return self.game.sheriff_flag and not self.game.sheriff.alive

    def step_1(self):
        self.moderator.speak(
            "你要把警徽移交给谁？输出目标序号，不移交输出0。",
            audience=self.game.sheriff
        )

    def step_2(self):
        dead_sheriff = self.game.sheriff
        target = dead_sheriff.select_one_player()

        if target is not None:
            self.moderator.speak(f"{dead_sheriff}将警徽移交给{target}。")
            self.game.sheriff = target
        else:
            self.moderator.speak(f"{dead_sheriff}没有移交警徽，警徽流失。")


class Die(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cause = kwargs.get('cause')
        self.dead = None

    @property
    def condition(self):
        self.dead = self.involved[0]
        return isinstance(self.dead, WerewolfGamePlayer) and self.dead.alive

    def step_1(self):
        self.dead = self.involved[0]
        self.dead.alive = False
        if self.game.over:
            self.nxt = self.game

    def step_2(self):
        if self.dead == self.hunter and self.cause in ['a_werewolf', 'lynch']:
            hunter_kill = self.create_subprocess(HunterKill)
            self.execute_subprocess(hunter_kill)

    def step_3(self):
        if self.dead.is_sheriff:
            sheriff_succession = self.create_subprocess(SheriffSuccession)
            self.execute_subprocess(sheriff_succession)


class ConsolidateMemory(WerewolfGameProcess):
    @property
    def player(self):
        return self.involved[0]

    @property
    def condition(self):
        return self.player.alive

    def step_1(self):
        self.player.consolidate_memory()


class Speak(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speaker = kwargs.get('speaker')

    @property
    def condition(self):
        return self.speaker.alive

    def step_1(self):
        self.speaker.think_and_speak(self.involved)


class Vote(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.abstain = kwargs.get('abstain', True)

    @property
    def condition(self):
        return self.involved[0].alive and isinstance(self.parent, Voting)

    def step_1(self):
        voter = self.involved[0]
        self.payload[voter] = voter.select_one_player(abstain=self.abstain)
        self.update_parent_payload()


class Voting(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.announcement = kwargs.get('announcement')
        self.abstain = kwargs.get('abstain', True)
        self.tie = kwargs.get('abstain', True)

    def announce_votes(
        self,
        votes: Dict[WerewolfGamePlayer, WerewolfGamePlayer],
        audience: Optional[List[WerewolfGamePlayer]] = None,
    ) -> List[WerewolfGamePlayer]:

        target_to_voter = {}
        for voter, target in votes.items():
            if target not in target_to_voter:
                target_to_voter[target] = []
            target_to_voter[target].append(voter)

        msg = ""
        temp = []
        high_score = 0
        for target, voters in target_to_voter.items():
            # abstain
            if not target:
                msg += f"{order_str(voters)}弃权，"
                continue

            msg += f"{order_str(voters)}投给了{target}，"
            if isinstance(self.parent, Accusation):
                score = sum(1.5 if voter.is_sheriff else 1 for voter in voters)
            else:
                score = len(voters)
            if score > high_score:
                high_score = score
                temp = [target]
            elif score == high_score:
                temp.append(target)

        # count votes
        if len(temp) == 1:
            msg += f"投票的结果是{temp[0]}。"
            result = temp[0]
        elif len(temp) == 0:
            msg += f"没有有效票，投票没有结果。"
            result = None
        else:
            msg += f"{order_str(temp)}票数最多且相同，投票没有结果。"
            result = None

        self.moderator.speak(msg, audience=audience)
        logger.info(f"vote result: {result}")
        return result

    def step_1(self):
        msg = self.announcement
        if self.abstain:
            msg += "，输出目标序号，弃权输出0。"
        else:
            msg += "，输出目标序号，不能弃权。"
        self.moderator.speak(msg, self.involved)

    def step_2(self):
        for voter in self.involved:
            self.create_subprocess(
                process_class=Vote,
                involved=voter,
                abstain=self.abstain
            )
        self.execute_subprocesses_concurrent()

    def step_3(self):
        self.payload['result'] = self.announce_votes(
            votes=self.payload,
            audience=self.involved
        )
        self.update_parent_payload()

    def step_4(self):
        self.clear_subprocesses()
        for player in self.involved:
            self.create_subprocess(
                process_class=ConsolidateMemory,
                involved=player
            )
        self.execute_subprocesses_concurrent()


class Discussion(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = []
        self.announcement = kwargs.get('announcement')

    def step_1(self):
        self.moderator.speak(self.announcement, self.involved)

    def step_2(self):
        for speaker in self.involved:
            self.create_subprocess(
                process_class=Speak,
                speaker=speaker,
                involved=self.involved
            )
        self.execute_subprocesses_sequential()

    def step_3(self):
        self.clear_subprocesses()
        for player in self.involved:
            self.create_subprocess(
                process_class=ConsolidateMemory,
                involved=player
            )
        self.execute_subprocesses_concurrent()


class SeerAct(WerewolfGameProcess):
    @property
    def condition(self):
        return self.seer is not None and self.seer.alive and isinstance(self.parent, Night)

    def step_1(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}夜-预言家行动\n{'='*64}")
        self.moderator.speak("你要查验谁？输出目标序号。", self.seer)

    def step_2(self):
        target = self.seer.select_one_player(abstain=False)
        self.moderator.speak(f"{target}是{target.team}。", self.seer)

    def step_3(self):
        consolidate_memory = self.create_subprocess(
            process_class=ConsolidateMemory,
            involved=self.seer
        )
        self.execute_subprocess(consolidate_memory)


class WerewolvesAct(WerewolfGameProcess):
    @property
    def condition(self):
        return isinstance(self.parent, Night)

    def step_1(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}夜-狼人行动-讨论\n{'='*64}")
        self.payload["werewolves_target"] = None
        discussion = self.create_subprocess(
            process_class=Discussion,
            involved=self.werewolves,
            announcement=f"狼人{order_str(self.werewolves)}，现在秘密讨论，请依次发言。"
        )
        self.execute_subprocess(discussion)

    def step_2(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}夜-狼人行动-投票\n{'='*64}")
        voting = self.create_subprocess(
            process_class=Voting,
            involved=self.werewolves,
            announcement="现在开始秘密投票选择击杀对象",
            abstain=True
        )
        self.execute_subprocess(voting)

    def step_3(self):
        self.payload["werewolves_target"] = self.payload.pop('result')
        self.update_parent_payload()


class Heal(WerewolfGameProcess):
    @property
    def condition(self):
        return self.witch is not None and self.witch.alive and self.witch.healing_remain

    @property
    def night(self):
        return self.parent.parent

    def step_1(self):
        assert isinstance(self.parent, WitchAct)
        target = self.night.payload['werewolves_target']
        if target is not None:
            self.moderator.speak(
                f"今夜狼人的目标是{target}，你要使用解药吗？",
                self.game.witch
            )
        else:
            self.moderator.speak("今夜狼人没有杀人", self.game.witch)

    def step_2(self):
        if self.night.payload['werewolves_target'] is not None:
            result = self.witch.decide_binary()
            self.payload['heal'] = result
            if result:
                self.witch.healing_remain = False
            self.update_parent_payload()


class Poison(WerewolfGameProcess):
    @property
    def condition(self):
        return self.witch is not None and self.witch.alive and self.witch.poison_remain

    def step_1(self):
        assert isinstance(self.parent, WitchAct)
        self.moderator.speak(
            f"你要对谁使用毒药？输出目标序号，不使用输出0。",
            self.witch
        )

    def step_2(self):
        result = self.witch.select_one_player(abstain=True)
        self.payload['poison_target'] = result
        if result:
            self.witch.poison_remain = False
        self.update_parent_payload()


class WitchAct(WerewolfGameProcess):
    @property
    def condition(self):
        return self.witch is not None and self.witch.alive

    def step_1(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}夜-女巫行动\n{'='*64}")
        
        self.payload['heal'] = False
        self.payload['poison_target'] = None

        heal = self.create_subprocess(Heal)
        self.execute_subprocess(heal)

    def step_2(self):
        if not self.payload['heal']:
            poison = self.create_subprocess(Poison)
            self.execute_subprocess(poison)

    def step_3(self):
        self.update_parent_payload()
        self.clear_subprocesses()
        consolidate_memory = self.create_subprocess(
            process_class=ConsolidateMemory,
            involved=self.witch
        )
        self.execute_subprocess(consolidate_memory)


class SheriffElection(WerewolfGameProcess):
    @property
    def condition(self):
        return self.game.round == 1 and self.game.sheriff_flag

    def appoint_sheriff(
        self,
        player: Optional[WerewolfGamePlayer]
    ):
        if player is None:
            self.moderator.speak("本局游戏没有警长。")
        else:
            self.moderator.speak(f"{player}当选警长。")
            self.game.sheriff = player

    def step_1(self):
        logger.info(f"\n{'='*64}\n警长选举-讨论\n{'='*64}")
        discussion = self.create_subprocess(
            Discussion,
            announcement="现在开始警长选举讨论，请依次发言。"
        )
        self.execute_subprocess(discussion)

    def step_2(self):
        logger.info(f"\n{'='*64}\n警长选举-投票\n{'='*64}")
        voting = self.create_subprocess(
            Voting,
            announcement="现在开始投票选举警长",
            abstain=True
        )
        self.execute_subprocess(voting)

    def step_3(self):
        self.appoint_sheriff(self.payload['result'])


class Accusation(WerewolfGameProcess):
    def step_1(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}天-指控狼人-讨论\n{'='*64}")
        discussion = self.create_subprocess(
            Discussion,
            name="accusation discussion",
            announcement="现在开始指控狼人讨论，请依次发言。"
        )
        self.execute_subprocess(discussion)

    def step_2(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}天-指控狼人-投票\n{'='*64}")
        voting = self.create_subprocess(
            Voting,
            announcement="现在开始投票指控狼人",
            abstain=True
        )
        self.execute_subprocess(voting)

    def step_3(self):
        target = self.payload['result']
        if target:
            kill = self.create_subprocess(
                Kill,
                cause={target: 'lynch'}
            )
            self.execute_subprocess(kill)


class Night(WerewolfGameProcess):
    @property
    def condition(self):
        return isinstance(self.nxt, Day)

    def step_1(self):
        self.game.round += 1
        self.payload = {
            'deaths': {},
            'werewolves_target': None,
            'heal': False,
            'poison_target': None
        }
        logger.info(f"\n{'='*64}\n第{self.game.round}夜\n{'='*64}")
        self.moderator.speak(f"第{self.game.round}夜，天黑了。")

    def step_2(self):
        seer_act = self.create_subprocess(SeerAct)
        self.execute_subprocess(seer_act)

    def step_3(self):
        werewolves_act = self.create_subprocess(WerewolvesAct)
        self.execute_subprocess(werewolves_act)

    def step_4(self):
        witch_act = self.create_subprocess(WitchAct)
        self.execute_subprocess(witch_act)

    def step_5(self):
        if not self.payload['heal'] and self.payload['werewolves_target']:
            target = self.payload['werewolves_target']
            self.payload['deaths'][target] = 'a_werewolf'
        if self.payload['poison_target']:
            self.payload['deaths'][self.payload['poison_target']] = 'poison'
        self.clear_subprocesses()


class Day(WerewolfGameProcess):
    @property
    def condition(self):
        return isinstance(self.nxt, Night)

    def step_1(self):
        self.payload = {}
        logger.info(f"\n{'='*64}\n第{self.game.round}天\n{'='*64}")
        self.moderator.speak(f"第{self.game.round}天，天亮了。")

    def step_2(self):
        sheriff_election = self.create_subprocess(SheriffElection)
        self.execute_subprocess(sheriff_election)

    def step_3(self):
        logger.info(f"\n{'='*64}\n第{self.game.round}天-指控狼人\n{'='*64}")
        kill = self.create_subprocess(Kill, cause=self.nxt.payload['deaths'])
        self.execute_subprocess(kill)

    def step_4(self):
        accusation = self.create_subprocess(Accusation)
        self.execute_subprocess(accusation)

    def step_5(self):
        self.clear_subprocesses()


class WerewolfGame(Game):
    info = WEREWOLF_INFO
    name = WEREWOLF_GAME_NAME

    def __init__(self, game_id, config):
        super().__init__(self.name, game_id)
        self.game_id = game_id

        self.set_up = config["set_up"]
        # number of players does not include moderator
        self.number_of_players = sum(self.set_up.values())

        self.__players: List[WerewolfGamePlayer] = []  # exluding moderator
        self.id_to_player: Dict[int, WerewolfGamePlayer] = {}

        self.moderator = Moderator(game=self)
        self.seer = None
        self.witch = None
        self.hunter = None

        self.sheriff_flag = config["sheriff"]
        self.sheriff = None
        self.reveal_upon_death = config["reveal_upon_death"]
        self.add_info()

        self.round = 0
        self.curr = self

    def add_info(self):
        if self.reveal_upon_death:
            self.info += "玩家死亡后会展示角色身份。"
        else:
            self.info += "玩家死亡后不会展示角色身份。"

        if self.sheriff_flag:
            self.info += "第一天公布死者之前有竞选警长环节，警长在指控狼人投票中有1.5票。"

        self.info += f"\n本场游戏玩家为{order_str(self.alive_players)}，"
        self.info += f"其中有{self.set_up['werewolf']}个狼人，"
        self.info += f"{self.set_up['townsfolk']}个平民，"
        self.info += f"{self.set_up['seer']}个预言家，"
        self.info += f"{self.set_up['witch']}个女巫。"
        self.info += f"{self.set_up['witch']}个猎人。\n"

    @property
    def observable_state(self):
        result = f"目前{order_str(self.alive_players)}存活，{order_str(self.dead_players)}已出局。"
        if self.sheriff:
            result += f"警长是{self.sheriff}。"
        return result

    @property
    def over(self):
        if len(self.villagers) == 0:
            msg = "狼人胜利。"
            self.moderator.speak(msg)
            logger.success(msg)
            return True

        elif len(self.werewolves) == 0:
            msg = "村民胜利。"
            self.moderator.speak(msg)
            logger.success(msg)
            return True

        return False

    @property
    def players(self):
        return self.__players

    @property
    def alive_players(self):
        return [player for player in self.players if player.alive]

    @property
    def dead_players(self):
        return [player for player in self.players if not player.alive]

    @property
    def werewolves(self):
        return [player for player in self.alive_players if player.team == "狼人"]

    @property
    def villagers(self):
        return [player for player in self.alive_players if player.team == "村民"]

    @property
    def townsfolks(self):
        return [player for player in self.alive_players if player.role == "平民"]

    def get_player_by_id(self, player_id: int):
        return self.id_to_player.get(player_id)

    def step_1(self):
        logger.info(f"initiate {self}")

        # setting up game
        roles = [role for role, n in self.set_up.items() for _ in range(n)]
        random.shuffle(roles)

        for role_str in roles:
            player_id = len(self.players) + 1
            role = get_role(role_str)
            player = role(game=self, player_id=player_id)
            self.players.append(player)
            self.id_to_player[player_id] = player

            if role == Seer:
                self.seer = player
            if role == Witch:
                self.witch = player
            if role == Hunter:
                self.hunter = player

            logger.info(f"initiate {player} {player.role}")

        logger.info(f"initiate {self.moderator}")

        for player in self.alive_players:
            private_info = self.info + f"你是{player}，你的身份是{player.role}。"
            player.set_up_memory(private_info)

        logger.info(f"\n{'='*64}\n游戏开始\n{'='*64}")
        self.moderator.speak("游戏开始。")

    def step_2(self):
        self.create_subprocess(Night)
        self.create_subprocess(Day)
        self.execute_subprocesses_loop()

    def step_3(self):
        self.save()

    def play(self):
        while self.curr is not None:
            self.curr.run()
