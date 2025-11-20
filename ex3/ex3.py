import mango
import asyncio
import random
from mango import Agent, create_tcp_container, activate, JSON

## simple state reducer example with 3 agents choosing colors

COLORS = ["red", "green", "blue"]

class ColorAgent (Agent):
    def __init__(self):
        super().__init__()
        self.color = random.choice(COLORS)
        print(f"Agent {self.addr} initialized with color {self.color}")

    def on_ready(self):
        print("Chosen color:", self.color)

    def handle_message(self, content, meta):
        print("Chosen color:", content)

class VoteCounter ():
    def __init__(self):
        self.agents = []
        print("VoteCounter initialized")

    def register_agent(self, agent):
        self.agents.append(agent)
    
    def check_conflict(self):
        colors = [agent.color for agent in self.agents]
        for color in COLORS:
            if colors.count(color) > 1:
                return True
        return False
    
    def conflict_resolver(self):
        """Just a simple conflict resolver that changes colors randomly with respect to existing colors."""
 
        self.agents[0].color = random.choice(COLORS)
        colors=COLORS.copy()
        colors.remove(self.agents[0].color)
        print(f"Setting one color for agent {self.agents[0].addr}, removing {self.agents[0].color} from options")
        for agent in [self.agents[2],self.agents[1]]:
            agent.color = random.choice(colors)
            colors.remove(agent.color)





async def main():   
    """ Randomized Voting example with 3 agents getting assigned random colors."""


    container = create_tcp_container(addr=("127.0.0.1", 5555))
    agents = [container.register(ColorAgent()) for _ in range(3)]
    
    # set colors for conflict
    for agent in agents:
        agent.color="red"
    vote_counter = VoteCounter()
    for agent in agents:
        vote_counter.register_agent(agent)
    
    async with mango.activate(container):
        conflict = True
        count =0
        while conflict:
            count+=1
            print(f"Voting round {count}...")
            await asyncio.sleep(0.1)
            conflict = vote_counter.check_conflict()
            if conflict:
                # Conflict resolver
                print("Conflict detected, re-voting...")
                vote_counter.conflict_resolver()
            for agent in agents:
                await agent.send_message(content=agent.color, receiver_addr=agent.addr)
        print("No conflicts! Final colors:")
        for agent in agents:
            print(f"Agent {agent.addr} chose color {agent.color}")

asyncio.run(main())
    