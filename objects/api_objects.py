from __future__ import annotations

import logging
import math

import lilyweight
from lilyweight import LilyWeight


class SkyBlockPlayer:
    def __init__(self, uuid: str, player_data: dict = None, profile_id: str = None, profile_name: str = None):
        self.uuid = uuid
        self.player_data = player_data

        if player_data.get("profiles"):
            for profile in player_data["profiles"]:
                if self.uuid not in profile["members"]:
                    self.player_data["profiles"].remove(profile)

        self._name = None
        self._player_data = None
        self._weight_with_overflow = None

        self.member_profile = None
        self.cute_name = None
        self.profile_id = None

        self._senither_constants = {
            "dungeons_level50_experience": 569809640,
            "skills_level50_experience": 55172425,
            "skills_level60_experience": 111672425,
            "dungeon_weights": {
                "catacombs": 0.0002149604615,
                "healer": 0.0000045254834,
                "mage": 0.0000045254834,
                "berserk": 0.0000045254834,
                "archer": 0.0000045254834,
                "tank": 0.0000045254834,
            },
            "slayer_weights": {
                "zombie": {
                    "divider": 2208,
                    "modifier": 0.15,
                },
                "spider": {
                    "divider": 2118,
                    "modifier": 0.08,
                },
                "wolf": {
                    "divider": 1962,
                    "modifier": 0.015,
                },
                "enderman": {
                    "divider": 1430,
                    "modifier": 0.017,
                }
            },
            "skill_weights": {
                # Maxes out mining at 1,750 points at 60.
                "mining": {
                    "exponent": 1.18207448,
                    "divider": 259634,
                    "maxLevel": 60,
                },
                # Maxes out foraging at 850 points at level 50.
                "foraging": {
                    "exponent": 1.232826,
                    "divider": 259634,
                    "maxLevel": 50,
                },
                # Maxes out enchanting at 450 points at level 60.
                "enchanting": {
                    "exponent": 0.96976583,
                    "divider": 882758,
                    "maxLevel": 60,
                },
                # Maxes out farming at 2,200 points at level 60.
                "farming": {
                    "exponent": 1.217848139,
                    "divider": 220689,
                    "maxLevel": 60,
                },
                # Maxes out combat at 1,500 points at level 60.
                "combat": {
                    "exponent": 1.15797687265,
                    "divider": 275862,
                    "maxLevel": 60,
                },
                # Maxes out fishing at 2,500 points at level 50.
                "fishing": {
                    "exponent": 1.406418,
                    "divider": 88274,
                    "maxLevel": 50,
                },
                # Maxes out alchemy at 200 points at level 50.
                "alchemy": {
                    "exponent": 1.0,
                    "divider": 1103448,
                    "maxLevel": 50,
                },
                # Maxes out taming at 500 points at level 50.
                "taming": {
                    "exponent": 1.14744,
                    "divider": 441379,
                    "maxLevel": 50,
                },
                # Sets up carpentry and runecrafting without any weight components.
                "carpentry": {
                    "maxLevel": 50,
                },
                "runecrafting": {
                    "maxLevel": 25,
                },
            },
            "skill_weight_groups": [
                'mining', 'foraging', 'enchanting', 'farming', 'combat', 'fishing', 'alchemy', 'taming'
            ],
        }
        self.skill_max_level = {
            "mining": 60,
            "foraging": 50,
            "enchanting": 60,
            "farming": 60,
            "combat": 60,
            "fishing": 50,
            "alchemy": 50,
            "taming": 50,
            "carpentry": 50,
            "runecrafting": 25,
        }
        self._used_average_skills = [
            'mining', 'foraging', 'enchanting', 'farming', 'combat', 'fishing', 'alchemy', 'taming', 'carpentry'
        ]

        self.select_profile(profile_id, profile_name)

    def select_profile(self, profile_id: str = None, profile_name: str = None):
        if self.player_data["profiles"] is None:
            return None

        if profile_id:
            for profile in self.player_data["profiles"]:
                if profile["profile_id"] == profile_id:  # and self.uuid in profile["members"]:
                    self.member_profile = profile["members"][self.uuid]
                    self.cute_name = profile["cute_name"]
                    self.profile_id = profile["profile_id"]
                    return self.member_profile

        if profile_name:
            for profile in self.player_data["profiles"]:
                if profile["cute_name"] == profile_name:
                    self.member_profile = profile["members"][self.uuid]
                    self.cute_name = profile["cute_name"]
                    self.profile_id = profile["profile_id"]
                    return self.member_profile

        profiles = []
        for profile in self.player_data["profiles"]:
            try:
                profile["members"][self.uuid]["cute_name"] = profile["cute_name"]
                profile["members"][self.uuid]["profile_id"] = profile["profile_id"]
                profiles.append(profile["members"][self.uuid])
            except KeyError:
                continue

        self.member_profile = sorted(
            profiles, key=lambda x: x.get("leveling", {}).get("experience", 0), reverse=True
        )[0]

        self.cute_name = self.member_profile["cute_name"]
        self.profile_id = self.member_profile["profile_id"]

        self._weight_with_overflow = None
        return self.member_profile

    async def get_name(self, app) -> str:
        if self._name:
            return self._name
        self._name = await app.httpr.get_name(self.uuid)
        return self._name

    async def get_player_data(self, app) -> str:
        if self._player_data:
            return self._player_data
        self._player_data = await app.httpr.get_player_data(self.uuid)
        return self._player_data

    @staticmethod
    def get_cata_lvl(exp, overflow=True):
        levels = {
            1: 50, 2: 75, 3: 110, 4: 160, 5: 230, 6: 330, 7: 470, 8: 670, 9: 950, 10: 1340, 11: 1890, 12: 2665,
            13: 3760, 14: 5260, 15: 7380, 16: 10300, 17: 14400, 18: 20000, 19: 27600, 20: 38000, 21: 52500, 22: 71500,
            23: 97000, 24: 132000, 25: 180000, 26: 243000, 27: 328000, 28: 445000, 29: 600000, 30: 800000, 31: 1065000,
            32: 1410000, 33: 1900000, 34: 2500000, 35: 3300000, 36: 4300000, 37: 5600000, 38: 7200000, 39: 9200000,
            40: 12000000, 41: 15000000, 42: 19000000, 43: 24000000, 44: 30000000, 45: 38000000, 46: 48000000,
            47: 60000000, 48: 75000000, 49: 93000000, 50: 116250000,
        }
        # > 50 200 000 000 per level
        # levels dict is incremental
        remaining_xp = exp
        level50 = sum(levels.values())

        if exp >= level50:
            return 50 + (exp - level50) / 200000000 if overflow else 50

        for lvl, xp in levels.items():
            if remaining_xp < xp:
                decimal = remaining_xp / xp
                return lvl + decimal - 1
            remaining_xp -= xp
        return 0

    @property
    def catacombs_xp(self) -> float:
        try:
            return self.member_profile["dungeons"]["dungeon_types"]["catacombs"]["experience"]
        except:
            return 0

    @property
    def sb_experience(self) -> int:
        try:
            return int(self.member_profile.get("leveling", {}).get("experience", 0))
        except:
            return 0

    @property
    def catacombs_level(self) -> float:
        return self.get_cata_lvl(self.catacombs_xp, overflow=False)

    @property
    def catacombs_level_overflow(self) -> float:
        return self.get_cata_lvl(self.catacombs_xp, overflow=True)

    @property
    def slayer_xp(self) -> float:
        if self.member_profile and self.member_profile.get("slayer") is not None:
            return sum([i.get("xp", 0) for i in self.member_profile["slayer"].get("slayer_bosses", {}).values()])
        return 0

    async def average_skill(self, app=None):
        if (
                self.member_profile is None or
                self.member_profile.get("player_data") is None or
                self.member_profile["player_data"].get("experience") is None
        ):
            return 0

        taming_cap = 50
        # find taming cap
        if app:
            player_data = await self.get_player_data(app)
            try:
                taming_cap = player_data["player"]["achievements"].get("skyblock_domesticator", 50)
            except:
                pass

        total_skills = 0
        for skill_type in self._used_average_skills:
            experience = self.member_profile["player_data"]["experience"].get(f"SKILL_{skill_type.upper()}", 0)
            total_skills += self.get_skill_lvl(
                skill_type, experience, given_max_level=None if skill_type != "taming" else taming_cap
            )

        return total_skills / len(self._used_average_skills)

    def get_skill_lvl(self, skill_type, exp, given_max_level=None):
        # max_level = self.skill_max_level[skill_type] if given_max_level is None else given_max_level
        max_level = given_max_level if given_max_level else self.skill_max_level[skill_type]
        if max_level > 60:
            max_level = 60
        levels = {
            "0": 0, "1": 50, "2": 175, "3": 375, "4": 675, "5": 1175, "6": 1925, "7": 2925, "8": 4425, "9": 6425,
            "10": 9925, "11": 14925, "12": 22425, "13": 32425, "14": 47425, "15": 67425, "16": 97425, "17": 147425,
            "18": 222425, "19": 322425, "20": 522425, "21": 822425, "22": 1222425, "23": 1722425, "24": 2322425,
            "25": 3022425, "26": 3822425, "27": 4722425, "28": 5722425, "29": 6822425, "30": 8022425, "31": 9322425,
            "32": 10722425, "33": 12222425, "34": 13822425, "35": 15522425, "36": 17322425, "37": 19222425,
            "38": 21222425, "39": 23322425, "40": 25522425, "41": 27822425, "42": 30222425, "43": 32722425,
            "44": 35322425, "45": 38072425, "46": 40972425, "47": 44072425, "48": 47472425, "49": 51172425,
            "50": 55172425, "51": 59472425, "52": 64072425, "53": 68972425, "54": 74172425, "55": 79672425,
            "56": 85472425, "57": 91572425, "58": 97972425, "59": 104672425, "60": 111672425
        }
        for level in levels:
            if exp >= levels[str(max_level)]:
                return max_level
            if levels[level] > exp:
                lowexp = levels[str(int(level) - 1)]
                highexp = levels[level]
                difference = highexp - lowexp
                extra = exp - lowexp
                percentage = (extra / difference)
                return (int(level) - 1) + percentage

    # Senither Weight

    def _senither_calculate_dungeon_weight(self, weight_type: str, level: int, experience: int,
                                           with_overflow: bool = True):

        percentage_modifier = self._senither_constants["dungeon_weights"][weight_type]

        # Calculates the base weight using the players level
        base = math.pow(level, 4.5) * percentage_modifier

        # If the dungeon XP is below the requirements for a level 50 dungeon we'll
        # just return our weight right away.
        if experience <= self._senither_constants["dungeons_level50_experience"]:
            return base

        # Calculates the XP above the level 50 requirement, and the splitter
        # value, weight given past level 50 is given at 1/4 the rate.
        remaining = experience - self._senither_constants["dungeons_level50_experience"]
        splitter = (4 * self._senither_constants["dungeons_level50_experience"]) / base

        # Calculates the dungeon overflow weight and returns it to the weight object builder.
        return math.floor(base) + math.pow(remaining / splitter, 0.968) if with_overflow else math.floor(base)

    def senither_dungeon_weight(self, with_overflow: bool = True):
        if self.member_profile is None or self.member_profile.get("dungeons") is None or self.member_profile.get(
                "dungeons").get(
            "player_classes") is None:
            return 0
        cata_weight = self._senither_calculate_dungeon_weight("catacombs", self.catacombs_level, self.catacombs_xp,
                                                              with_overflow)
        return sum(
            self._senither_calculate_dungeon_weight(
                cls_data, self.get_cata_lvl(exp.get("experience", 0), overflow=False), exp.get("experience", 0),
                with_overflow
            ) for cls_data, exp in self.member_profile["dungeons"]["player_classes"].items()
        ) + cata_weight

    def _senither_calculate_slayer_weight(self, weight_type: str, experience: int, with_overflow: bool = True):
        slayer_weight = self._senither_constants["slayer_weights"].get(weight_type)
        if not slayer_weight:
            return 0

        if experience <= 1000000:
            return 0 if experience <= 0 else experience / slayer_weight["divider"]

        base = 1000000 / slayer_weight["divider"]
        remaining = experience - 1000000

        modifier = slayer_weight["modifier"]
        overflow = 0

        while remaining > 0:
            left = min(remaining, 1000000)

            overflow += math.pow(left / (slayer_weight["divider"] * (1.5 + modifier)), 0.942)
            modifier += slayer_weight["modifier"]
            remaining -= left

        return base + overflow if with_overflow else base

    def senither_slayer_weight(self, with_overflow: bool = True):
        if (
                self.member_profile is None or
                self.member_profile.get("slayer") is None or
                self.member_profile["slayer"].get("slayer_bosses") is None
        ):
            return 0

        return sum(
            self._senither_calculate_slayer_weight(
                slayer_type,
                self.member_profile["slayer"]["slayer_bosses"].get(slayer_type, {}).get("xp",
                                                                                        0) if self.member_profile else 0,
                with_overflow
            )
            for slayer_type in self._senither_constants["slayer_weights"].keys()
        )

    def _senither_calculate_skill_weight(self, weight_type: str, level: int, experience: int,
                                         with_overflow: bool = True):
        skill_weight = self._senither_constants["skill_weights"].get(weight_type)
        if not skill_weight or skill_weight["divider"] == 0 or skill_weight["exponent"] == 0:
            return 0

        # Gets the XP required to max out the skill.
        max_skill_level_xp = self._senither_constants["skills_level60_experience"] if skill_weight["maxLevel"] == 60 \
            else self._senither_constants["skills_level50_experience"]

        # Calculates the base weight using the players level, if the players level
        # is 50/60 we'll round off their weight to get a nicer looking number.
        base = math.pow(level * 10, 0.5 + skill_weight["exponent"] + level / 100) / 1250
        if experience > max_skill_level_xp:
            base = round(base)

        # If the skill XP is below the requirements for a level 50/60 skill we'll
        # just return our weight to the weight object builder right away.
        if experience <= max_skill_level_xp:
            return base

        # Calculates the skill overflow weight and returns it to the weight object builder.
        return base + math.pow((experience - max_skill_level_xp) / skill_weight["divider"], 0.968) if with_overflow \
            else base

    def senither_skill_weight(self, with_overflow: bool = True):
        if (
                self.member_profile is None or
                self.member_profile.get("player_data") is None or
                self.member_profile["player_data"].get("experience") is None
        ):
            return 0

        skill_weight = 0
        for skill_type, value in self._senither_constants["skill_weights"].items():
            if skill_type in self._senither_constants["skill_weight_groups"]:
                senither_old_max_level_cap = value["maxLevel"]
                experience = self.member_profile["player_data"]["experience"].get(f"SKILL_{skill_type.upper()}", 0)

                skill_weight += self._senither_calculate_skill_weight(
                    skill_type,
                    self.get_skill_lvl(
                        skill_type, experience, given_max_level=senither_old_max_level_cap
                    ),
                    experience, with_overflow
                )
        return skill_weight

    def senither_weight(self):
        if self._weight_with_overflow:
            return self._weight_with_overflow

        self._weight_with_overflow = (
                self.senither_slayer_weight(True) +
                self.senither_skill_weight(True) +
                self.senither_dungeon_weight(True)
        )
        return self._weight_with_overflow

    # Lily Weight

    async def lily_weight(self, app):
        slayer_kwargs = {  # Loop through the slayer bosses and get the xp if they key exists else default value
            "zombie": 0, "spider": 0, "wolf": 0, "enderman": 0, "blaze": 0
        }

        if (
                self.member_profile and
                self.member_profile.get("slayer") and
                self.member_profile["slayer"].get("slayer_bosses")
        ):
            for boss_type, boss_data in self.member_profile["slayer"]["slayer_bosses"].items():
                slayer_kwargs[boss_type] = boss_data.get("xp", 0)

            # Catacombs Completions
        # Get the catacombs weight of the player
        try:
            cata_completions = self.member_profile["dungeons"]["dungeon_types"]["catacombs"]["tier_completions"]
            # Try to get the catacombs completions
        except:
            # If the keys are not found set to default value
            cata_completions = {}
        try:
            m_cata_compl = self.member_profile["dungeons"]["dungeon_types"]["master_catacombs"]["tier_completions"]
        except:
            m_cata_compl = {}

        # Catacombs XP
        try:
            cata_xp = self.member_profile["dungeons"]["dungeon_types"]["catacombs"]["experience"]
        except:
            cata_xp = 0

        # Skills
        skill_experience_dict = {}
        skill_level_dict = {}

        if (
                self.member_profile is None or
                self.member_profile.get("player_data") is None or
                self.member_profile["player_data"].get("experience") is None
        ):
            return {"total": 0}

        if (
                self.member_profile is None or
                self.member_profile.get("player_data") is None or
                self.member_profile["player_data"].get("experience") is None or
                self.member_profile["player_data"]["experience"].get("SKILL_MINING") is None
        ):
            # Skill api is off
            try:
                player = await self.get_player_data(app)  # Get the player data from the hypixel api
                for skill_type, achv_name in lilyweight.used_skills.items():
                    level = player["player"].get("achievements", {}).get(achv_name, 0)
                    # Get the level of the skill from achievements
                    skill_experience_dict[skill_type] = lilyweight.get_xp_from_level(level)
                    # Get the xp of the skill from the level
                    skill_level_dict[skill_type] = level  # Add the skill level to the skill level dict
            except Exception as e:
                logging.getLogger("lilyweight").error(f"Error getting player data: {e} {self.uuid}")
                print(e)
        else:
            # Loop through all the skills lily weight uses
            if self.member_profile:
                for skill_type in lilyweight.used_skills.keys():
                    # Get the experience of the skill
                    experience = self.member_profile["player_data"]["experience"].get(f"SKILL_{skill_type.upper()}", 0)
                    skill_experience_dict[skill_type] = experience  # Add the experience to the experience skill dict
                    skill_level_dict[skill_type] = lilyweight.get_level_from_XP(experience)
                    # Add the skill level to the counter

        slayer_kwargs.pop("vampire", None)
        return LilyWeight.get_weight_raw(
            skill_level_dict, skill_experience_dict, cata_completions, m_cata_compl, cata_xp, **slayer_kwargs
        )
