import mango
import time
import asyncio

class TestAgent(mango.Agent):
    def __init__(self, neighbor=None):
        super().__init__()
        self.message_count = 0
        self.neighbor = neighbor
        print("Hello I am a Reflexive agent!")

    def handle_message(self, content, meta):
        # increment counter and show receipt then send response
  
        print(f"[{self.addr}] Received ({self.message_count}): {content}  meta={meta}")
        if self.message_count < 10:
            self.schedule_instant_message("Ping" if str(content).lower().startswith("pong") else "Pong", mango.sender_addr(meta))
            self.message_count += 1
        


    def get_message_count(self):
        return self.message_count

container = mango.create_tcp_container(('127.0.0.1', 5555))
agent1 = TestAgent()
agent2 = TestAgent()

# Register neighbor
agent1.neighbor = agent2
agent2.neighbor = agent1

# Register agent
container.register(agent1)
container.register(agent2)

async def agent_test():
    async with mango.activate(container):
        # Kick off the ping-pong: A -> B, include sender in meta, initial message from container to A
        # starter wont count towards the 10 messages
        agent1.schedule_instant_message("Ping", agent1.neighbor.addr)


        # wait until either agent reaches 10 messages
        while max(agent1.get_message_count(), agent2.get_message_count()) < 10:
            await asyncio.sleep(0.1)

        # allow final processing and print results
        await asyncio.sleep(0.1)
        print(f"Final counts: agent1={agent1.get_message_count()}, agent2={agent2.get_message_count()}")



async def main():
    await agent_test()

if __name__ == "__main__":
    asyncio.run(main())
