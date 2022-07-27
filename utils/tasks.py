import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Client
    from objects.api_objects import SkyBlockPlayer


class Tasks:
    def __init__(self, client: "Client"):
        self.client = client

    async def open(self):
        self.client.loop.create_task(self.delete_old_records())
        # print(Time().datetime)
        self.client.loop.create_task(self.update_guilds())
        # self.client.loop.create_task(self.add_new_guild(guild_id="610c5b608ea8c9d8ce9bb436"))

        # self.client.loop.create_task(self.find_new_guilds())
        # for guild in self.guilds_to_add:
        #     print(guild)
        #     r = await self.client.db.get_guild(guild)
        #     if not r:
        self.client.logger.info("Tasks started")
        return self

    async def get_player(self, guild_stats, uuid):
        # r = await self.client.db.pool.fetchrow("""
        # SELECT * FROM players WHERE uuid = $1 ORDER BY capture_date DESC LIMIT 1;
        #             """, uuid)
        #         if r and Time().datetime - r["capture_date"] <= datetime.timedelta(hours=3):
        #             print("Not updating", uuid)
        #             p_stats = dict(r)
        #         else:
        player: SkyBlockPlayer = await self.client.httpr.get_profile(uuid=uuid, select_profile_on="weight")
        try:
            name = await player.get_name(self.client)
        except:
            name = (await self.client.db.pool.fetchrow("""
SELECT name FROM players WHERE uuid=$1 LIMIT 1;            
            """, uuid))["name"]
        try:
            sbzscammer = await self.client.httpr.sbz_check_scammer(uuid)
        except:
            sbzscammer = {
                "success": False,
                "result": {
                    "reason": None
                }

            }
        scam_reason = None
        if sbzscammer["success"]:
            scam_reason = sbzscammer["result"]["reason"]

        p_stats = {
            "uuid": player.uuid,
            "name": name,
            "weight": player.weight(),
            "skill_weight": player.skill_weight(),
            "slayer_weight": player.slayer_weight(),
            "dungeon_weight": player.dungeon_weight(),
            "average_skill": player.average_skill,
            "catacomb": player.catacombs_level,
            "catacomb_xp": player.catacombs_xp,
            "total_slayer": player.slayer_xp,
            "scam_reason": scam_reason,
        }
        await self.client.db.insert_new_player(**p_stats)
        guild_stats["average_weight"] += p_stats["weight"]
        guild_stats["average_slayers"] += p_stats["total_slayer"]
        guild_stats["average_catacombs"] += p_stats["catacomb"]
        guild_stats["average_skill_average"] += p_stats["average_skill"]
        guild_stats["count"] += 1
        if p_stats["scam_reason"]:
            guild_stats["scammers"] += 1

    async def add_new_guild(self, guild_name=None, guild_id=None, weight_req=None):
        r = await self.client.httpr.get_guild_data(name=guild_name, _id=guild_id)
        guild_data = r["guild"]
        if not guild_data:
            return
        members = [i["uuid"] for i in guild_data["members"]]

        guild_stats = {
            "average_weight": 0,
            "average_slayers": 0,
            "average_catacombs": 0,
            "average_skill_average": 0,
            "scammers": 0,
            "count": 0,
        }
        # does_not_need_update_uuids = await self.client.db.does_not_need_update()
        # print(does_not_need_update_uuids)
        # return
        tasks = []
        for uuid in members:
            tasks.append(self.client.loop.create_task(self.get_player(guild_stats, uuid)))
            if len(tasks) >= 2:
                await asyncio.wait(tasks)
                tasks = []

        new_guild_stats = {}
        for i, j in guild_stats.items():
            if i == "scammers":
                new_guild_stats[i] = j
            elif i == 'count':
                continue
            else:
                new_guild_stats[i] = j / guild_stats["count"]

        print(new_guild_stats)
        if weight_req and new_guild_stats["average_weight"] < weight_req:
            print("Not adding", guild_name or guild_id)
            return
        print("Adding", guild_name or guild_id)
        await self.client.db.insert_new_guild(
            guild_id=guild_data["_id"],
            guild_name=guild_data["name"],
            players=[i["uuid"] for i in guild_data["members"]],
            average_weight=new_guild_stats["average_weight"],
            average_skills=new_guild_stats["average_skill_average"],
            average_catacombs=new_guild_stats["average_catacombs"],
            average_slayer=new_guild_stats["average_slayers"],
            scammers=new_guild_stats["scammers"],
        )

    async def delete_old_records(self):
        # members = await self.client.httpr.get_guild_members(name=self.guilds_to_add[0])
        # print(members)
        while True:
            r = await self.client.db.pool.execute("""
DELETE FROM players WHERE (NOW()::date - '90 day'::interval) > capture_date;
            """)
            print(r)
            r = await self.client.db.pool.execute("""
DELETE FROM guilds WHERE (NOW()::date - '90 day'::interval) > capture_date;
            """)
            print(r)
            await asyncio.sleep(600)

    async def update_guilds(self):
        while True:
            r = await self.client.db.pool.fetch("""
SELECT guild_id FROM (SELECT DISTINCT ON (guild_id) * FROM guilds ORDER BY guild_id, capture_date DESC) AS latest_guilds WHERE (NOW() - capture_date::timestamptz at time zone 'UTC') > '1 day'::interval;
""")
            for guild_id in r:
                try:
                    await self.add_new_guild(guild_id=guild_id[0])
                except:
                    pass
            await asyncio.sleep(10)

    async def find_new_guilds(self):
        await asyncio.sleep(60)
        while True:
            r = await self.client.db.pool.fetchrow("""
SELECT name, id, total_members, total_gexp, last_check FROM all_guilds WHERE total_members >= 100 AND total_gexp >= 5000000 ORDER BY last_check DESC LIMIT 1;            
            """)
            if r:
                await self.add_new_guild(guild_name=r["name"], guild_id=r["id"], weight_req=4000)
                await self.client.db.pool.execute("""
UPDATE all_guilds SET last_check = NOW() WHERE id = $1;
            """, r["id"])
                # await asyncio.sleep(10)
