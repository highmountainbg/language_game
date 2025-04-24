import random
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from loguru import logger

from agent import (
    Player,
    DecideBinary,
    SelectOnePlayer,
)
from utils.utils import order_str
from .werewolf_template import (
    WEREWOLF_GAME_NAME,
    WEREWOLF_INFO,
)
from ..process import (
    Game,
    Process,
    checkpoint,
    concurrent_checkpoint,
)


class WerewolfGamePlayer(Player):
    """
    Werewolf game player class.
    """

    def __init__(self, game: "WerewolfGame", player_id: int):
        super().__init__(game=game, player_id=player_id)
        self.role = None
        self.tools = [DecideBinary, SelectOnePlayer]

    @property
    def is_sheriff(self):
        return self == self.game.sheriff


class Moderator(WerewolfGamePlayer):
    """
    Moderator class for the Werewolf game.
    """

    def __init__(self, game: "WerewolfGame"):
        super().__init__(game=game, player_id=0)
        self.role = "裁判"

    def __str__(self):
        return "裁判"


class Werewolf(WerewolfGamePlayer):
    """
    Werewolf class for the Werewolf game.
    """

    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "狼人"
        self.team = "狼人"
        self.teammates = self.game.werewolves


class Townsfolk(WerewolfGamePlayer):
    """
    Townsfolk class for the Werewolf game.
    """

    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "平民"
        self.team = "村民"


class Seer(WerewolfGamePlayer):
    """
    Seer class for the Werewolf game.
    """

    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "预言家"
        self.team = "村民"


class Witch(WerewolfGamePlayer):
    """
    Witch class for the Werewolf game.
    """

    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "女巫"
        self.team = "村民"
        self.healing_remain = True
        self.poison_remain = True


class Hunter(WerewolfGamePlayer):
    """
    Hunter class for the Werewolf game.
    """

    def __init__(self, player_id: int, game: "WerewolfGame"):
        super().__init__(game=game, player_id=player_id)
        self.role = "猎人"
        self.team = "村民"


def get_role(role_str: str) -> WerewolfGamePlayer:
    """
    Get the role class based on the role string.
    """
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
    """
    Base class for all processes in the Werewolf game.
    """

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

    def die_in_order(self):
        """
        Announce the death in order of the cause.
        """
        self.announce_death(self.cause.keys())

        for dead in sorted(
            self.cause.keys(),
            key=lambda x: self.cause.get(x)
        ):
            self.create_subprocess(
                Die,
                involved=dead,
                cause=self.cause.get(dead)
            )
        self.execute_subprocesses_sequential()

    @property
    def sequence(self):
        return [
            self.die_in_order
        ]


class HunterKill(WerewolfGameProcess):

    def ask(self):
        self.moderator.speak(
            "你要对谁开枪？输出目标序号，不开枪输出0。",
            audience=self.hunter
        )

    @checkpoint
    def select(self):
        target = self.hunter.select_one_player(
            choices=self.game.alive_players,
            abstain=True
        )
        if target is not None:
            self.moderator.speak(f"{self.hunter}猎人开枪击杀了{target}。")
            self.payload['hunter_kill'] = target

    def kill(self):
        target = self.payload.get('hunter_kill')
        if target is not None:
            kill = self.create_subprocess(
                Kill,
                cause={target: 'hunter kill'}
            )
            self.execute_subprocess(kill)

    @property
    def sequence(self):
        return [
            self.ask,
            self.select,
            self.kill
        ]


class SheriffSuccession(WerewolfGameProcess):

    def ask(self):
        self.moderator.speak(
            "你要把警徽移交给谁？输出目标序号，不移交输出0。",
            audience=self.game.sheriff
        )

    @checkpoint
    def select(self):
        dead_sheriff = self.game.sheriff
        target = dead_sheriff.select_one_player(
            choices=self.game.alive_players,
            abstain=True
        )
        if target is not None:
            self.moderator.speak(f"{dead_sheriff}将警徽移交给了{target}。")
            self.game.sheriff = target
        else:
            self.moderator.speak(f"{dead_sheriff}没有移交警徽，警徽流失。")

    @property
    def sequence(self):
        return [
            self.ask,
            self.select
        ]


