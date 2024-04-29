import datetime
from math import *
from typing import List

# import motor
from motor.motor_asyncio import AsyncIOMotorClient


def weight_multiplier(members):
    frequency = sin(members / (125 / 0.927296)) + 0.2
    return members / 125 + (1 - members / 125) * frequency


"""
history {
    _id str, index

    type str,
    uuid str,
    name str,
    capture_date datetime,
    guild_id str,
    guild_name str
}

guilds {
    _id str, # guild id index
    guild_name str,
    position_change int,
    discord str,   

    metrics: [ # latest metrics first
        {
            capture_date TIMESTAMP, index
            players TEXT[],
            multiplier REAL,            
            weighted_stats str # comma separated list of stats
                    {
                        catacombs float,
                        skills float,
                        slayer int,
                        senither_weight int,
                        lily_weight int,
                        networth int,
                        sb_experience int 
                    }
        },
        ...
    ],
    positions str # comma separated list of positions 
                {
                    catacombs float,
                    skills float,
                    slayer int,
                    senither_weight int,
                    lily_weight int,
                    networth int,
                    sb_experience int    
                }    
}
guilds.players is an aray of uuids

players {
    _id str, index # uuid
    name str,

    latest_senither int,
    latest_lily int,
    latest_nw int,
    latest_sb_xp int,
    latest_slayer int,
    latest_cata int,
    latest_asl float,
    latest_capture_date TIMESTAMP,



    metrics: [ # latest metrics first
        {
            capture_date TIMESTAMP, index

            general_stats str # comma separated list of stats
                    {
                        senither_weight REAL,
                        lily_weight REAL,
                        networth BIGINT,
                        sb_experience BIGINT,
                    }
            slayer_stats str # comma separated list of stats
                    {
                        total_slayer REAL,
                        zombie_xp BIGINT,
                        spider_xp BIGINT,
                        wolf_xp BIGINT,
                        enderman_xp BIGINT,
                        blaze_xp BIGINT,
                        vampire_xp BIGINT,
                    }
            dungeon_stats str # comma separated list of stats
                    {
                        catacombs_xp BIGINT,
                        healer_xp BIGINT,
                        mage_xp BIGINT,
                        berserk_xp BIGINT,
                        archer_xp BIGINT,
                        tank_xp BIGINT,
                    }
            skill_stats str # comma separated list of stats
                    {
                        average_skill REAL,
                        taming_xp BIGINT,
                        mining_xp BIGINT,
                        farming_xp BIGINT,
                        combat_xp BIGINT,
                        foraging_xp BIGINT,
                        fishing_xp BIGINT,
                        enchanting_xp BIGINT,
                        alchemy_xp BIGINT,
                        carpentry_xp BIGINT
                    }
        },
        ...
    ]

"""


