import asyncio
from mango import Agent, AgentAddress, create_tcp_container, activate

TOPO_ADDR = AgentAddress(protocol_addr=('127.0.0.1', 5555), aid='agent0')  # pasted

class WorkerAgent(Agent):
    def __init__(self, name, topology_addr):
        super().__init__()
        self.name = name
        self.topology_addr = topology_addr
        self.neighbors = []

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
    # Second TCP container, different port
    container = create_tcp_container(addr=("127.0.0.1", 5556))

    # 5 remote agents in this container
    workers = [
        container.register(WorkerAgent(name=f"remote-{i}", topology_addr=TOPO_ADDR))
        for i in range(5)
    ]

    async with activate(container):
        print("Script 2 running; agents will register with the topology in script 1.")
        await asyncio.Event().wait()  # run until Ctrl+C


if __name__ == "__main__":
    asyncio.run(main())
