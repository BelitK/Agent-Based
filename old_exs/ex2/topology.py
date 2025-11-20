import asyncio
import mango

class AgentWithTopology(mango.Agent):

    def __init__(self):
        super().__init__()

        self.neighbors: list[mango.AgentAddress] = []

    def handle_message(self, content, meta):
        print(f"{self.aid}: {content} from {meta}")
    
    def on_ready(self):
        for neighbor in self.neighbors:
            self.schedule_instant_message("Hi", neighbor)


async def main():
    container = mango.create_tcp_container("127.0.0.1:9995")

    # register
    a = container.register(AgentWithTopology())
    a2 = container.register(AgentWithTopology())
    a3 = container.register(AgentWithTopology())
    
    # define topology
    a.neighbors = [a2.addr]
    a2.neighbors = [a3.addr]
    a3.neighbors = [a.addr]

    async with mango.activate(container):
        await asyncio.sleep(1)

    
if __name__ == "__main__":
    asyncio.run(main())