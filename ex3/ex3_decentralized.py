import asyncio
import random
import networkx as nx

from mango import Agent, run_with_tcp, custom_topology, per_node

COLORS = ["red", "green", "blue", "yellow", "purple", "orange"]  # agent count will match this


class RoundManager:
    def __init__(self, agent_count: int):
        self.agent_count = agent_count
        self.round_event = asyncio.Event()
        self.round_done_event = asyncio.Event()
        self._finished_this_round = 0
        self._lock = asyncio.Lock()

    async def wait_round_start(self):
        """Agents call this at the start of every round."""
        await self.round_event.wait()

    async def agent_step_done(self):
        """Agents call this at the end of their round logic."""
        async with self._lock:
            self._finished_this_round += 1
            if self._finished_this_round == self.agent_count:
                # Last agent to finish this round
                self._finished_this_round = 0
                self.round_event.clear()
                self.round_done_event.set()

    async def wait_round_end(self):
        """Main loop waits for all agents to finish the round."""
        await self.round_done_event.wait()
        self.round_done_event.clear()


class ColorAgent(Agent):
    def __init__(self, idx: int, round_manager: RoundManager):
        super().__init__()
        self.idx = idx
        self.color = random.choice(COLORS)
        self.round_manager = round_manager
        self.neighbor_colors = {}  # sender_addr -> {"id": int, "color": str}
        self.stable_rounds = 0
        self.done = False

    def on_ready(self):
        print(f"[{self.idx}] ready with initial color {self.color}")
        asyncio.create_task(self.protocol_loop())

    async def protocol_loop(self):
        while not self.done:
            # 1 - wait for round to start
            await self.round_manager.wait_round_start()

            # 2 - broadcast my color to neighbors
            for neighbor in self.neighbors():
                await self.send_message(
                    {"id": self.idx, "color": self.color},
                    neighbor,
                )

            # 3 - check conflicts based on neighbor_colors
            conflicts = [
                info for info in self.neighbor_colors.values()
                if info["color"] == self.color
            ]

            if conflicts:
                conflict_ids = [info["id"] for info in conflicts]
                max_id = max(conflict_ids + [self.idx])

                if self.idx == max_id:
                    old = self.color
                    options = [c for c in COLORS if c != self.color]
                    self.color = random.choice(options)
                    print(
                        f"[{self.idx}] conflict with {conflict_ids}, "
                        f"changing {old} -> {self.color}"
                    )
                else:
                    print(
                        f"[{self.idx}] conflict but keeping {self.color}, "
                        f"smaller id than {max_id}"
                    )

                self.stable_rounds = 0
            else:
                self.stable_rounds += 1
                print(f"[{self.idx}] no conflict, stable_rounds={self.stable_rounds}")
                if self.stable_rounds >= 3:
                    self.done = True
                    print(f"[{self.idx}] finished with final color {self.color}")

            # 4 - tell round manager that I am done with this round
            await self.round_manager.agent_step_done()

            # 5 - clear for next round
            self.neighbor_colors = {}

    def handle_message(self, content, meta):
        sender_addr = meta.get("sender_addr") or meta.get("sender")
        if not sender_addr:
            return
        self.neighbor_colors[sender_addr] = {
            "id": content["id"],
            "color": content["color"],
        }
        # Optional debug print:
        # print(f"[{self.idx}] heard {content['color']} from id={content['id']}")


async def main():
    """a ring of agents that repeatedly exchange colors, resolve conflicts with neighbors, and stop once each agent stabilizes on a unique color. """
    agent_count = len(COLORS)

    # Ring topology of size = number of colors
    graph = nx.cycle_graph(agent_count)
    topology = custom_topology(graph)

    round_manager = RoundManager(agent_count)

    # Attach one agent per node
    idx = 0
    for node in per_node(topology):
        node.add(ColorAgent(idx, round_manager))
        idx += 1

    async with run_with_tcp(1, *topology.agents):
        print("Starting decentralized color negotiation...")

        while True:
            # Start one round
            round_manager.round_event.set()

            # Wait until all agents finish this round
            await round_manager.wait_round_end()

            # Check if everyone is done
            if all(agent.done for agent in topology.agents):
                break

        print("\nAll agents reached stable colors:")
        for agent in topology.agents:
            print(f"Agent {agent.idx} at {agent.addr} -> {agent.color}")


if __name__ == "__main__":
    asyncio.run(main())
