import asyncio
from mango import Agent, create_tcp_container, activate


class RepeatingAgent(Agent):
    def __init__(self):
        super().__init__()
        print(f"Creating a RepeatingAgent. At this point self.addr={self.addr}")

    def handle_message(self, content, meta):
        print(f"Received a message with the following content: {content}!")

    def on_register(self):
        print(f"The agent has been registered to a container: {self.addr}!")

    def on_ready(self):
        print("All containers have been activated!")

class HelloWorldAgent(Agent):
    async def greet(self, other_addr):
        await self.send_message("Hello world!", other_addr)

    def handle_message(self, content, meta):
        print(f"Received a message with the following content: {content}")


async def run_container_and_two_agents(first_addr, second_addr):
    first_container = create_tcp_container(addr=first_addr)
    second_container = create_tcp_container(addr=second_addr)

    first_agent = first_container.register(RepeatingAgent())
    second_agent = second_container.register(HelloWorldAgent())

    async with activate(first_container, second_container) as cl:
        await second_agent.greet(first_agent.addr)
        await asyncio.sleep(.1)

asyncio.run(run_container_and_two_agents(
    first_addr=('127.0.0.1', 5555), second_addr=('127.0.0.1', 5556))
)