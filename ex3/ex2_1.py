import asyncio
from mango import Agent, create_tcp_container, activate, sender_addr

class TopologyAgent(Agent):
    def __init__(self):
        super().__init__()
        self.known_agents = {}      # AgentAddress -> name
        self.expected_agents = 10   # 5 local + 5 remote
        self.topology_built = False

    def on_register(self):
        print(f"[Topology] registered at {self.addr!r}")
        print("Copy this line into script 2:")
        print(f"TOPO_ADDR = {self.addr!r}")

    def handle_message(self, content, meta):
        if not isinstance(content, dict):
            return

        msg_type = content.get("type")
        if msg_type == "register":
            sender = sender_addr(meta)  # gives an AgentAddress
            name = content.get("name", "<unnamed>")

            if sender not in self.known_agents:
                self.known_agents[sender] = name
                print(
                    f"[Topology] registered {name} at {sender!r}. "
                    f"Total agents: {len(self.known_agents)}"
                )

            # When all agents are registered, build neighborhoods once
            if (
                len(self.known_agents) == self.expected_agents
                and not self.topology_built
            ):
                self.topology_built = True
                asyncio.create_task(self.setup_neighborhoods())

    async def setup_neighborhoods(self):
        print("\n[Topology] All agents registered, creating neighborhoods...")

        # Split local / remote by name prefix
        locals_ = [
            (addr, name)
            for addr, name in self.known_agents.items()
            if name.startswith("local-")
        ]
        remotes_ = [
            (addr, name)
            for addr, name in self.known_agents.items()
            if name.startswith("remote-")
        ]

        # Sort so indices match name suffix (0..4)
        locals_.sort(key=lambda x: int(x[1].split("-")[1]))
        remotes_.sort(key=lambda x: int(x[1].split("-")[1]))

        neighborhoods = {}  # AgentAddress -> list[AgentAddress]

        # Local agents: ring + cross to remote with same index
        n_local = len(locals_)
        for i, (addr, name) in enumerate(locals_):
            left = locals_[(i - 1) % n_local][0]
            right = locals_[(i + 1) % n_local][0]
            cross = remotes_[i][0]
            neighborhoods[addr] = [left, right, cross]

        # Remote agents: fully connected inside + cross to matching local
        for i, (addr, name) in enumerate(remotes_):
            # all remote except self
            remote_neighbors = [a for a, nm in remotes_ if a != addr]
            cross = locals_[i][0]
            neighborhoods[addr] = remote_neighbors + [cross]

        # Print neighborhood lists and send to each agent
        print("\n[Topology] Neighborhoods:")
        for addr, neighbors in neighborhoods.items():
            name = self.known_agents[addr]
            neighbor_names = [self.known_agents[n] for n in neighbors]
            print(f"  {name} -> {neighbor_names}")

        # Send each agent its neighbors (serialized)
        for addr, neighbors in neighborhoods.items():
            serialized = [
                {
                    "protocol_addr": list(n.protocol_addr),  # ['127.0.0.1', 5555]
                    "aid": n.aid,
                }
                for n in neighbors
            ]
            await self.send_message(
                {
                    "type": "set_neighbors",
                    "neighbors": serialized,
                },
                addr,
            )


class WorkerAgent(Agent):
    def __init__(self, name, topology_addr):
        super().__init__()
        self.name = name
        self.topology_addr = topology_addr
        self.neighbors = []  # list[AgentAddress]

    def on_ready(self):
        print(f"[{self.name}] ready at {self.addr!r}")
        asyncio.create_task(self.register_with_topology())

    async def register_with_topology(self):
        await self.send_message(
            {"type": "register", "name": self.name},
            self.topology_addr,
        )

    def handle_message(self, content, meta):
        if not isinstance(content, dict):
            return
        if content.get("type") == "set_neighbors":
            raw = content.get("neighbors", [])
            from mango import AgentAddress
            self.neighbors = [
                AgentAddress(protocol_addr=tuple(n["protocol_addr"]), aid=n["aid"])
                for n in raw
            ]
            print(f"[{self.name}] got neighbors: {self.neighbors!r}")



async def main():
    container = create_tcp_container(addr=("127.0.0.1", 5555))

    # Topology agent first (so it usually gets aid='agent0' on this container)
    topo = container.register(TopologyAgent())

    # 5 local agents in the same container
    workers = [
        container.register(WorkerAgent(name=f"local-{i}", topology_addr=topo.addr))
        for i in range(5)
    ]

    async with activate(container):
        print("Script 1 running. Start script 2 in another shell.")
        await asyncio.Event().wait()  # run until Ctrl+C


if __name__ == "__main__":
    asyncio.run(main())
