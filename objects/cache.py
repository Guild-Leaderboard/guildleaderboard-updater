import asyncio
import logging
from functools import wraps
from typing import Union

from objects.errors import *
from objects.utils import Time
import os

DEFAULT_TIMEOUT = 999

if os.name == 'posix':
    HYPIXEL_KEY = "2764e7a2-6df6-48a7-bd87-fc8aeb480484" # production
else:
    HYPIXEL_KEY = "27b5e087-0f4c-49b5-b18f-9efcd4c33797"

"""
high level cache workflow:
https://cdn.discordapp.com/attachments/789953379027255316/963873058874081311/unknown.png
"""


def ratelimit_apis(*apis, host_mapping):
    def decorator(method):
        hosts = []
        for api in apis:
            if isinstance(api, str):
                hosts.append(api)
            else:
                hosts.extend(host_mapping[api.__qualname__])

        host_mapping[method.__qualname__] = hosts

        @wraps(method)
        async def wrapper(*args, **kwargs):
            return await method(*args, **kwargs)

        return wrapper

    return decorator


class Ratelimit:
    """
    Ratelimitresponse class for handling ratelimits.
    The class is dynamically updated, so you only need to get it once and can use it multiple times.
    That's also why the you have to run a function to get the wanted value.
    """

    def __init__(self, host: str, api_d: Union[dict, None]):
        self.api_d = api_d
        self.host = host

    def __repr__(self):
        return f"<Ratelimit: {self.host} remaining: {self.remaining()} wait_time: {self.wait_time()}>"

    def has_ratelimit(self):
        return self.api_d is not None

    def host(self):
        return self.host

    def remaining(self):
        return self.api_d.get("remaining")

    def reset_time(self):
        return self.api_d.get("reset_time")

    def wait_time(self):
        return self.reset_time() - Time().time

    def max(self):
        return self.api_d.get("max")

    def ratelimit_sync(self):
        return self.api_d.get("ratelimit_sync")

    def exclude(self):
        return self.api_d.get("exclude")

    def is_limited(self):
        return self.remaining() == 0


