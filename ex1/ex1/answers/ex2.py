# Ping-Pong agents with neighour example
import mango
import time
import asyncio

class PVAgent(mango.Agent):
    def __init__(self, neighbor=None):
        super().__init__()
        self.message_count = 0
        self.neighbor = neighbor
        print("Hello I am a Reflexive agent!")

    def handle_message(self, content, meta):
        # increment counter and show receipt
  
        print(f"[{self.addr}] Received ({self.message_count}): {content}  meta={meta}")
        print(f"message count is {self.message_count}")
        if self.message_count < 10:
            self.message_count += 1
            self.schedule_instant_message("Ping" if str(content).lower().startswith("pong") else "Pong", mango.sender_addr(meta))
        


    def get_message_count(self):
        return self.message_count

container = mango.create_tcp_container(('127.0.0.1', 5555))
Aagent = PVAgent()
Bagent = PVAgent()

# Register neighbor
Aagent.neighbor = Bagent
Bagent.neighbor = Aagent

# Register agent
container.register(Aagent)
container.register(Bagent)

async def agent_test():
    async with mango.activate(container):
        # Kick off the ping-pong: A -> B, include sender in meta, initial message from container to A
        # starter wont count towards the 10 messages
        Aagent.schedule_instant_message("Ping", Aagent.neighbor.addr)


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
