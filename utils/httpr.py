from __future__ import annotations

import os
from typing import TYPE_CHECKING

from objects.api_objects import SkyBlockPlayer
from objects.cache import RateLimitSession, Ratelimit, ratelimit_apis
from objects.errors import *

if TYPE_CHECKING:
    from main import Client

SBZ_KEY = os.getenv("SBZ_KEY")


class Httpr:
    """
    Example on how to do an HTTPS request in a command with proper ratelimit in mind.

    await interaction.response.defer()
    uuid = await self.client.httpr.ratelimit_handle(
        self.client.httpr.get_uuid(player),
        interaction
    )
    """
    session = None
    host_mapping = {}

    def __init__(self, client: Client):
        self.client = client

    async def open(self):
        Httpr.session = RateLimitSession(logger=self.client.logger)
        self.client.logger.info("RateLimitSession has been initialized")
        return self

    async def close(self):
        if Httpr.session:
            await Httpr.session.close()
            self.client.logger.info("RateLimitSession closed")
        return self

    @staticmethod
    def get_ratelimit(host: str) -> Ratelimit:
        return Httpr.session.ratelimit_handler.get_ratelimit(host)

    """
    Mojang APIs
    """

    @ratelimit_apis("api.mojang.com", host_mapping=host_mapping)
    async def get_uuid(self, name: str, db_check: bool = True) -> str:
        async with Httpr.session.get(f"https://api.mojang.com/users/profiles/minecraft/{name}") as r:
            if r.status == 200:
                res = (await r.json())
                return res["id"]
            elif r.status == 204:
                raise InvalidName("No UUID found for name", r, name)
            elif r.status == 400:
                rj = await r.json()
                raise UnexpectedResponse(f"{rj['error']} | {rj['errorMessage']}", r)
            else:
                raise UnexpectedResponse("Error while getting UUID", r)

    @ratelimit_apis("api.mojang.com", host_mapping=host_mapping)
    async def _mojang_get_name(self, uuid: str) -> str:
        async with Httpr.session.get(f"https://api.mojang.com/user/profiles/{uuid}/names") as r:
            if r.status == 200:
                res = (await r.json())[-1]['name']
                return res
            elif r.status == 204:
                raise InvalidUUID("No name found for UUID", r, uuid)
            else:
                raise UnexpectedResponse(
                    f"Error while getting name {r.status}", r)

    @ratelimit_apis("sessionserver.mojang.com", host_mapping=host_mapping)
    async def _session_get_name(self, uuid: str, ) -> str:
        async with Httpr.session.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}") as r:
            if r.status == 200:
                res = (await r.json())['name']
                return res
            elif r.status == 204:
                raise InvalidUUID("No name found for UUID", r, uuid)
            else:
                raise UnexpectedResponse(
                    f"Error while getting name {r.status}", r)

    @ratelimit_apis(_mojang_get_name, _session_get_name, host_mapping=host_mapping)
    async def get_name(self, uuid: str, db_check: bool = True,
                       return_uuid: bool = False) -> str:
        if self.get_ratelimit("sessionserver.mojang.com").is_limited() and self.get_ratelimit(
                "api.mojang.com").remaining() > 10:
            name = await self._mojang_get_name(uuid)
        else:
            try:
                name = await self._session_get_name(uuid)
            except InvalidUUID:  # Session sometimes says uuid doesn't exist while it does on mojang
                name = await self._mojang_get_name(uuid, )
        if return_uuid:
            return name, uuid
        return name

    """
    Hypixel APIs
    """

    @ratelimit_apis("api.hypixel.net", host_mapping=host_mapping)
    async def get_player_data(self, uuid: str, ) -> dict:
        async with self.session.get(f"https://api.hypixel.net/player?uuid={uuid}") as r:
            if r.status == 200:
                return await r.json()
            else:
                raise UnexpectedResponse("Error while getting UUID", r)

    @ratelimit_apis("api.hypixel.net", host_mapping=host_mapping)
    async def get_sb_player_data(self, uuid: str, ) -> dict:
        async with self.session.get(f"https://api.hypixel.net/skyblock/profiles?uuid={uuid}",
                                    ) as r:
            if r.status == 200:
                return await r.json()
            else:
                raise UnexpectedResponse("Error getting sb_player_data", r)

    @ratelimit_apis(get_sb_player_data, host_mapping=host_mapping)
    async def get_profile(
            self, uuid: str,
            profile_id: str = None,
            profile_name: str = None,
            select_profile_on: str = "last_save",
    ) -> SkyBlockPlayer:
        return SkyBlockPlayer(
            uuid,
            await self.get_sb_player_data(uuid),
            profile_id,
            profile_name,
            select_profile_on,
        )

    @ratelimit_apis("api.hypixel.net", host_mapping=host_mapping)
    async def get_guild_data(self, _id: str = None, uuid: str = None, name: str = None,
                             ) -> dict:
        if _id is not None:
            param = f"?id={_id}"
        elif uuid is not None:
            param = f"?player={uuid}"
        elif name is not None:
            param = f"?name={name}"
        else:
            raise Exception("No parameters given")

        async with self.session.get(f"https://api.hypixel.net/guild{param}") as r:
            if r.status == 200:
                rj = await r.json()
                if not rj["guild"] and uuid:
                    raise NotInAGuild("Player is not in a guild", uuid)
                elif not rj["guild"] and name:
                    raise GuildNotFound("Guild not found", name)
                return rj
            else:
                raise UnexpectedResponse("Error while getting Guild data", r)

    @ratelimit_apis(get_guild_data, host_mapping=host_mapping)
    async def get_guild_members(self, *args, **kwargs) -> list:
        guild_data = await self.get_guild_data(*args, **kwargs)
        return [i["uuid"] for i in guild_data["guild"]["members"]]

    @ratelimit_apis("api.robothanzo.dev", host_mapping=host_mapping)
    async def sbz_check_scammer(self, uuid: str = None) -> dict:
        # if uuid in self.ignore_scammer_check:
        #     return {
        #         "message": "Scammer not present in the database",
        #         "success": False
        #     }
        async with self.session.get(f"https://api.robothanzo.dev/scammer/{uuid}?key={SBZ_KEY}") as r:
            if r.status == 200:
                return await r.json()
            else:
                raise UnexpectedResponse("Error while checking scammers sbz", r)

    async def log_updates(self, identifier: str, changes: dict) -> None:
        return
