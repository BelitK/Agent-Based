# compare_topologies.py
# pip install mango-agents

import asyncio
from typing import Any, Iterable
from mango import Agent, run_with_tcp


class MsgCounter:
    neighborhood_msgs: int = 0
    id_msgs: int = 0

    def total(self) -> int:
        return self.neighborhood_msgs + self.id_msgs


class WorkerAgent(Agent):
    def __init__(self, name: str, counter: MsgCounter):
        super().__init__()
        self.name = name
        self._neighbor_addrs = []
        self.received_ids: set[str] = set()
        self._counter = counter

    def handle_message(self, content: Any, meta: dict[str, Any]):
        mtype = content.get("type")
        if mtype == "NEIGHBORHOOD":
            self._neighbor_addrs = list(content["neighbor_addrs"])
            # Broadcast my ID to neighbors
            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)
                self._counter.id_msgs += 1
        elif mtype == "ID":
            self.received_ids.add(content["from"])


class TopologyAgent(Agent):
    """
    Builds a k-regular ring lattice (p=0). k even. k=2 gives a simple ring.
    """
    def __init__(self, workers: list[WorkerAgent], k: int, counter: MsgCounter):
        super().__init__()
        assert k % 2 == 0 and k >= 2, "k must be an even integer >= 2"
        self.workers = workers
        self.k = k
        self._counter = counter

    def on_ready(self):
        n = len(self.workers)
        addrs = [w.addr for w in self.workers]
        half = self.k // 2
        for i, w in enumerate(self.workers):
            neighbors = []
            for d in range(1, half + 1):
                neighbors.append(addrs[(i - d) % n])
                neighbors.append(addrs[(i + d) % n])
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_addrs": neighbors},
                w.addr,
            )
            self._counter.neighborhood_msgs += 1


async def run_once(n_agents: int, k: int) -> MsgCounter:
    counter = MsgCounter()
    workers = [WorkerAgent(f"worker_{i}", counter) for i in range(n_agents)]
    topo_agent = TopologyAgent(workers, k=k, counter=counter)
    async with run_with_tcp(1, *workers, topo_agent):
        await asyncio.sleep(0.2)
    return counter


async def main():
    n = 10

    # A) k=2 ring
    c_ring = await run_once(n_agents=n, k=2)

    # B) k=4 ring-lattice (Small World)
    c_k4 = await run_once(n_agents=n, k=4)

    # Report
    def report(name: str, c: MsgCounter, k: int):
        print(f"\n{name}")
        print(f"  Neighborhood messages: {c.neighborhood_msgs}")
        print(f"  ID messages:          {c.id_msgs}")
        print(f"  Total:                {c.total()}")
        print(f"  Formula check: n + n*k = {n} + {n}*{k} = {n + n*k}")

    report("Topology A: ring (k=2)", c_ring, 2)
    report("Topology B: ring-lattice (k=4)", c_k4, 4)

if __name__ == "__main__":
    asyncio.run(main())
