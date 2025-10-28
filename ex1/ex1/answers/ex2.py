# Ping-Pong agents with neighour example
import mango
import time
import asyncio
from Test_Agent import PVAgent

container = mango.create_tcp_container(('127.0.0.1', 5555))
print_agent = mango.PrintingAgent()
Aagent = PVAgent()
Bagent = PVAgent(print_agent)

# Register agent
container.register(Aagent)
container.register(print_agent)
container.register(Bagent) # neighbor is the printing agent

async def agent_test():
    async with mango.activate(container):
        # Kick off the ping-pong: A -> B, include sender in meta
        Aagent.schedule_instant_message("Ping", Bagent.addr)

        # wait until either agent reaches 10 messages
        while max(Aagent.get_message_count(), Bagent.get_message_count()) < 10:
            await asyncio.sleep(0.1)

        # allow final processing and print results
        await asyncio.sleep(0.1)
        print(f"Final counts: Aagent={Aagent.get_message_count()}, Bagent={Bagent.get_message_count()}")



async def main():
    await agent_test()

if __name__ == "__main__":
    asyncio.run(main())
