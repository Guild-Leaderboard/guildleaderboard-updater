import asyncio
import logging

from dotenv import load_dotenv

from utils.database import Database
from utils.httpr import Httpr
from utils.tasks import Tasks

load_dotenv(".env")


class Client:
    def __init__(self):
        self.loop = None
        self.db = None
        self.httpr = None
        self.tasks = None
        self.logger = logging.getLogger("backend")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())

    async def run(self):
        if not self.loop:
            self.loop = asyncio.get_event_loop()
            self.loop.set_debug(True)
        if not self.db:
            self.db = await Database(self).open()
        if not self.httpr:
            self.httpr = await Httpr(self).open()
        if not self.tasks:
            self.tasks = await Tasks(self).open()

        while True:
            await asyncio.sleep(10000)


client = Client()

asyncio.run(client.run())
