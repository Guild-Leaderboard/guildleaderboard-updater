import asyncio
import datetime
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
        _ = self.client.loop.create_task(self.delete_old_records())
        _ = self.client.loop.create_task(self.update_positions())
        _ = self.client.loop.create_task(self.update_guilds())
        _ = self.client.loop.create_task(self.resolve_names())

        # t = self.client.loop.create_task(self.update_guild(guild_id="5b243ac90cf212fe4c98d619"))
        # t = self.client.loop.create_task(self.update_player({}, "5e22209be5864a088761aa6bde56a090"))
        # self.update_positions()

        # self.client.loop.create_task(self.add_new_guild(guild_name="Menhir"))  # Drachen Jaeger 3

        self.client.logger.info("Tasks started")
        return self

    async def update_player(self, guild_stats, uuid):
        player: SkyBlockPlayer = await self.client.httpr.get_profile(uuid=uuid)

        if not player.member_profile:
            networth = 0
        else:
            museum_data = None
            if player.profile_id:
                museum_data = await self.client.httpr.get_museum_data(player.profile_id)

            full_profile = [
                profile for profile in player.player_data.get("profiles", []) if
                profile["members"][uuid] == player.member_profile
            ][0]
            r = await self.client.httpr.get_networth(
                uuid=uuid, profile=full_profile,
                museum_data=museum_data.get("members", {}).get(uuid) if museum_data else None
            )
            networth = r["networth"]

        try:
            name = await player.get_name(self.client)
        except:
            name = None

        lily_weight = await player.lily_weight(self.client)
        skill_average = await player.average_skill(self.client)

        p_profile = player.member_profile if player.member_profile else {}

        dungeon_types = p_profile.get("dungeons", {}).get("player_classes", {})
        slayer_bosses = p_profile.get("slayer", {}).get("slayer_bosses", {})
        skill_xps = p_profile.get("player_data", {}).get("experience", {})

        p_stats = {
            "uuid": player.uuid,
            "name": name,
            "senither_weight": player.senither_weight(),
            "lily_weight": lily_weight["total"],
            "networth": networth,
            "sb_experience": player.sb_experience,

            "total_slayer": player.slayer_xp,
            "zombie_xp": slayer_bosses.get("zombie", {}).get("xp", 0),
            "spider_xp": slayer_bosses.get("spider", {}).get("xp", 0),
            "wolf_xp": slayer_bosses.get("wolf", {}).get("xp", 0),
            "enderman_xp": slayer_bosses.get("enderman", {}).get("xp", 0),
            "blaze_xp": slayer_bosses.get("blaze", {}).get("xp", 0),
            "vampire_xp": slayer_bosses.get("vampire", {}).get("xp", 0),

            "catacombs_xp": player.catacombs_xp,
            "healer_xp": dungeon_types.get("healer", {}).get("experience", 0),
            "mage_xp": dungeon_types.get("mage", {}).get("experience", 0),
            "berserk_xp": dungeon_types.get("berserk", {}).get("experience", 0),
            "archer_xp": dungeon_types.get("archer", {}).get("experience", 0),
            "tank_xp": dungeon_types.get("tank", {}).get("experience", 0),


            "average_skill": skill_average,
            "taming_xp": skill_xps.get("SKILL_TAMING", 0),
            "mining_xp": skill_xps.get("SKILL_MINING", 0),
            "farming_xp": skill_xps.get("SKILL_FARMING", 0),
            "combat_xp": skill_xps.get("SKILL_COMBAT", 0),
            "foraging_xp": skill_xps.get("SKILL_FORAGING", 0),
            "fishing_xp": skill_xps.get("SKILL_FISHING", 0),
            "enchanting_xp": skill_xps.get("SKILL_ENCHANTING", 0),
            "alchemy_xp": skill_xps.get("SKILL_ALCHEMY", 0),
            "carpentry_xp": skill_xps.get("SKILL_CARPENTRY", 0),
        }
        print(p_stats)
        await self.client.db.upsert_player_entry(**p_stats)

        guild_stats["senither_weight"] += p_stats["senither_weight"]
        guild_stats["lily_weight"] += p_stats["lily_weight"]
        guild_stats["slayer"] += p_stats["total_slayer"]
        guild_stats["catacombs"] += player.catacombs_level_overflow
        guild_stats["skills"] += p_stats["average_skill"]
        guild_stats["networth"] += p_stats["networth"]
        guild_stats["sb_experience"] += p_stats["sb_experience"]
        guild_stats["count"] += 1

    async def add_guild_history(self, old_players, new_players, guild_id, guild_name):
        leave_uuids = [uuid for uuid in old_players if uuid not in new_players]
        join_uuids = [uuid for uuid in new_players if uuid not in old_players]

        name_uuid_dict = await self.client.db.get_names(leave_uuids + join_uuids)
        print(name_uuid_dict)

        for leave_uuid in leave_uuids:
            name = name_uuid_dict.get(leave_uuid, leave_uuid)
            await self.client.db.insert_history("0", leave_uuid, name, guild_id, guild_name)

        for join_uuid in join_uuids:
            name = name_uuid_dict.get(join_uuid, join_uuid)
            await self.client.db.insert_history("1", join_uuid, name, guild_id, guild_name)

    async def update_guild(self, guild_name=None, guild_id=None, weight_req=None):
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
            "count": 0,
            "networth": 0,
            "sb_experience": 0,
        }

        tasks = []
        for uuid in members:
            tasks.append(self.client.loop.create_task(self.update_player(guild_stats, uuid)))
            if len(tasks) >= 2:
                await asyncio.wait(tasks)
                tasks = []

        if tasks:
            await asyncio.wait(tasks)

        if guild_stats["count"] != len(members):
            print("Count mismatch", guild_stats["count"], len(members), guild_name)

        new_guild_stats = {}
        for i, j in guild_stats.items():
            if i == 'count':
                continue
            else:
                new_guild_stats[i] = j / guild_stats["count"]

        print(new_guild_stats)
        if weight_req and new_guild_stats["senither_weight"] < weight_req:
            print("Not adding", guild_name or guild_id)
            return

        print("Adding", guild_data["name"])
        old_guild_members = await self.client.db.get_guild_members(guild_data["_id"])
        new_guild_members = [i["uuid"] for i in guild_data["members"]]

        await self.client.db.upsert_guild_entry(
            guild_id=guild_data["_id"],
            guild_name=guild_data["name"],
            players=new_guild_members,
            senither_weight=new_guild_stats["senither_weight"],
            lily_weight=new_guild_stats["lily_weight"],
            skills=new_guild_stats["skills"],
            catacombs=new_guild_stats["catacombs"],
            slayer=new_guild_stats["slayer"],
            networth=new_guild_stats["networth"],
            sb_experience=new_guild_stats["sb_experience"],
        )

        await self.add_guild_history(old_guild_members, new_guild_members, guild_data["_id"], guild_data["name"])
        await self.update_positions()

    async def update_guilds(self):
        while True:
            # Find guilds that have not been updated in the last 24 hours
            r = self.client.db.guilds.find({
                "metrics.0.capture_date": {"$lt": datetime.datetime.now() - datetime.timedelta(days=1)}
            }, {"_id": 1})

            async for g in r:
                print(g["_id"])
                try:
                    await self.update_guild(guild_id=g["_id"])
                except asyncio.exceptions.TimeoutError:
                    pass
            await asyncio.sleep(10)

    async def delete_old_records(self):
        while True:
            # delete metrics older than 90 days
            guilds = self.client.db.guilds.find({}, {"metrics": 1})
            async for guild in guilds:
                new_metrics = []
                for metric in guild["metrics"]:
                    if metric["capture_date"] > datetime.datetime.now() - datetime.timedelta(days=90):
                        new_metrics.append(metric)
                await self.client.db.guilds.update_one({"_id": guild["_id"]}, {"$set": {"metrics": new_metrics}})

            players = self.client.db.players.find({}, {"metrics": 1})
            async for player in players:
                new_metrics = []
                for metric in player["metrics"]:
                    if metric["capture_date"] > datetime.datetime.now() - datetime.timedelta(days=90):
                        new_metrics.append(metric)
                await self.client.db.players.update_one({"_id": player["_id"]}, {"$set": {"metrics": new_metrics}})

            print("Deleted old records")
            await asyncio.sleep(3600)

    async def update_positions(self):
        # Get only the latest metrics
        all_guilds = self.client.db.guilds.find({}, {"guild_name": 1, "_id": 1, "metrics": {"$slice": 4}})
        # print(list(current_guilds))
        current_guilds = []
        old_guilds = []
        async for g in all_guilds:
            current_guilds.append({
                "_id": g["_id"],
                "weighted_stats": g["metrics"][0]["weighted_stats"]
            })
            old_guilds.append({
                "_id": g["_id"],
                "weighted_stats": g["metrics"][3]["weighted_stats"]
            })

        cur_guilds_sorted = sorted(current_guilds, key=lambda x: int(x["weighted_stats"].split(",")[6]), reverse=True)
        old_guilds_sorted = sorted(old_guilds, key=lambda x: int(x["weighted_stats"].split(",")[6]), reverse=True)

        current_guild_positions = {d["_id"]: i + 1 for i, d in enumerate(cur_guilds_sorted)}
        old_guild_positions = {d["_id"]: i + 1 for i, d in enumerate(old_guilds_sorted)}

        positions_difference = {
            k: old_guild_positions[k] - current_guild_positions[k] for k in
            set(current_guild_positions.keys()) & set(old_guild_positions.keys())
        }
        # print(positions_difference)
        # for i, k in positions_difference.items():
        #     print("Position Change: ", i, k)
        #     print("Previous", old_guild_positions[i])
        #     print("Current", current_guild_positions[i])
        #     print("")

        for guild_id, position_change in positions_difference.items():
            await self.client.db.guilds.update_one({"_id": guild_id}, {"$set": {"position_change": position_change}})
        await asyncio.sleep(1)
        # Update positions Array
        guild_position_str = {}
        for i in range(7):
            cur_guilds_sorted = sorted(current_guilds, key=lambda x: float(x["weighted_stats"].split(",")[i]),
                                       reverse=True)
            for j, g in enumerate(cur_guilds_sorted):
                if g["_id"] not in guild_position_str:
                    guild_position_str[g["_id"]] = []

                guild_position_str[g["_id"]].append(str(j + 1))

        for i, position_str in guild_position_str.items():
            await self.client.db.guilds.update_one({"_id": i}, {"$set": {"positions": ",".join(position_str)}})

    async def resolve_names(self):
        while True:
            broken_rows = self.client.db.history.find({"uuid": {"$eq": "name"}})
            uuids = [i["uuid"] async for i in broken_rows]
            uuid_name_dict = await self.client.db.get_names(uuids)
            async for row in broken_rows:
                try:
                    name = uuid_name_dict[row["uuid"]]
                except KeyError:
                    name = await self.client.httpr.get_name(row["uuid"])
                await self.client.db.history.update_one({"uuid": row["uuid"]}, {"$set": {"name": name}})
            await asyncio.sleep(3600)
