import asyncio
import json
import math

import aiohttp
import asyncpg
import discord
from discord import Webhook


def get_xp_lvl(exp):
    levels = {
        "0": 0,
        "1": 50,
        "2": 175,
        "3": 375,
        "4": 675,
        "5": 1175,
        "6": 1925,
        "7": 2925,
        "8": 4425,
        "9": 6425,
        "10": 9925,
        "11": 14925,
        "12": 22425,
        "13": 32425,
        "14": 47425,
        "15": 67425,
        "16": 97425,
        "17": 147425,
        "18": 222425,
        "19": 322425,
        "20": 522425,
        "21": 822425,
        "22": 1222425,
        "23": 1722425,
        "24": 2322425,
        "25": 3022425,
        "26": 3822425,
        "27": 4722425,
        "28": 5722425,
        "29": 6822425,
        "30": 8022425,
        "31": 9322425,
        "32": 10722425,
        "33": 12222425,
        "34": 13822425,
        "35": 15522425,
        "36": 17322425,
        "37": 19222425,
        "38": 21222425,
        "39": 23322425,
        "40": 25522425,
        "41": 27822425,
        "42": 30222425,
        "43": 32722425,
        "44": 35322425,
        "45": 38072425,
        "46": 40972425,
        "47": 44072425,
        "48": 47472425,
        "49": 51172425,
        "50": 55172425,
        "51": 59472425,
        "52": 64072425,
        "53": 68972425,
        "54": 74172425,
        "55": 79672425,
        "56": 85472425,
        "57": 91572425,
        "58": 97972425,
        "59": 104672425,
        "60": 111672425
    }
    for level in levels:
        if exp >= levels["60"]:
            return 60
        if levels[level] > exp:
            lowexp = levels[str(int(level) - 1)]
            highexp = levels[level]
            difference = highexp - lowexp
            extra = exp - lowexp
            percentage = (extra / difference)
            return (int(level) - 1) + percentage
    return "ERROR1"


def get_cata_lvl(exp):
    levels = {'1': 50, '2': 125, '3': 235, '4': 395, '5': 625, '6': 955, '7': 1425, '8': 2095, '9': 3045,
              '10': 4385, '11': 6275, '12': 8940, '13': 12700, '14': 17960, '15': 25340, '16': 35640,
              '17': 50040, '18': 70040, '19': 97640, '20': 135640, '21': 188140, '22': 259640, '23': 356640,
              '24': 488640, '25': 668640, '26': 911640, '27': 1239640, '28': 1684640, '29': 2284640,
              '30': 3084640, '31': 4149640, '32': 5559640, '33': 7459640, '34': 9959640, '35': 13259640,
              '36': 17559640, '37': 23159640, '38': 30359640, '39': 39559640, '40': 51559640, '41': 66559640,
              '42': 85559640, '43': 109559640, '44': 139559640, '45': 177559640, '46': 225559640,
              '47': 285559640, '48': 360559640, '49': 453559640, '50': 569809640
              }
    for level in levels:
        if exp >= levels["50"]:
            return 50
        if levels[level] > exp:
            if int(level) == 1:
                level = str(2)
            lowexp = levels[str(int(level) - 1)]
            highexp = levels[level]
            difference = highexp - lowexp
            extra = exp - lowexp
            percentage = (extra / difference)
            return (int(level) - 1) + percentage
    return "ERROR1"


