import asyncio
import logging

from utils.database2 import Database2
from utils.httpr import Httpr
from utils.tasks import Tasks


class Client:
    def __init__(self):
        self.loop: asyncio.BaseEventLoop = None
        self.db: Database2 = None
        self.httpr: Httpr = None
        self.tasks: Tasks = None
        self.logger = logging.getLogger("backend")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())

    async def run(self):
        if not self.loop:
            self.loop = asyncio.get_event_loop()
            self.loop.set_debug(True)
        if not self.db:
            self.db = Database2(self)
        if not self.httpr:
            self.httpr = await Httpr(self).open()
        if not self.tasks:
            self.tasks = await Tasks(self).open()

        while True:
            await asyncio.sleep(10000)


client = Client()
asyncio.run(client.run())