class RatelimitHandler:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger if logger else logging.getLogger(__name__)
        self.rate_limits = {  # everything is in requests per minute
            "api.mojang.com": {  # https://wiki.vg/Mojang_API
                "max": 60,  # max requests per minute
                "ratelimit_sync": False,
                "exclude": [],
            },
            "sessionserver.mojang.com": {  # https://wiki.vg/Mojang_API
                "max": 200,  # Liars they said there was none
                "ratelimit_sync": False,
                "exclude": [],
            },
            "api.hypixel.net": {  # https://api.hypixel.net/
                "max": 100 if os.name == 'posix' else 50,  # max requests per minute # supposed to be 100
                "headers": {"API-Key": HYPIXEL_KEY},
                "ratelimit_sync": False,
                "exclude": ["/skyblock/auctions", "/skyblock/auctions_ended"],
            },
            "api.robothanzo.dev": {  # https://api.robothanzo.dev/
                "max": 1000,  # max requests per minute
                "ratelimit_sync": False,
                "exclude": [],
            },
            "api.poke535.dev": {  # Imagine docs
                "max": 1000,  # max requests per minute
                # "headers": {
                #     "Authorization": "6ZCFljqGHEue4JPNp2gxEEM3triwoImC"
                # },
                "ratelimit_sync": False,
                "exclude": [],
            },
            "nwapi.guildleaderboard.com": {  # https://api.hypixel.net/
                "max": 1000,  # max requests per minute
                "headers": {"authorization": "TIMNOOT_IS_AWESOME"},
                "ratelimit_sync": False,
                "exclude": [],
            },
            "195.201.43.165": {  # https://api.hypixel.net/
                "max": 1000,  # max requests per minute
                "headers": {"authorization": "TIMNOOT_IS_AWESOME"},
                "ratelimit_sync": False,
                "exclude": [],
            },

        }
        for key, value in self.rate_limits.items():
            value["reset_time"], value["remaining"], value["in_queue"] = 0, value["max"], 0

    def get_ratelimit(self, host: str) -> Ratelimit:
        if host in self.rate_limits:
            api_d = self.rate_limits[host]

            if api_d["reset_time"] - Time().time <= 0:
                api_d["reset_time"] = Time().time + 60
                api_d["remaining"] = api_d["max"]
            return Ratelimit(host, api_d)
        return Ratelimit(host, None)

    async def before_request(self, params: aiohttp.tracing.TraceRequestStartParams,
                             max_ratelimit_wait: int = DEFAULT_TIMEOUT) -> aiohttp.tracing.TraceRequestStartParams:
        host = str(params.url.host)
        api_d = None
        if host in self.rate_limits:
            api_d = self.rate_limits[host]

            if any([params.url.path.startswith(i) for i in api_d["exclude"]]):
                return params
            api_d["in_queue"] += 1

            params.headers.update(api_d.get("headers", {}))

            while 1:
                if (api_d["reset_time"] - Time().time) + 2 <= 0:
                    api_d["remaining"], api_d["reset_time"] = api_d["max"] - 1, Time().time + 60
                    break

                if api_d["remaining"] <= 1:
                    extra_wait = int(api_d["in_queue"] / api_d["max"]) * 60

                    sleep_time = abs((api_d["reset_time"] - Time().time) + extra_wait)
                    if sleep_time >= max_ratelimit_wait:
                        api_d["in_queue"] -= 1
                        from objects.errors import RatelimitReached
                        raise RatelimitReached(
                            f"Ratelimit reached for {host}! Try again in {round(sleep_time, 1)} seconds. {api_d['in_queue']} requests in queue.",
                            reset_time=api_d["reset_time"],
                        )
                    self.logger.error(
                        f"Ratelimit reached for {host}! Sleeping for {round(sleep_time, 1)} seconds. {api_d['in_queue']} requests in queue."
                    )
                    await asyncio.sleep(sleep_time + 1.5)

                elif api_d["remaining"] > 1:
                    api_d["remaining"] -= 1
                    break
                print("waiting for ratelimit")

        if api_d:
            api_d["in_queue"] -= 1
        return params

    async def after_request(self, params: aiohttp.tracing.TraceRequestEndParams):
        host = str(params.url.host)
        if host in self.rate_limits:
            api_d, headers = self.rate_limits[host], params.response.headers
            if not api_d["ratelimit_sync"]:
                return
            try:
                seconds = float(headers.get("RateLimit-Reset") or headers.get("Retry-After"))
                remaining = int(headers.get("RateLimit-Remaining") or headers.get("X-RateLimit-Remaining"))
            except TypeError:
                return

            # if time.time() - request_time > seconds - 10:
            #     print(time.time() - request_time, seconds)
            #     return
            if seconds <= 5 or remaining <= 10:
                print(f"Not syncing {seconds}, {api_d['remaining']}, {remaining}")
                return

            try:
                if api_d.get("ratelimit_sync_remaining", True):
                    api_d["remaining"] = min(
                        remaining,
                        api_d["remaining"]
                    )
                seconds = float(headers.get("RateLimit-Reset") or headers.get("Retry-After"))
                api_d["reset_time"] = Time().time + seconds
                self.logger.info(f"Synced the rate-limits for {host} {api_d['remaining']} {seconds}")
            except TypeError:
                pass


class RateLimitSession(aiohttp.ClientSession):
    def __init__(self, logger: logging.Logger = None, *args, **kwargs):
        _trace_config = aiohttp.TraceConfig()
        _trace_config.on_request_start.append(self.on_request_start)
        _trace_config.on_request_end.append(self.on_request_end)

        kwargs_config = kwargs.get("trace_configs", [])
        kwargs_config.append(_trace_config)
        kwargs["trace_configs"] = kwargs_config

        super().__init__(*args, **kwargs)
        self.logger = logger if logger else logging.getLogger(__name__)
        self.ratelimit_handler = RatelimitHandler(self.logger)

    async def on_request_start(self, session, ctx, params: aiohttp.tracing.TraceRequestStartParams):
        params: aiohttp.tracing.TraceRequestStartParams = (
            await self.ratelimit_handler.before_request(
                params, ctx.trace_request_ctx.get("max_ratelimit_wait", DEFAULT_TIMEOUT)
                if ctx.trace_request_ctx else DEFAULT_TIMEOUT,
            )
        )
        self.logger.info(f"Making {params.method} request to {params.url}")

    async def on_request_end(self, session, ctx, params: aiohttp.tracing.TraceRequestEndParams):
        if params.response.status == 429:
            try:
                r = await params.response.json()
            except:
                try:
                    r = await params.response.text()
                except:
                    r = params.response
            from objects.errors import InternalRatelimitReached
            error = InternalRatelimitReached(params.response, r)
            self.logger.error(error.message)
            raise error
        await self.ratelimit_handler.after_request(params)
