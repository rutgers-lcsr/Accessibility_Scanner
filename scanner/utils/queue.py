from asyncio import Queue


class ListQueue():
    
    def __init__(self):
        self.queue = Queue()
        self.items = []

    async def put(self, item):
        await self.queue.put(item)
        self.items.append(item)

    async def get(self):
        item = await self.queue.get()
        self.items.remove(item)
        return item

    def task_done(self):
        self.queue.task_done()

    def exists(self, item):
        return item in self.items
    def join(self):
        return self.queue.join()
    def qsize(self):
        return self.queue.qsize()