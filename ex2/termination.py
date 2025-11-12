# ring_manual_topology.py
# pip install mango-agents

import asyncio
from typing import Any, Iterable, List

from mango import Agent, run_with_tcp


class WorkerAgent(Agent):
    """
    No mango topology used.
    Receives:
      - {"type": "NEIGHBORHOOD", "neighbor_addrs": [AgentAddress, ...]}
      - {"type": "ID", "from": aid}
    After NEIGHBORHOOD:
      - cache neighbor addresses
      - broadcast my ID to neighbors
    Tracks:
      - received_ids
      - got_neighborhood and got_all_ids events for sync
    """
    def __init__(self, name: str):
        super().__init__()
        self.name = name

        self._neighbor_addrs: List[Any] = []   # holds AgentAddress objects
        self.expected_neighbors: int = 0
        self.received_ids: set[str] = set()

        self.got_neighborhood = asyncio.Event()
        self.got_all_ids = asyncio.Event()

    def handle_message(self, content: Any, meta: dict[str, Any]):
        mtype = content.get("type")

        if mtype == "NEIGHBORHOOD":
            # Topology agent gives us actual AgentAddress objects to contact
            neighbor_addrs: Iterable[Any] = content["neighbor_addrs"]
            self._neighbor_addrs = list(neighbor_addrs)
            self.expected_neighbors = len(self._neighbor_addrs)

            # Signal that we know our neighborhood
            self.got_neighborhood.set()

            # Broadcast my ID to all neighbors
            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)

        elif mtype == "ID":
            # Store who pinged us
            self.received_ids.add(content["from"])
            if self.expected_neighbors and len(self.received_ids) >= self.expected_neighbors:
                self.got_all_ids.set()


class TopologyAgent(Agent):
    """
    Builds a ring manually using workers' live addresses.
    No create_topology, no custom_topology, no neighbors().
    """
    def __init__(self, workers: list[WorkerAgent]):
        super().__init__()
        self.workers = workers

    def on_ready(self):
        # Collect the concrete addresses from each worker
        addrs = [w.addr for w in self.workers]
        n = len(addrs)

        # Ring: i connected to (i-1) and (i+1)
        for i, w in enumerate(self.workers):
            left_idx = (i - 1) % n
            right_idx = (i + 1) % n
            neighbor_addrs = [addrs[left_idx], addrs[right_idx]]

            # Tell worker its neighborhood as real addresses it can message directly
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_addrs": neighbor_addrs},
                w.addr,
            )


async def main():
    # 10 workers
    workers = [WorkerAgent(f"worker_{i}") for i in range(10)]
    topo = TopologyAgent(workers)

    # Run everyone in a single TCP container
    async with run_with_tcp(1, *workers, topo):
        # Wait until all workers received their neighborhood
        await asyncio.gather(*(w.got_neighborhood.wait() for w in workers))

        # Then wait until all workers have received all neighbor IDs
        await asyncio.gather(*(w.got_all_ids.wait() for w in workers))

        # Print the results
        print("Received IDs per agent:")
        for w in workers:
            print(f"{w.aid}: {sorted(w.received_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