class Die(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cause = kwargs.get('cause')
        self.dead = None

    def die(self):
        """
        The involved player dies.
        """
        self.dead = self.involved[0]
        self.dead.alive = False

    def check_if_game_over(self):
        """
        Check if the game is over after the death of a player.
        """
        if self.game.is_over:
            self.nxt = self.game

    def hunter_act(self):
        """
        If the dead player is a hunter and the cause of death is a werewolf,
        the death of the hunter will trigger the hunter's action.
        """
        if self.dead == self.hunter and self.cause in ['a_werewolf', 'lynch']:
            hunter_kill = self.create_subprocess(HunterKill)
            self.execute_subprocess(hunter_kill)

    def sheriff_succession(self):
        """
        If the dead player is a sheriff,
        the death of the sheriff will trigger the sheriff's succession.
        """
        if self.dead.is_sheriff:
            sheriff_succession = self.create_subprocess(SheriffSuccession)
            self.execute_subprocess(sheriff_succession)

    @property
    def sequence(self):
        return [
            self.die,
            self.check_if_game_over,
            self.hunter_act,
            self.sheriff_succession
        ]


class Consolidate(WerewolfGameProcess):
    def consolidate(self):
        self.involved[0].consolidate_memory()

    @property
    def sequence(self):
        return [
            self.consolidate
        ]


class MemoryConsolidation(WerewolfGameProcess):
    def prepare_consolidate(self):
        self.clear_subprocesses()
        for player in self.involved:
            self.create_subprocess(
                process_class=Consolidate,
                involved=player
            )

    @concurrent_checkpoint
    def concurrent_consolidate(self):
        self.execute_subprocesses_concurrent()

    @property
    def sequence(self):
        return [
            self.prepare_consolidate,
            self.concurrent_consolidate
        ]


class Speak(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speaker = kwargs.get('speaker')

    @checkpoint
    def speak(self):
        self.speaker.think_and_speak(self.involved)

    @property
    def sequence(self):
        return [
            self.speak
        ]


class Vote(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.abstain = kwargs.get('abstain', True)

    def select(self):
        voter = self.involved[0]
        self.payload[voter] = voter.select_one_player(
            choices=self.game.alive_players,
            abstain=self.abstain
        )
        self.update_parent_payload()

    @property
    def sequence(self):
        return [
            self.select
        ]


class Voting(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.announcement = kwargs.get('announcement')
        self.abstain = kwargs.get('abstain', True)
        self.tie = kwargs.get('abstain', True)

    def announce(self):
        msg = self.announcement
        if self.abstain:
            msg += "，输出目标序号，弃权输出0。"
        else:
            msg += "，输出目标序号，不能弃权。"
        self.moderator.speak(msg, self.involved)

    def prepare_vote(self):
        for voter in self.involved:
            self.create_subprocess(
                process_class=Vote,
                involved=voter,
                abstain=self.abstain
            )

    @concurrent_checkpoint
    def concurrent_vote(self):
        self.execute_subprocesses_concurrent()

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
            if target is None:
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
            msg += "没有有效票，投票没有结果。"
            result = None
        else:
            msg += f"{order_str(temp)}票数最多且相同，投票没有结果。"
            result = None

        self.moderator.speak(msg, audience=audience)
        logger.info(f"vote result: {result}")
        return result

    def announce_and_update(self):
        self.payload['result'] = self.announce_votes(
            votes=self.payload,
            audience=self.involved
        )
        self.update_parent_payload()

    @property
    def sequence(self):
        return [
            self.announce,
            self.prepare_vote,
            self.concurrent_vote,
            self.announce_and_update
        ]


class Discussion(WerewolfGameProcess):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = []
        self.announcement = kwargs.get('announcement')

    def announce(self):
        self.moderator.speak(self.announcement, self.involved)

    def speak(self):
        for speaker in self.involved:
            self.create_subprocess(
                process_class=Speak,
                speaker=speaker,
                involved=self.involved
            )
        self.execute_subprocesses_sequential()

    def consolidation(self):
        consolidation = self.create_subprocess(
            process_class=MemoryConsolidation,
            involved=self.involved
        )
        self.execute_subprocess(consolidation)

    @property
    def sequence(self):
        return [
            self.announce,
            self.speak,
            self.consolidation
        ]


class SeerAct(WerewolfGameProcess):

    def ask(self):
        self.moderator.speak("你要查验谁？输出目标序号。", self.seer)

    @checkpoint
    def select(self):
        target = self.seer.select_one_player(
            choices=self.game.alive_players,
            abstain=False
        )
        self.moderator.speak(f"{target}是{target.team}。", self.seer)

    @checkpoint
    def consolidate(self):
        self.seer.consolidate_memory()

    @property
    def sequence(self):
        return [
            self.ask,
            self.select,
            self.consolidate
        ]


class WerewolvesAct(WerewolfGameProcess):

    def discussion(self):
        if len(self.werewolves) > 1:
            self.payload["werewolves_target"] = None
            discussion = self.create_subprocess(
                process_class=Discussion,
                involved=self.werewolves,
                announcement=f"狼人{order_str(self.werewolves)}，现在秘密讨论，请依次发言。"
            )
            self.execute_subprocess(discussion)

    def voting(self):
        voting = self.create_subprocess(
            process_class=Voting,
            involved=self.werewolves,
            announcement="现在开始秘密投票选择击杀对象",
            abstain=True
        )
        self.execute_subprocess(voting)

    def update_payload(self):
        self.payload["werewolves_target"] = self.payload.pop('result')
        self.update_parent_payload()

    def consolidation(self):
        consolidation = self.create_subprocess(
            process_class=MemoryConsolidation,
            involved=self.werewolves
        )
        self.execute_subprocess(consolidation)

    @property
    def sequence(self):
        return [
            self.discussion,
            self.voting,
            self.update_payload,
            self.consolidation
        ]


class Heal(WerewolfGameProcess):

    @property
    def night(self):
        return self.parent.parent

    def ask(self):
        target = self.night.payload['werewolves_target']
        if target is not None:
            self.moderator.speak(
                f"今夜狼人的目标是{target}，你要使用解药吗？",
                self.game.witch
            )
            self.victim_exists = True
        else:
            self.moderator.speak("今夜狼人没有杀人", self.game.witch)
            self.victim_exists = False

    @checkpoint
    def decide(self):
        if self.victim_exists:
            result = self.witch.decide_binary()
            self.payload['heal'] = result
            if result:
                self.witch.healing_remain = False
            self.update_parent_payload()

    @property
    def sequence(self):
        return [
            self.ask,
            self.decide
        ]


class Poison(WerewolfGameProcess):

    def ask(self):
        self.moderator.speak(
            "你要对谁使用毒药？输出目标序号，不使用输出0。",
            audience=self.witch
        )

    @checkpoint
    def select(self):
        result = self.witch.select_one_player(
            choices=self.game.alive_players,
            abstain=True
        )
        self.payload['poison_target'] = result
        if result:
            self.witch.poison_remain = False
        self.update_parent_payload()

    @property
    def sequence(self):
        return [
            self.ask,
            self.select
        ]


class WitchAct(WerewolfGameProcess):

    def initialize(self):
        self.payload['heal'] = False
        self.payload['poison_target'] = None

    def heal(self):
        if self.witch.healing_remain:
            heal = self.create_subprocess(Heal)
            self.execute_subprocess(heal)

    def poison(self):
        if self.witch.poison_remain and not self.payload['heal']:
            poison = self.create_subprocess(Poison)
            self.execute_subprocess(poison)

    def settle(self):
        self.update_parent_payload()
        self.clear_subprocesses()

    @checkpoint
    def consolidate(self):
        self.witch.consolidate_memory()

    @property
    def sequence(self):
        return [
            self.initialize,
            self.heal,
            self.poison,
            self.settle,
            self.consolidate
        ]


class SheriffElection(WerewolfGameProcess):

    def discussion(self):
        discussion = self.create_subprocess(
            Discussion,
            announcement="现在开始警长选举讨论，请依次发言。"
        )
        self.execute_subprocess(discussion)

    def voting(self):
        voting = self.create_subprocess(
            Voting,
            announcement="现在开始投票选举警长",
            abstain=True
        )
        self.execute_subprocess(voting)

    def appoint_sheriff(self):
        sheriff = self.payload['result']
        if sheriff is None:
            self.moderator.speak("本局游戏没有警长。")
        else:
            self.moderator.speak(f"{sheriff}当选警长。")
            self.game.sheriff = sheriff

    def consolidation(self):
        consolidation = self.create_subprocess(
            process_class=MemoryConsolidation,
            involved=self.involved
        )
        self.execute_subprocess(consolidation)

    @property
    def sequence(self):
        return [
            self.discussion,
            self.voting,
            self.appoint_sheriff,
            self.consolidation
        ]


class Accusation(WerewolfGameProcess):
    def discussion(self):
        discussion = self.create_subprocess(
            Discussion,
            name="accusation discussion",
            announcement="现在开始指控狼人讨论，请依次发言。"
        )
        self.execute_subprocess(discussion)

    def voting(self):
        voting = self.create_subprocess(
            Voting,
            announcement="现在开始投票指控狼人",
            abstain=True
        )
        self.execute_subprocess(voting)

    def lynch(self):
        target = self.payload['result']
        if target is not None:
            kill = self.create_subprocess(
                Kill,
                cause={target: 'lynch'}
            )
            self.execute_subprocess(kill)

    def consolidation(self):
        consolidation = self.create_subprocess(
            process_class=MemoryConsolidation,
            involved=[p for p in self.involved if p.alive]
        )
        self.execute_subprocess(consolidation)

    @property
    def sequence(self):
        return [
            self.discussion,
            self.voting,
            self.lynch,
            self.consolidation
        ]


class Night(WerewolfGameProcess):

    def initialize(self):
        self.game.round += 1
        self.payload = {
            'deaths': {},
            'werewolves_target': None,
            'heal': False,
            'poison_target': None
        }
        self.moderator.speak(f"第{self.game.round}夜，天黑了。")

    def seer_act(self):
        if self.seer is not None and self.seer.alive:
            seer_act = self.create_subprocess(SeerAct)
            self.execute_subprocess(seer_act)

    def werewolves_act(self):
        if self.werewolves:
            werewolves_act = self.create_subprocess(WerewolvesAct)
            self.execute_subprocess(werewolves_act)

    def witch_act(self):
        if self.witch is not None and self.seer.alive:
            witch_act = self.create_subprocess(WitchAct)
            self.execute_subprocess(witch_act)

    def settle(self):
        if not self.payload['heal'] and self.payload['werewolves_target']:
            target = self.payload['werewolves_target']
            self.payload['deaths'][target] = 'a_werewolf'
        if self.payload['poison_target'] is not None:
            self.payload['deaths'][self.payload['poison_target']] = 'poison'
        self.clear_subprocesses()

    @property
    def sequence(self):
        return [
            self.initialize,
            self.seer_act,
            self.werewolves_act,
            self.witch_act,
            self.settle
        ]


class Day(WerewolfGameProcess):

    def dawn(self):
        self.payload = {}
        self.moderator.speak(f"第{self.game.round}天，天亮了。")

    def sheriff_election(self):
        if self.game.round == 1 and self.game.sheriff_flag:
            sheriff_election = self.create_subprocess(SheriffElection)
            self.execute_subprocess(sheriff_election)

    def announce_death_last_night(self):
        kill = self.create_subprocess(Kill, cause=self.nxt.payload['deaths'])
        self.execute_subprocess(kill)

    def accusation(self):
        accusation = self.create_subprocess(Accusation)
        self.execute_subprocess(accusation)

    def reset(self):
        self.clear_subprocesses()

    @property
    def sequence(self):
        return [
            self.dawn,
            self.sheriff_election,
            self.announce_death_last_night,
            self.accusation,
            self.reset
        ]


class WerewolfGame(Game):
    info = WEREWOLF_INFO
    name = "狼人杀"

    def __init__(self, config):
        super().__init__(
            name=self.name,
            language=config.get("language", "zh"),
        )

        self.setup = config["setup"]

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

        # init_game_logger(self)

    def add_info(self):
        if self.reveal_upon_death:
            self.info += "玩家死亡后会展示角色身份。"
        else:
            self.info += "玩家死亡后不会展示角色身份。"

        if self.sheriff_flag:
            self.info += "第一天公布死者之前有竞选警长环节，警长在指控狼人投票中有1.5票。"

        self.info += f"\n本场游戏玩家为{order_str(self.alive_players)}，"
        self.info += f"其中有{self.setup['werewolf']}个狼人，"
        self.info += f"{self.setup['townsfolk']}个平民，"
        self.info += f"{self.setup['seer']}个预言家，"
        self.info += f"{self.setup['witch']}个女巫。"
        self.info += f"{self.setup['witch']}个猎人。\n"

    @property
    def observable_state(self):
        result = f"目前{order_str(self.alive_players)}存活，"
        if self.dead_players:
            result += f"{order_str(self.dead_players)}死亡。"
        else:
            result += "无人死亡。"
        if self.sheriff:
            result += f"警长是{self.sheriff}。"
        return result

    @property
    def is_over(self):
        if len(self.villagers) == 0:
            msg = "狼人胜利。"
            self.moderator.speak(msg)
            logger.success(msg)
            self.result = {'werewolf_win': 1, 'villager_win': 0}
            return True

        elif len(self.werewolves) == 0:
            msg = "村民胜利。"
            self.moderator.speak(msg)
            logger.success(msg)
            self.result = {'werewolf_win': 0, 'villager_win': 1}
            return True

        return False

    @property
    def players(self):
        return sorted(self.id_to_player.values(), key=lambda x: x.id)

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

    def initialize(self):
        logger.info(f"initiate {self}")

        # setting up game
        roles = [role for role, n in self.setup.items() for _ in range(n)]
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

        system = "\n" + self.info
        detail = {"system": player.system}

        for player in self.alive_players:
            player.initialize_system(system)
            self.moderator.speak(
                msg=f"你是{player}，你的身份是{player.role}。",
                audience=player
            )
            detail[str(player)] = player.role

        self.record_detail(detail)
        self.moderator.speak("游戏开始。")

    def day_night_loop(self):
        self.create_subprocess(Night)
        self.create_subprocess(Day)
        self.execute_subprocesses_loop()

    @property
    def sequence(self):
        return [
            self.initialize,
            self.day_night_loop,
            self.save
        ]
