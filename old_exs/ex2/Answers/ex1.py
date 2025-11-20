import asyncio
import random
import math
import mango

class SampleAgent(mango.Agent):
    def __init__(self):
        super().__init__()
        self.event = asyncio.Event()
        self.neighbors_list: list[mango.AgentAddress]= []

    def on_ready(self):
        print(f"[{self.aid}] Agent is ready.")
        for neighbor in self.neighbors_list:
            self.schedule_instant_message("Hi", neighbor)

    def handle_message(self, content, meta):
        print(f"[{self.aid}] Received message: {content} from {mango.sender_addr(meta)}")
        self.event.set()

async def main():
    container = mango.create_tcp_container("127.0.0.1:9995")

    # Container registration
    a = container.register(SampleAgent())
    a2 = container.register(SampleAgent())
    a3 = container.register(SampleAgent())
    a4 = container.register(SampleAgent())
    a5= container.register(SampleAgent())
    a6 = container.register(SampleAgent())

    # Ring topology registrations (0–1–2–3–4–0)
    a.neighbors_list = [a2.addr, a6.addr]
    a2.neighbors_list = [a.addr, a3.addr]
    a3.neighbors_list = [a2.addr, a4.addr]
    a4.neighbors_list = [a3.addr, a5.addr]
    a5.neighbors_list = [a4.addr, a6.addr]
    a6.neighbors_list = [a5.addr, a.addr]

    async with mango.activate(container):

        # event
        await asyncio.gather(a.event.wait(), a2.event.wait())
        print("Terminated")

    
if __name__ == "__main__":
    asyncio.run(main())