class SkyBlockPlayer:
    def __init__(
            self, uuid: str, player_data: dict = None, profile_id: str = None, profile_name: str = None,
            select_profile_on: str = "last_save"
    ):
        self.uuid = uuid
        self.player_data = player_data
        if player_data.get("profiles"):
            for profile in player_data["profiles"]:
                if self.uuid not in profile["members"]:
                    self.player_data["profiles"].remove(profile)

        """
        select_profile_on can be one of the following:
        - last_save
        - weight
        - cata
        - slayer
        """
        self._name, self._weight_with_overflow, self._weight_without_overflow, self.profile, self.gexp, _selected_profile_name = (
                                                                                                                                     None,) * 6

        self.select_profile(profile_id, profile_name, select_profile_on)

        self._dungeons_level50_experience = 569809640
        self._skills_level50_experience = 55172425
        self._skills_level60_experience = 111672425
        self._dungeon_weights = {
            "catacombs": 0.0002149604615,
            "healer": 0.0000045254834,
            "mage": 0.0000045254834,
            "berserk": 0.0000045254834,
            "archer": 0.0000045254834,
            "tank": 0.0000045254834,
        }
        self._slayer_weights = {
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
        }
        self._skill_weights = {
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
        }
        self._skill_weight_groups = [
            'mining', 'foraging', 'enchanting', 'farming', 'combat', 'fishing', 'alchemy', 'taming'
        ]

    def _selected_profile(
            self, profile_id: str = None, profile_name: str = None, select_profile_on: str = "last_save"
    ) -> dict:
        if self.player_data["profiles"] is None:
            self._selected_profile_name = None
            return None
        if profile_id:
            for profile in self.player_data["profiles"]:
                if profile["profile_id"] == profile_id:  # and self.uuid in profile["members"]:
                    self._selected_profile_name = profile["cute_name"]
                    return profile["members"][self.uuid]
        if profile_name:
            for profile in self.player_data["profiles"]:
                if profile["cute_name"] == profile_name:
                    self._selected_profile_name = profile["cute_name"]
                    return profile["members"][self.uuid]

        profiles = []
        for profile in self.player_data["profiles"]:
            try:
                profile["members"][self.uuid]["cute_name"] = profile["cute_name"]
                profiles.append(profile["members"][self.uuid])
            except KeyError:
                continue

        if select_profile_on == "last_save":
            found_profile = sorted(profiles, key=lambda x: x.get("last_save", 0), reverse=True)[0]

        elif select_profile_on == "weight":
            found_profile = sorted(
                self.player_data["profiles"],
                key=lambda x: SkyBlockPlayer(self.uuid, self.player_data, x["profile_id"]).weight(),
                reverse=True
            )[0]["members"][self.uuid]
        elif select_profile_on == "cata":
            found_profile = sorted(
                profiles,
                key=lambda x: x.get("dungeons", {}).get("dungeon_types", {}).get("catacombs", {}).get("experience", 0),
                reverse=True
            )[0]
        elif select_profile_on == "slayer":
            found_profile = sorted(
                profiles,
                key=lambda x: sum([i.get("xp", 0) for i in x.get("slayer_bosses", {}).values()]),
                reverse=True
            )[0]
        else:
            raise ValueError(f"Invalid select_profile_on: {select_profile_on}")

        self._selected_profile_name = found_profile["cute_name"]
        return found_profile

    def select_profile(self, profile_id: str = None, profile_name: str = None, select_profile_on: str = "last_save"):
        """
        select_profile_on can be one of the following:
        - last_save
        - weight
        - cata
        - slayer
        """

        self.profile = self._selected_profile(profile_id, profile_name, select_profile_on)
        self._weight_with_overflow, self._weight_without_overflow = None, None
        return self

    async def get_name(self, client, max_ratelimit_wait) -> str:
        if self._name:
            return self._name
        self._name = await client.httpr.get_name(self.uuid, max_ratelimit_wait)
        return self._name

    @staticmethod
    def get_cata_lvl(exp):
        levels = {
            '1': 50, '2': 125, '3': 235, '4': 395, '5': 625, '6': 955, '7': 1425, '8': 2095, '9': 3045,
            '10': 4385, '11': 6275, '12': 8940, '13': 12700, '14': 17960, '15': 25340, '16': 35640,
            '17': 50040, '18': 70040, '19': 97640, '20': 135640, '21': 188140, '22': 259640, '23': 356640,
            '24': 488640, '25': 668640, '26': 911640, '27': 1239640, '28': 1684640, '29': 2284640,
            '30': 3084640, '31': 4149640, '32': 5559640, '33': 7459640, '34': 9959640, '35': 13259640,
            '36': 17559640, '37': 23159640, '38': 30359640, '39': 39559640, '40': 51559640, '41': 66559640,
            '42': 85559640, '43': 109559640, '44': 139559640, '45': 177559640, '46': 225559640,
            '47': 285559640, '48': 360559640, '49': 453559640, '50': 569809640
        }
        for level in levels:
            if exp >= levels["50"]:
                return 50
            if levels[level] > exp:
                if int(level) == 1:
                    level = str(2)
                lowexp = levels[str(int(level) - 1)]
                highexp = levels[level]
                difference = highexp - lowexp
                extra = exp - lowexp
                percentage = (extra / difference)
                return (int(level) - 1) + percentage

    def get_skill_lvl(self, skill_type, exp):
        skill_weight = self._skill_weights[skill_type]
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
            if exp >= levels[str(skill_weight["maxLevel"])]:
                return skill_weight["maxLevel"]
            if levels[level] > exp:
                lowexp = levels[str(int(level) - 1)]
                highexp = levels[level]
                difference = highexp - lowexp
                extra = exp - lowexp
                percentage = (extra / difference)
                return (int(level) - 1) + percentage

    @property
    def selected_profile_name(self):
        return self._selected_profile_name

    @property
    def last_save(self):
        try:
            return self.profile["last_save"]
        except (KeyError, TypeError):
            return None

    @property
    def catacombs_xp(self) -> float:
        try:
            return self.profile["dungeons"]["dungeon_types"]["catacombs"]["experience"]
        except (KeyError, TypeError):
            return 0

    @property
    def catacombs_level(self) -> float:
        return self.get_cata_lvl(self.catacombs_xp)

    def _calculate_dungeon_weight(self, weight_type: str, level: int, experience: int, with_overflow: bool = True):
        percentage_modifier = self._dungeon_weights[weight_type]

        # Calculates the base weight using the players level
        base = math.pow(level, 4.5) * percentage_modifier

        # If the dungeon XP is below the requirements for a level 50 dungeon we'll
        # just return our weight right away.
        if experience <= self._dungeons_level50_experience:
            return base

        # Calculates the XP above the level 50 requirement, and the splitter
        # value, weight given past level 50 is given at 1/4 the rate.
        remaining = experience - self._dungeons_level50_experience
        splitter = (4 * self._dungeons_level50_experience) / base

        # Calculates the dungeon overflow weight and returns it to the weight object builder.

        # return {
        #     "weight": math.floor(base),
        #     "weight_overflow": math.pow(remaining / splitter, 0.968),
        # }
        return math.floor(base) + math.pow(remaining / splitter, 0.968) if with_overflow else math.floor(base)

    def dungeon_weight(self, with_overflow: bool = True):
        if self.profile is None or self.profile.get("dungeons") is None:
            return 0
        return sum(
            self._calculate_dungeon_weight(
                cls_data, self.get_cata_lvl(exp.get("experience", 0)), exp.get("experience", 0), with_overflow
            ) for cls_data, exp in self.profile["dungeons"]["player_classes"].items()
        ) + self._calculate_dungeon_weight("catacombs", self.catacombs_level, self.catacombs_xp, with_overflow)

    @property
    def slayer_xp(self) -> float:
        if self.profile and self.profile.get("slayer_bosses") is not None:
            return sum([i.get("xp", 0) for i in self.profile.get("slayer_bosses", {}).values()])
        return 0

    def _calculate_slayer_weight(self, weight_type: str, experience: int, with_overflow: bool = True):
        slayer_weight = self._slayer_weights.get(weight_type)
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

    def slayer_weight(self, with_overflow: bool = True):
        if self.profile is None or self.profile.get("slayer_bosses") is None:
            return 0
        return sum(
            self._calculate_slayer_weight(
                slayer_type,
                self.profile["slayer_bosses"].get(slayer_type, {}).get("xp", 0) if self.profile else 0,
                with_overflow
            )
            for slayer_type in self._slayer_weights.keys()
        )

    def _calculate_skill_weight(self, weight_type: str, level: int, experience: int, with_overflow: bool = True):
        skill_weight = self._skill_weights.get(weight_type)
        if not skill_weight or skill_weight["divider"] == 0 or skill_weight["exponent"] == 0:
            return 0

        # Gets the XP required to max out the skill.
        max_skill_level_xp = self._skills_level60_experience if skill_weight["maxLevel"] == 60 \
            else self._skills_level50_experience

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

    def skill_weight(self, with_overflow: bool = True):
        if self.profile is None:
            return 0

        r = 0
        for skill_type in self._skill_weights.keys():
            if skill_type in self._skill_weight_groups:
                experience = self.profile.get(f"experience_skill_{skill_type}", 0)
                r += self._calculate_skill_weight(
                    skill_type, self.get_skill_lvl(skill_type, experience), experience, with_overflow
                )
        return r

    def weight(self, with_overflow: bool = True):
        if with_overflow:
            if self._weight_with_overflow:
                return self._weight_with_overflow
            self._weight_with_overflow = self.slayer_weight(with_overflow) + self.skill_weight(
                with_overflow) + self.dungeon_weight(with_overflow)
            return self._weight_with_overflow
        else:
            if self._weight_without_overflow:
                return self._weight_without_overflow
            self._weight_without_overflow = self.slayer_weight(with_overflow) + self.skill_weight(
                with_overflow) + self.dungeon_weight(with_overflow)
            return self._weight_without_overflow