class Database2:
    def __init__(self, app=None):
        self.client = AsyncIOMotorClient('195.201.43.165', 27017, username='root', password='R8xC7rdEE8')
        self.db = self.client.guildleaderboard
        self.app = app

        self.history = self.db.history
        self.history.create_index([("_id", 1)])
        self.history.create_index([("uuid", 1)])
        self.history.create_index([("guild_id", 1)])

        self.guilds = self.db.guilds
        self.guilds.create_index([("_id", 1)])

        self.players = self.db.players
        self.players.create_index([("_id", 1)])
        self.players.create_index([("name", 1)])

        self.players.create_index([("latest_senither", -1)])
        self.players.create_index([("latest_nw", -1)])
        self.players.create_index([("latest_sb_xp", -1)])
        self.players.create_index([("latest_slayer", -1)])
        self.players.create_index([("latest_cata", -1)])
        self.players.create_index([("latest_asl", -1)])

    async def upsert_guild_entry(
            self, guild_id: str, guild_name: str, players: List[str], senither_weight: float, skills: float,
            catacombs: float, slayer: float, lily_weight: float, networth: int, sb_experience: int, discord: str = None
    ):
        multiplier = weight_multiplier(len(players))
        weighted_stats = f"{round(senither_weight * multiplier)},{round(skills, 2)},{round(catacombs, 2)},{round(slayer)},{round(lily_weight * multiplier)},{round(networth)},{round(sb_experience * multiplier)}"

        metrics = {
            "capture_date": datetime.datetime.now(),
            "players": players,
            "multiplier": round(weight_multiplier(len(players)), 3),
            "weighted_stats": weighted_stats
        }

        await self.guilds.update_one(
            {"_id": guild_id},
            {
                "$push": {"metrics": {"$each": [metrics], "$position": 0}},
                "$set": {
                    "guild_name": guild_name,
                    "discord": discord,
                    "positions": "0,0,0,0,0,0,0",
                    "position_change": 0
                }
            },
            upsert=True
        )

    async def upsert_player_entry(
            self, uuid: str, name: str, senither_weight: float, lily_weight: float, networth: int, sb_experience: int,

            total_slayer: int, zombie_xp: int, spider_xp: int, wolf_xp: int, enderman_xp: int, blaze_xp: int,
            vampire_xp: int,

            catacombs_xp: int, healer_xp: int, mage_xp: int, berserk_xp: int, archer_xp: int,
            tank_xp: int,

            average_skill: float, taming_xp: int, mining_xp: int, farming_xp: int, combat_xp: int, foraging_xp: int,
            fishing_xp: int, enchanting_xp: int, alchemy_xp: int, carpentry_xp: int
    ):
        general_stats = f"{round(senither_weight, 2)},{round(lily_weight, 2)},{int(networth)},{round(sb_experience)}"
        slayer_stats = f"{int(total_slayer)},{int(zombie_xp)},{int(spider_xp)},{int(wolf_xp)},{int(enderman_xp)},{int(blaze_xp)},{int(vampire_xp)}"
        dungeon_stats = f"{int(catacombs_xp)},{int(healer_xp)},{int(mage_xp)},{int(berserk_xp)},{int(archer_xp)},{int(tank_xp)}"
        skill_stats = f"{round(average_skill, 2)},{int(taming_xp)},{int(mining_xp)},{int(farming_xp)},{int(combat_xp)},{int(foraging_xp)},{int(fishing_xp)},{int(enchanting_xp)},{int(alchemy_xp)},{int(carpentry_xp)}"
        capture_date = datetime.datetime.now()

        metrics = {
            "capture_date": capture_date,
            "general_stats": general_stats,
            "slayer_stats": slayer_stats,
            "dungeon_stats": dungeon_stats,
            "skill_stats": skill_stats
        }

        await self.players.update_one(
            {"_id": uuid},
            {
                "$push": {"metrics": {"$each": [metrics], "$position": 0}},
                "$set": {
                    "name": name,
                    "latest_senither": round(senither_weight, 2),
                    "latest_lily": round(lily_weight, 2),
                    "latest_nw": int(networth),
                    "latest_sb_xp": int(sb_experience),
                    "latest_slayer": int(total_slayer),
                    "latest_cata": int(catacombs_xp),
                    "latest_asl": round(average_skill, 2),
                    "latest_capture_date": capture_date
                }
            },
            upsert=True
        )

    async def insert_history(self, history_type: str, uuid: str, name: str, guild_id: str, guild_name: str,
                             capture_date: datetime.datetime = None):
        if capture_date is None:
            capture_date = datetime.datetime.now()

        await self.history.insert_one({
            "type": str(history_type),
            "uuid": uuid,
            "name": name,
            "guild_id": guild_id,
            "guild_name": guild_name,
            "capture_date": capture_date
        })

    async def get_guild_members(self, guild_id: str):
        # Get the latest list of guild members
        r = await self.guilds.find_one({"_id": guild_id})
        return r["metrics"][0]["players"]

    async def get_names(self, uuids: List):
        r = self.players.find({"_id": {"$in": uuids}})
        return {row["_id"]: row["name"] async for row in r}

    async def main(self):
        pass


if __name__ == "__main__":
    import asyncio

    async def main():
        db = Database2()
        await db.main()

    asyncio.run(main())
