import aiohttp


class UnexpectedResponse(Exception):  # update this
    def __init__(self, message: str, clientresponse: aiohttp.ClientResponse):
        super().__init__(message)
        self.message = message
        self.response = clientresponse
        self.status = clientresponse.status


class InternalRatelimitReached(Exception):
    def __init__(self, clientresponse: aiohttp.ClientResponse, r):
        self.message = f"429 - Internal Ratelimit Reached for {clientresponse.url} {r} {clientresponse.headers}"
        super().__init__(self.message)


class RatelimitReached(Exception):
    def __init__(self, message, reset_time: int):
        super().__init__(message)
        self.message = message
        self.reset_time = reset_time


class InvalidName(UnexpectedResponse):
    def __init__(self, message, clientresponse, name: str):
        super().__init__(message, clientresponse)
        self.name = name


class InvalidUUID(UnexpectedResponse):
    def __init__(self, message, clientresponse, uuid: str):
        super().__init__(message, clientresponse)
        self.uuid = uuid


class NotInAGuild(Exception):
    def __init__(self, message, uuid: str):
        super().__init__(message)
        self.uuid = uuid


class GuildNotFound(Exception):
    def __init__(self, message, name: str):
        super().__init__(message)
        self.name = name


class NoSbProfiles(Exception):
    def __init__(self, message, uuid: str):
        super().__init__(message)
        self.uuid = uuid


class InvalidURL(Exception):
    def __init__(self, message, url: str):
        super().__init__(message)
        self.url: str = url
