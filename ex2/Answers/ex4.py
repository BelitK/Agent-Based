# ring_small_world_manual.py
# pip install mango-agents
import asyncio
from typing import Any, Iterable, List

from mango import Agent, run_with_tcp


K_PER_SIDE = 2   # neighbors on each side (k = 2 => degree 4)
N_WORKERS = 10   # number of agents
BETA = 0.0       # rewiring probability (0.0 => no random edges, pure lattice)


class WorkerAgent(Agent):
    """
    Receives:
      - {"type": "NEIGHBORHOOD", "neighbor_addrs": [AgentAddress, ...]}
      - {"type": "ID", "from": aid}
    After NEIGHBORHOOD:
      - cache neighbor addresses
      - broadcast my ID to neighbors
    Sync:
      - got_neighborhood, got_all_ids events
    """
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._neighbor_addrs: List[Any] = []
        self.expected_neighbors: int = 0
        self.received_ids: set[str] = set()
        self.got_neighborhood = asyncio.Event()
        self.got_all_ids = asyncio.Event()

    def handle_message(self, content: Any, meta: dict[str, Any]):
        mtype = content.get("type")
        if mtype == "NEIGHBORHOOD":
            neighbor_addrs: Iterable[Any] = content["neighbor_addrs"]
            self._neighbor_addrs = list(neighbor_addrs)
            self.expected_neighbors = len(self._neighbor_addrs)

            self.got_neighborhood.set()

            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)

        elif mtype == "ID":
            self.received_ids.add(content["from"])
            if self.expected_neighbors and len(self.received_ids) >= self.expected_neighbors:
                self.got_all_ids.set()


class TopologyAgent(Agent):
    """
    Builds a small-world ring-lattice by hand:
      for each i, neighbors are i±1, i±2, ..., i±K_PER_SIDE (mod N)
    Random factor BETA is 0.0 here, so no rewiring is applied.
    """
    def __init__(self, workers: list[WorkerAgent]):
        super().__init__()
        self.workers = workers

    def on_ready(self):
        addrs = [w.addr for w in self.workers]
        n = len(addrs)

        for i, w in enumerate(self.workers):
            neighbors_idx = set()
            for offset in range(1, K_PER_SIDE + 1):
                neighbors_idx.add((i - offset) % n)
                neighbors_idx.add((i + offset) % n)

            neighbor_addrs = [addrs[j] for j in sorted(neighbors_idx)]
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_addrs": neighbor_addrs},
                w.addr,
            )


async def main():
    workers = [WorkerAgent(f"worker_{i}") for i in range(N_WORKERS)]
    topo = TopologyAgent(workers)

    async with run_with_tcp(1, *workers, topo):
        await asyncio.gather(*(w.got_neighborhood.wait() for w in workers))
        await asyncio.gather(*(w.got_all_ids.wait() for w in workers))

        print("Received IDs per agent:")
        for w in workers:
            print(f"{w.aid}: {sorted(w.received_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
