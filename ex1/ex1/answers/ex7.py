import asyncio
import random
from mango import Agent, create_tcp_container, activate, sender_addr


# ---------------- REFLEXIVE AGENT ----------------
class ReflexiveAgent(Agent):
    def handle_message(self, content, meta):
        # Reflexive: reacts immediately, no thinking or planning
        print(f"[ReflexiveAgent] got '{content}' from {sender_addr(meta)}")
        if str(content).lower() == "hello":
            self.schedule_instant_message("Hi!", sender_addr(meta))



# ---------------- DELIBERATIVE AGENT ----------------
class DeliberativeAgent(Agent):
    async def think_and_reply(self, content, meta):
        # Simulate reasoning or planning
        print(f"[DeliberativeAgent] received '{content}', thinking...")
        await asyncio.sleep(1)  # simulate internal decision-making
        
        if "problem" in str(content).lower():

            reply = f"I received a problem sending solution. random={random.randint(1,100)}"

        else:
            reply = "proccessing message"
        self.schedule_instant_message(reply, sender_addr(meta))

    def handle_message(self, content, meta):
        # Delegate to reasoning function
        asyncio.create_task(self.think_and_reply(content, meta))


# ---------------- MAIN PROGRAM ----------------
async def main():
    container = create_tcp_container(addr=("127.0.0.1", 5555))

    reflex = container.register(ReflexiveAgent())
    deliber = container.register(DeliberativeAgent())

    async with activate(container):
        # Reflexive reaction
        reflex.schedule_instant_message("I have a problem", deliber.addr)

        # Deliberative reasoning
        deliber.schedule_instant_message("hello", reflex.addr)

        await asyncio.sleep(2.5)


if __name__ == "__main__":
    asyncio.run(main())
