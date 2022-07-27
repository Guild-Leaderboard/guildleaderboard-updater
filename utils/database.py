from __future__ import annotations

import asyncio
import json
import os
from typing import TYPE_CHECKING, List, Union

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
    average_weight REAL,
    average_skills REAL,
    average_catacombs REAL,
    average_slayer REAL,
    scammers SMALLINT

)
guilds.players is an aray of uuids

CREATE TABLE players (
    uuid TEXT UNIQUE,
    name TEXT,
    weight REAL,
    skill_weight REAL,
    slayer_weight REAL,
    dungeon_weight REAL,
    average_skill REAL,
    catacomb REAL,
    catacomb_xp REAL,
    total_slayer REAL,
    capture_date TIMESTAMP,
    scam_reason TEXT
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

    def format_json(self, record: asyncpg.Record) -> Union[dict, None]:
        if record is None:
            return None
        return {key: (json.loads(value) if key in self.json_keys else value) for (key, value) in dict(record).items()}

    async def insert_new_guild(
            self, guild_id: str, guild_name: str, players: List[str],
            average_weight: float, average_skills: float, average_catacombs: float,
            average_slayer: float, scammers: int
    ):
        await self.pool.execute(
            """
INSERT INTO guilds (guild_id, guild_name, capture_date, players, average_weight, average_skills, average_catacombs, average_slayer, scammers)
VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, $8)        
        """, guild_id, guild_name, players, average_weight, average_skills, average_catacombs, average_slayer, scammers
        )

    async def insert_new_player(self, **kwargs):
        querry = f"""
INSERT INTO players ({", ".join(kwargs.keys())}, capture_date)
VALUES ({", ".join(["$" + str(i + 1) for i in range(len(kwargs))])}, NOW()) ON CONFLICT (uuid) 
DO UPDATE SET {", ".join([f"{key}=${i + 1}" for i, key in enumerate(kwargs.keys())])}, capture_date=NOW();
        """
        await self.pool.execute(querry, *list(kwargs.values()))

    async def get_guild(self, guild_id, conn=None):
        query_str = """
SELECT DISTINCT ON (guild_id) ROUND(average_catacombs::numeric, 2)::float AS average_catacombs, ROUND(average_skills::numeric, 2)::float AS average_skills, ROUND(average_slayer::numeric, 2)::float AS average_slayer, ROUND(average_weight::numeric, 2)::float AS average_weight, guild_id, guild_name, players, NOW() - capture_date::timestamptz at time zone 'UTC' AS time_difference FROM guilds WHERE guild_id = $1 ORDER BY guild_id, capture_date DESC;
        """
        if conn:
            r = await conn.fetchrow(query_str, guild_id)
        else:
            r = await self.pool.fetchrow(query_str, guild_id)
        return self.format_json(r)

    async def get_guild_name(self, guild_id, conn=None):
        query_str = """
SELECT * FROM guilds WHERE guild_name = $1 LIMIT 1;
        """
        if conn:
            r = await conn.fetchrow(query_str, guild_id)
        else:
            r = await self.pool.fetchrow(query_str, guild_id)
        return self.format_json(r)
