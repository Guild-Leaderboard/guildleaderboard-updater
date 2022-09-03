import asyncio
from math import sin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Client
    from objects.api_objects import SkyBlockPlayer


def weight_multiplier(members):
    frequency = sin(members / (125 / 0.927296)) + 0.2
    return members / 125 + (1 - members / 125) * frequency


class Tasks:
    def __init__(self, client: "Client"):
        self.client: Client = client

    async def open(self):
        self.client.loop.create_task(self.delete_old_records())
        self.client.loop.create_task(self.resolve_names())
        self.client.loop.create_task(self.update_guilds())
        # r = await self.client.db.pool.fetch("""
        # SELECT * FROM history
        #         """)
        #         with open("history.json", "w") as f:
        #             json.dump([{key: str(value) if key == "capture_date" else value for key, value in dict(i).items()} for i in r], f, indent=4)

        # self.client.loop.create_task(self.add_new_guild(guild_name="Cromax"))
        # self.client.loop.create_task(self.find_new_guilds())

        self.client.logger.info("Tasks started")
        return self

    async def resolve_names(self):
        while True:
            broken_rows = await self.client.db.pool.fetch("""
    SELECT * FROM history WHERE uuid = name ORDER by capture_date DESC;
            """)
            uuids = [i["uuid"] for i in broken_rows]
            uuid_name_dict = await self.client.db.get_names(uuids)
            for row in broken_rows:
                try:
                    name = uuid_name_dict[row["uuid"]]
                except KeyError:
                    name = await self.client.httpr.get_name(row["uuid"])
                await self.client.db.pool.execute("""
    UPDATE history SET name = $1 WHERE uuid = $2;
                """, name, row["uuid"])
            await asyncio.sleep(3600)

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
        lily_weight = await player.lily_weight(self.client)

        p_stats = {
            "uuid": player.uuid,
            "name": name,
            "senither_weight": player.senither_weight(),
            "lily_weight": lily_weight["total"],
            "average_skill": player.average_skill,
            "catacombs": player.catacombs_level,
            "total_slayer": player.slayer_xp,
            "scam_reason": scam_reason,
        }
        await self.client.db.insert_new_player(**p_stats)
        guild_stats["senither_weight"] += p_stats["senither_weight"]
        guild_stats["lily_weight"] += p_stats["lily_weight"]
        guild_stats["slayer"] += p_stats["total_slayer"]
        guild_stats["catacombs"] += p_stats["catacombs"]
        guild_stats["skills"] += p_stats["average_skill"]
        guild_stats["count"] += 1
        if p_stats["scam_reason"]:
            guild_stats["scammers"] += 1

        dungeon_types = player.profile.get("dungeons", {}).get("player_classes", {})

        player_metrics = {
            "uuid": player.uuid,
            "name": name,

            "senither_weight": player.senither_weight(),
            "lily_weight": lily_weight["total"],

            "zombie_xp": player.profile.get("slayer_bosses", {}).get("zombie", {}).get("xp", 0),
            "spider_xp": player.profile.get("slayer_bosses", {}).get("spider", {}).get("xp", 0),
            "wolf_xp": player.profile.get("slayer_bosses", {}).get("wolf", {}).get("xp", 0),
            "enderman_xp": player.profile.get("slayer_bosses", {}).get("enderman", {}).get("xp", 0),
            "blaze_xp": player.profile.get("slayer_bosses", {}).get("blaze", {}).get("xp", 0),

            "catacombs_xp": player.catacombs_xp,
            "catacombs": player.catacombs_level,
            "healer": player.get_cata_lvl(dungeon_types.get("healer", {}).get("experience", 0)),
            "healer_xp": dungeon_types.get("healer", {}).get("experience", 0),
            "mage": player.get_cata_lvl(dungeon_types.get("mage", {}).get("experience", 0)),
            "mage_xp": dungeon_types.get("mage", {}).get("experience", 0),
            "berserk": player.get_cata_lvl(dungeon_types.get("berserk", {}).get("experience", 0)),
            "berserk_xp": dungeon_types.get("berserk", {}).get("experience", 0),
            "archer": player.get_cata_lvl(dungeon_types.get("archer", {}).get("experience", 0)),
            "archer_xp": dungeon_types.get("archer", {}).get("experience", 0),
            "tank": player.get_cata_lvl(dungeon_types.get("tank", {}).get("experience", 0)),
            "tank_xp": dungeon_types.get("tank", {}).get("experience", 0),

            "average_skill": player.average_skill,
            "taming": player.get_skill_lvl("taming", player.profile.get("experience_skill_taming", 0)),
            "taming_xp": player.profile.get("experience_skill_taming", 0),
            "mining": player.get_skill_lvl("mining", player.profile.get("experience_skill_mining", 0)),
            "mining_xp": player.profile.get("experience_skill_mining", 0),
            "farming": player.get_skill_lvl("farming", player.profile.get("experience_skill_farming", 0)),
            "farming_xp": player.profile.get("experience_skill_farming", 0),
            "combat": player.get_skill_lvl("combat", player.profile.get("experience_skill_combat", 0)),
            "combat_xp": player.profile.get("experience_skill_combat", 0),
            "foraging": player.get_skill_lvl("foraging", player.profile.get("experience_skill_foraging", 0)),
            "foraging_xp": player.profile.get("experience_skill_foraging", 0),
            "fishing": player.get_skill_lvl("fishing", player.profile.get("experience_skill_fishing", 0)),
            "fishing_xp": player.profile.get("experience_skill_fishing", 0),
            "enchanting": player.get_skill_lvl("enchanting", player.profile.get("experience_skill_enchanting", 0)),
            "enchanting_xp": player.profile.get("experience_skill_enchanting", 0),
            "alchemy": player.get_skill_lvl("alchemy", player.profile.get("experience_skill_alchemy", 0)),
            "alchemy_xp": player.profile.get("experience_skill_alchemy", 0),
        }

        await self.client.db.insert_new_player_metric(**player_metrics)

    async def add_guild_history(self, old_players, new_players, guild_id, guild_name):
        leave_uuids = [uuid for uuid in old_players if uuid not in new_players]
        join_uuids = [uuid for uuid in new_players if uuid not in old_players]

        name_uuid_dict = await self.client.db.get_names(leave_uuids + join_uuids)

        for leave_uuid in leave_uuids:
            name = name_uuid_dict.get(leave_uuid, leave_uuid)
            await self.client.db.insert_history("0", leave_uuid, name, guild_id, guild_name)

        for join_uuid in join_uuids:
            name = name_uuid_dict.get(join_uuid, join_uuid)
            await self.client.db.insert_history("1", join_uuid, name, guild_id, guild_name)

    async def add_new_guild(self, guild_name=None, guild_id=None, weight_req=None):
        r = await self.client.httpr.get_guild_data(name=guild_name, _id=guild_id)
        guild_data = r["guild"]
        if not guild_data:
            return
        members = [i["uuid"] for i in guild_data["members"]]

        guild_stats = {
            "senither_weight": 0,
            "lily_weight": 0,
            "slayer": 0,
            "catacombs": 0,
            "skills": 0,
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

        if guild_stats["count"] != len(members):
            print("Count mismatch", guild_stats["count"], len(members), guild_name)

        new_guild_stats = {}
        for i, j in guild_stats.items():
            if i == "scammers":
                new_guild_stats[i] = j
            elif i == 'count':
                continue
            else:
                new_guild_stats[i] = j / guild_stats["count"]

        print(new_guild_stats)
        if weight_req and new_guild_stats["senither_weight"] < weight_req:
            print("Not adding", guild_name or guild_id)
            return

        print("Adding", guild_name or guild_id)
        old_guild_members = await self.client.db.get_guild_members(guild_data["_id"])
        new_guild_members = [i["uuid"] for i in guild_data["members"]]

        await self.client.db.insert_new_guild(
            guild_id=guild_data["_id"],
            guild_name=guild_data["name"],
            players=new_guild_members,
            senither_weight=new_guild_stats["senither_weight"],
            lily_weight=new_guild_stats["lily_weight"],
            skills=new_guild_stats["skills"],
            catacombs=new_guild_stats["catacombs"],
            slayer=new_guild_stats["slayer"],
            scammers=new_guild_stats["scammers"],
        )
        await self.add_guild_history(old_guild_members, new_guild_members, guild_data["_id"], guild_data["name"])

        self.client.loop.create_task(self.update_positions())

    async def delete_old_records(self):
        # members = await self.client.httpr.get_guild_members(name=self.guilds_to_add[0])
        # print(members)
        while True:
            r1 = await self.client.db.pool.execute("""
DELETE FROM players WHERE (NOW()::date - '90 day'::interval) > capture_date;
            """)
            r2 = await self.client.db.pool.execute("""
DELETE FROM guilds WHERE (NOW()::date - '90 day'::interval) > capture_date;
            """)
            r3 = await self.client.db.pool.execute("""
DELETE FROM player_metrics WHERE (NOW()::date - '90 day'::interval) > capture_date;
            """)
            print(r1, r2, r3)
            await asyncio.sleep(600)

    async def update_guilds(self):
        while True:
            r = await self.client.db.pool.fetch("""
SELECT guild_id FROM (SELECT DISTINCT ON (guild_id) * FROM guilds ORDER BY guild_id, capture_date DESC) AS latest_guilds WHERE (NOW() - capture_date::timestamptz at time zone 'UTC') > '1 day'::interval;
""")
            for guild_id in r:
                try:
                    await self.add_new_guild(guild_id=guild_id[0])
                except asyncio.exceptions.TimeoutError:
                    pass
            await asyncio.sleep(10)

    async def update_positions(self):
        old_guilds = [self.client.db.format_json(i) for i in (await self.client.db.pool.fetch("""
    SELECT DISTINCT ON (guild_id) guild_id,
                          guild_name,
                          senither_weight,
                          array_length(players, 1) AS players                      
    FROM guilds
        WHERE Now() - capture_date >=  '3 days'
    ORDER BY guild_id, capture_date DESC; 
        """))]
        current_guilds = [self.client.db.format_json(i) for i in (await self.client.db.pool.fetch("""
    SELECT DISTINCT ON (guild_id) guild_id,
                          guild_name,
                          senither_weight,
                          array_length(players, 1) AS players                       
    FROM guilds
    ORDER BY guild_id, capture_date DESC;    
        """))]

        current_guilds_sorted = sorted(current_guilds,
                                       key=lambda x: x["senither_weight"] * weight_multiplier(x["players"]),
                                       reverse=True)
        old_guilds_sorted = sorted(old_guilds, key=lambda x: x["senither_weight"] * weight_multiplier(x["players"]),
                                   reverse=True)

        old_guild_positions = {d["guild_id"]: i + 1 for i, d in enumerate(old_guilds_sorted)}
        current_guild_positions = {d["guild_id"]: i + 1 for i, d in enumerate(current_guilds_sorted)}
        # positions_difference = {
        #     k: old_guild_positions[k] - current_guild_positions[k] for k in
        #     set(current_guild_positions.keys()) & set(old_guild_positions.keys())
        # }
        positions_difference = {
            k: old_guild_positions[k] - current_guild_positions[k] for k in
            set(current_guild_positions.keys()) & set(old_guild_positions.keys())
        }
        print(positions_difference)
        for guild_id, position_change in positions_difference.items():
            await self.client.db.pool.execute("""
    UPDATE guilds SET position_change = $1 WHERE guild_id = $2;
            """, position_change, guild_id)
        print("Updated positions", len(old_guild_positions), len(current_guild_positions))

#     async def find_new_guilds(self):
#         await asyncio.sleep(60)
#         while True:
#             r = await self.client.db.pool.fetchrow("""
# SELECT name, id, total_members, total_gexp, last_check FROM all_guilds WHERE total_members >= 100 AND total_gexp >= 5000000 ORDER BY last_check DESC LIMIT 1;
#             """)
#             if r:
#                 await self.add_new_guild(guild_name=r["name"], guild_id=r["id"], weight_req=4000)
#                 await self.client.db.pool.execute("""
# UPDATE all_guilds SET last_check = NOW() WHERE id = $1;
#             """, r["id"])
#                 # await asyncio.sleep(10)

#     async def test(self):
#         r = await self.client.db.pool.fetch("""
# SELECT DISTINCT ON (guild_id)
#     guild_id, guild_name
# FROM guilds
#             """)
#         all_guilds = {x["guild_id"]: x["guild_name"] for x in r}
#         progess = 0
#         for guild_id, guild_name in all_guilds.items():
#             guild_history = await self.client.db.pool.fetch("""
# SELECT
#     players,
#     capture_date::timestamptz at time zone 'UTC' AS capture_date
# FROM guilds
#     WHERE guild_id = $1
# ORDER BY capture_date
#                 """, guild_id)
#             prev_players = []
#
#             for guild_history_entry in guild_history:
#                 current_players = guild_history_entry["players"]
#                 capture_date: datetime.timedelta = guild_history_entry["capture_date"]
#
#                 leave_uuids = [uuid for uuid in prev_players if uuid not in current_players]
#                 join_uuids = [uuid for uuid in current_players if uuid not in prev_players]
#
#                 name_uuid_dict = await self.client.db.get_names(leave_uuids + join_uuids)
#
#                 for leave_uuid in leave_uuids:
#                     await self.client.db.insert_history("0", leave_uuid, name_uuid_dict.get(leave_uuid, leave_uuid),
#                                                         guild_id, guild_name, capture_date)
#
#                 for join_uuid in join_uuids:
#                     await self.client.db.insert_history("1", join_uuid, name_uuid_dict.get(join_uuid, join_uuid),
#                                                         guild_id, guild_name, capture_date)
#
#                 prev_players = current_players
#             print(guild_id, progess)
#             progess += 1
