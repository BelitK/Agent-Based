# smallworld_ring_lattice.py
# pip install mango-agents

import asyncio
from typing import Any, Iterable
from mango import Agent, run_with_tcp


class WorkerAgent(Agent):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._neighbor_addrs = []
        self.received_ids: set[str] = set()

    def handle_message(self, content: Any, meta: dict[str, Any]):
        if content.get("type") == "NEIGHBORHOOD":
            self._neighbor_addrs = list(content["neighbor_addrs"])
            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)
        elif content.get("type") == "ID":
            self.received_ids.add(content["from"])


class TopologyAgent(Agent):
    """
    Builds a k-regular ring lattice (With p=0).
    k must be even. For k=2, this is the plain ring.
    """
    def __init__(self, workers: list[WorkerAgent], k: int = 2):
        super().__init__()
        assert k % 2 == 0 and k >= 2, "k must be an even integer >= 2"
        self.workers = workers
        self.k = k

    def on_ready(self):
        n = len(self.workers)
        addrs = [w.addr for w in self.workers]
        half = self.k // 2  # neighbors on each side

        for i, w in enumerate(self.workers):
            # Collect 1..half neighbors on both sides (p=0, so no rewiring)
            neighbors = []
            for d in range(1, half + 1):
                neighbors.append(addrs[(i - d) % n])  # left d
                neighbors.append(addrs[(i + d) % n])  # right d
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_addrs": neighbors},
                w.addr,
            )


async def main():
    workers = [WorkerAgent(f"worker_{i}") for i in range(10)]

    # Set k=2 for plain ring; try k=4 for extra shortcuts to second neighbors.
    topo_agent = TopologyAgent(workers, k=2)

    async with run_with_tcp(1, *workers, topo_agent):
        await asyncio.sleep(0.2)

    print("Received IDs per agent:")
    for w in workers:
        print(f"{w.aid}: {sorted(w.received_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
