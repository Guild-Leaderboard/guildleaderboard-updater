from __future__ import annotations

import asyncio
import datetime
import json
import os
from typing import TYPE_CHECKING, List

import asyncpg
from dotenv import load_dotenv

if TYPE_CHECKING:
    from main import Client

load_dotenv()
DB_IP = os.getenv("DB_IP")
DB_USER = os.getenv("DB_USER")
DB_PWD = os.getenv("DB_PWD")


class Database:
    """
CREATE TABLE guilds (
    guild_id TEXT,
    guild_name TEXT,
    capture_date TIMESTAMP,
    players TEXT[],
    senither_weight REAL,
    skills REAL,
    catacombs REAL,
    slayer REAL,
    scammers SMALLINT,
    position_change SMALLINT,
    lily_weight REAL,
    networth BIGINT

)
guilds.players is an aray of uuids

CREATE TABLE players (
    uuid TEXT UNIQUE,
    name TEXT,
    senither_weight REAL,
    average_skill REAL,
    catacombs REAL,
    catacomb_xp REAL,
    total_slayer REAL,
    capture_date TIMESTAMP,
    scam_reason TEXT,
    lily_weight REAL,
    networth BIGINT
)

CREATE TABLE player_metrics (
    uuid TEXT,
    name TEXT,
    capture_date TIMESTAMP,

    senither_weight REAL,
    lily_weight REAL,
    networth BIGINT,

    zombie_xp BIGINT,
    spider_xp BIGINT,
    wolf_xp BIGINT,
    enderman_xp BIGINT,
    blaze_xp BIGINT,

    catacombs_xp BIGINT,
    catacombs REAL,
    healer REAL,
    healer_xp BIGINT,
    mage REAL,
    mage_xp BIGINT,
    berserk REAL,
    berserk_xp BIGINT,
    archer REAL,
    archer_xp BIGINT,
    tank REAL,
    tank_xp BIGINT,

    average_skill REAL,
    taming REAL,
    taming_xp BIGINT,
    mining REAL,
    mining_xp BIGINT,
    farming REAL,
    farming_xp BIGINT,
    combat REAL,
    combat_xp BIGINT,
    foraging REAL,
    foraging_xp BIGINT,
    fishing REAL,
    fishing_xp BIGINT,
    enchanting REAL,
    enchanting_xp BIGINT,
    alchemy REAL,
    alchemy_xp BIGINT
)

CREATE TABLE guild_information (
    guild_id TEXT,
    discord TEXT
)

CREATE TABLE history (
    type TEXT,
    uuid TEXT,
    name TEXT,
    capture_date TIMESTAMP,
    guild_id TEXT,
    guild_name TEXT
)
"""

    pool: asyncpg.pool.Pool = None

    def __init__(self, client: Client):
        self.client = client
        self.json_keys = []
        self.cached_guilds = {}

    @staticmethod
    async def get_pool():
        kwargs = {
            "host": DB_IP,
            "port": 5432,
            "user": DB_USER,
            "password": DB_PWD,
            "min_size": 3,
            "max_size": 10,
            "command_timeout": 60,
            "loop": asyncio.get_event_loop()
        }
        return await asyncpg.create_pool(**kwargs)

    async def open(self):
        self.client.logger.info('Initializing database connection...')
        Database.pool = await self.get_pool()
        self.client.logger.info('Database connection initialized.')
        return self

    async def close(self):
        await Database.pool.close()
        self.client.logger.info('Database connection closed.')
        return self

    def format_json(self, record: asyncpg.Record) -> dict:
        if record is None:
            return None
        return {key: (json.loads(value) if key in self.json_keys else value) for (key, value) in dict(record).items()}

    async def insert_new_guild(
            self, guild_id: str, guild_name: str, players: List[str], senither_weight: float, skills: float,
            catacombs: float, slayer: float, scammers: int, lily_weight: float, networth: int
    ):
        await self.pool.execute(
            """
INSERT INTO guilds (guild_id, guild_name, capture_date, players, senither_weight, skills, catacombs, slayer, scammers, lily_weight, networth)
VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, $8, $9, $10)        
        """, guild_id, guild_name, players, senither_weight, skills, catacombs, slayer, scammers, lily_weight, networth
        )

    async def insert_new_player(self, **kwargs):
        querry = f"""
INSERT INTO players ({", ".join(kwargs.keys())}, capture_date)
VALUES ({", ".join(["$" + str(i + 1) for i in range(len(kwargs))])}, NOW()) ON CONFLICT (uuid) 
DO UPDATE SET {", ".join([f"{key}=${i + 1}" for i, key in enumerate(kwargs.keys())])}, capture_date=NOW();
        """
        await self.pool.execute(querry, *list(kwargs.values()))

    async def insert_new_player_metric(self, **kwargs):
        querry = f"""
INSERT INTO player_metrics ({", ".join(kwargs.keys())}, capture_date)
VALUES ({", ".join(["$" + str(i + 1) for i in range(len(kwargs))])}, NOW())
            """
        await self.pool.execute(querry, *list(kwargs.values()))

    async def get_guild_name(self, guild_id, conn=None):
        query_str = """
SELECT * FROM guilds WHERE guild_name = $1 LIMIT 1;
        """
        if conn:
            r = await conn.fetchrow(query_str, guild_id)
        else:
            r = await self.pool.fetchrow(query_str, guild_id)
        return self.format_json(r)

    async def get_guild_members(self, guild_id, conn=None):
        query_str = """
SELECT DISTINCT ON (guild_id) 
    players
FROM guilds
    WHERE guild_id = $1 
    ORDER BY guild_id, capture_date DESC;
        """
        if conn:
            r = await conn.fetchrow(query_str, guild_id)
        else:
            r = await self.pool.fetchrow(query_str, guild_id)
        return r["players"] if r else []

    async def insert_history(self, history_type: str, uuid: str, name: str, guild_id: str, guild_name: str,
                             capture_date: datetime.datetime = None):
        args = [history_type, uuid, name, guild_id, guild_name]
        if capture_date:
            args.append(capture_date)

        await self.pool.execute(
            f"""
INSERT INTO history (type, uuid, name, capture_date, guild_id, guild_name)
VALUES ($1, $2, $3, {'$6' if capture_date else 'NOW()'}, $4, $5)        
        """, *args
        )

    async def get_names(self, uuids: List):
        r = await self.pool.fetch("""
SELECT uuid, name FROM players WHERE uuid = ANY($1)""", uuids)
        return {row['uuid']: row['name'] for row in r}