class Database:
    pool: asyncpg.pool.Pool = None

    @staticmethod
    async def get_pool():
        kwargs = {
            'host': '170.130.210.9', 'port': 5432, 'user': 'postgres', 'password': 'Nc_^K{/]2&"TAjVTy}.,\\{)4Y&;\\<$7<',
            'min_size': 3, 'max_size': 10, 'command_timeout': 60
        }
        return await asyncpg.create_pool(**kwargs)

    async def main(self):
        Database.pool = await self.get_pool()


class Httpr:
    session: aiohttp.ClientSession = None
    key = "023e759c-4f2c-40e6-a6d3-c1d93a438c98"

    async def main(self):
        Httpr.session = aiohttp.ClientSession()

    async def get_ah_page(self, page: int) -> dict:
        async with self.session.get(f"https://api.hypixel.net/skyblock/auctions?page={page}") as r:
            if r.status == 200:
                return await r.json()

    async def get_guild_inf(self, id: str) -> dict:
        async with self.session.get(f"https://api.hypixel.net/guild?key={self.key}&id={id}") as r:
            if r.status == 200:
                return await r.json()

    async def get_player_inf(self, uuid: str) -> dict:
        async with self.session.get(f"https://api.hypixel.net/skyblock/profiles?uuid={uuid}&key={self.key}") as r:
            if r.status == 200:
                return SkyBlockPlayer(
                    uuid=uuid,
                    player_data=await r.json(),
                    select_profile_on="weight"
                )


async def main():
    webhook_url = 'https://discord.com/api/webhooks/1027288264144605255/mc_jqPyiE_nYyQfubAOt_QFqWQJJZx5aU4vmjmSusw58yPl_McT-ihm-rpjIRXxSn_3Y'
    db = Database()
    await db.main()
    http = Httpr()
    await http.main()

    with open("guildids.json", "r") as f:
        guildids = json.load(f)

    old_guilds = ['53bd67d7ed503e868873eceb',
'5515e1ee0cf2978552888d31',
'56646c420cf24f7aae40744b',
'570940fb0cf2d37483e106b3',
'58fcea210cf2b6a61415ab04',
'5900a2830cf2b6a6141afaa9',
'5917b9d90cf24fbf5b7fa121',
'596e8e650cf2c68698ac86fc',
'5a4fb2d20cf2ce96094b057b',
'5a7879590cf2252f5fc3c53a',
'5ac693ad0cf226336274db5b',
'5aceeba00cf2a4518db446d6',
'5ae0d9330cf2a4518db4586c',
'5b1cc39d0cf27b3d4072290c',
'5b243ac90cf212fe4c98d619',
'5b27f6680cf29ddccd0f1f4a',
'5b61bab40cf204ba11d414fa',
'5b81f77a0cf245cb90c690b5',
'5b9579d70cf24be3ce6e2629',
'5c42d3dd77ce8448250e9b36',
'5c56e3c277ce84ef6c2a30af',
'5cc41f0977ce84d83a2f4a03',
'5ce5ace477ce84cf1204d9b7',
'5d29bbc977ce8415c3fcfa0c',
'5d2d3ed177ce8415c3fcff70',
'5d2e186677ce8415c3fd0074',
'5d2e5aa477ce8415c3fd00e8',
'5d37418077ce84d660de13af',
'5d436ce277ce84b7891fc3fd',
'5d443f3d77ce84b10dc35ec8',
'5d50ef0477ce8487d641bbe3',
'5d8401ef77ce8436b66ac215',
'5d87ccd677ce8436b66ac7ba',
'5d8b8c2577ce8436b66acace',
'5d8be3e877ce8436b66acb4a',
'5d90edb577ce8436b66ad1d2',
'5da0f5b277ce8491d195e822',
'5dec321c8ea8c92086b0f6bd',
'5e01049b8ea8c92086b10a5b',
'5e1d1ee58ea8c92086b12d3d',
'5e264d398ea8c9feb3f0bdd6',
'5e293c428ea8c9feb3f0c01c',
'5e3833808ea8c9feb3f0cf41',
'5e46a8c38ea8c9feb3f0dc65',
'5e4e6d0d8ea8c9feb3f0e44f',
'5e64d3f58ea8c9832198ef12',
'5e752b9f8ea8c932ed0cf522',
'5e784d628ea8c93927ad5935',
'5e8c4c568ea8c9ec75077be5',
'5e915be08ea8c97baf80596c',
'5e91a4778ea8c97baf8059d5',
'5e91f3c08ea8c97baf805a85',
'5e99e85d8ea8c9b706c956ac',
'5ea2f7528ea8c90aea370cfd',
'5ea610b98ea8c9ab72c4dc39',
'5ead88698ea8c9c55c244e6d',
'5eb4d01f8ea8c94128915a85',
'5eba1c5f8ea8c960a61f38ed',
'5ec14e148ea8c93479da0f4b',
'5ec41dcb8ea8c98d63a2803d',
'5ecc8b948ea8c98d63a2936d',
'5ed198fe8ea8c97aa07fe237',
'5ed1af4b8ea8c97aa07fe26c',
'5ed259c98ea8c97aa07fe399',
'5efc03478ea8c97b066140b2',
'5f10a9668ea8c9535477ae13',
'5f1b941a8ea8c9724857eaff',
'5f20063d8ea8c9724857f606',
'5f212b4f8ea8c9724857f90f',
'5f2c931d8ea8c972485813d8',
'5f3fe4fb8ea8c9a71bc958bc',
'5f458e708ea8c9a71bc9668a',
'5f568c528ea8c96f9852dd15',
'5f5c5b068ea8c96f9852e944',
'5f819da18ea8c9720c34d7ab',
'5f82fec88ea8c9720c34da5d',
'5fa44f5f8ea8c992ddb8dbd5',
'5fbd463b8ea8c9d1008d4718',
'5fbea1f38ea8c9d1008d4940',
'5fbec00e8ea8c9d1008d4995',
'5fc573b18ea8c9d1008d616f',
'5fcb90e78ea8c9d1008d720c',
'5fcce4e38ea8c9d1008d764f',
'5fd319aa8ea8c9855c12462b',
'5fd47a7f8ea8c9855c1249ef',
'5fd4cbcb8ea8c9855c124a92',
'5fe788ff8ea8c9855c128080',
'5fea32eb8ea8c9724b8e3f3c',
'5ff092f18ea8c9724b8e55f7',
'5ffc80fa8ea8c9e004b01308',
'60056ef28ea8c9e004b030f7',
'600b55008ea8c9e004b042cb',
'6015b5468ea8c9cb50edaf42',
'60189aa78ea8c9cb50edb82f',
'602915918ea8c9cb50ede5fd',
'602d5f558ea8c90182d333a7',
'602ec95e8ea8c90182d337e7',
'604137778ea8c962f2bb22a8',
'60430c5d8ea8c962f2bb27d5',
'60634c608ea8c962c0d578e4',
'60739d5b8ea8c9ee3f279650',
'6085b5f78ea8c9849e3f89d7',
'609c17508ea8c9bb7f6d82bf',
'60a239ff8ea8c9bb7f6d91ec',
'60ac425a8ea8c9bb7f6da827',
'60c0a3888ea8c99dccc770ab',
'60d744c18ea8c9d0f50e8815',
'60e21f618ea8c913180c8ffe',
'60e9ba0b8ea8c913180ca226',
'60f6836b8ea8c913180cbf12',
'60fc76398ea8c913180ccc23',
'610c5b608ea8c9d8ce9bb436',
'6114b5c88ea8c952404371d5',
'6117cbf88ea8c952404378a5',
'61227a2e8ea8c92e1833e1b1',
'6122cfda8ea8c92e1833e2be',
'6125d9f28ea8c92e1833e8f0',
'612b367f8ea8c9073badb40c',
'6136f6e68ea8c9f201cc5ab9',
'6172c2678ea8c9a202fc1f91',
'6178a19b8ea8c98053ad2081',
'6197c02b8ea8c940a6e5b187',
'61aaa6938ea8c940a6e5c989',
'61bfc8418ea8c9149942adb4',
'62173dc98ea8c9d034161b62',
'623eda8f8ea8c99072e68274',
'626840e78ea8c962e11cb8cf',
'6283d0bd8ea8c962e11ccfd3',
'628fd16c8ea8c94cd9f81438',
'62933fb48ea8c94cd9f816e9',
'62aa1ef510c6cf986d2d3fdc',
'62adf1748ea8c90da91fe0ba',
'62e28bf08ea8c929613332b4',
'62eabab78ea8c9635ef5cd97',
]

    with open("results.json", "r") as f:
        results = json.load(f)

    for guildid in guildids:
        guildids.remove(guildid)
        print(guildid)
        with open("guildids.json", "w") as f:
            json.dump(guildids, f, indent=4)
        if guildid in old_guilds:
            continue
        guild_info = await http.get_guild_inf(guildid)
        if guild_info["guild"] is None:
            continue
        print(guild_info)
        guild_members = guild_info["guild"]["members"]
        total_weight = 0
        for member in guild_members:
            member["uuid"] = member["uuid"].replace("-", "")
            sb_player = await http.get_player_inf(member["uuid"])
            await asyncio.sleep(0.5)
            print(member["uuid"], sb_player.weight())
            total_weight += sb_player.weight()
        average_weight = total_weight / len(guild_members)
        results[guildid] = average_weight
        with open("results.json", "w") as f:
            json.dump(results, f, indent=4)

        if average_weight >= 2500:
            em = discord.Embed(title=guild_info["guild"]["name"],
                               description=f"Average Weight: {average_weight}\nMembers: {len(guild_members)}")

            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhook_url, session=session)
                await webhook.send(embed=em)


asyncio.run(main())
