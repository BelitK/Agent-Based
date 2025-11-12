# ring_manual_topology.py
# pip install mango-agents

import asyncio
from typing import Any, Iterable

from mango import Agent, run_with_tcp


class WorkerAgent(Agent):
    """
    After receiving its neighborhood, it broadcasts its own ID to those neighbors.
    It stores any received IDs in `received_ids`.
    """
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._neighbor_addrs = []
        self.received_ids: set[str] = set()

    def handle_message(self, content: Any, meta: dict[str, Any]):
        mtype = content.get("type")
        if mtype == "NEIGHBORHOOD":
            # TopologyAgent sends actual neighbor addresses, so we can use them directly
            neighbor_addrs: Iterable = content["neighbor_addrs"]
            self._neighbor_addrs = list(neighbor_addrs)

            # Broadcast my ID to neighbors
            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)

        elif mtype == "ID":
            self.received_ids.add(content["from"])


class TopologyAgent(Agent):
    """
    On startup, compute a ring over the workers and send each its neighbors.
    No NetworkX, topology is defined manually here.
    """
    def __init__(self, workers: list[WorkerAgent]):
        super().__init__()
        self.workers = workers

    def on_ready(self):
        n = len(self.workers)
        # Build a ring: each i has neighbors (i-1) mod n and (i+1) mod n
        addrs = [w.addr for w in self.workers]
        for i, w in enumerate(self.workers):
            left = addrs[(i - 1) % n]
            right = addrs[(i + 1) % n]
            neighbor_addrs = [left, right]
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_addrs": neighbor_addrs},
                w.addr,
            )


async def main():
    # Create 10 workers
    workers: list[WorkerAgent] = [WorkerAgent(f"worker_{i}") for i in range(10)]

    # Create the topology announcer
    topo_agent = TopologyAgent(workers)

    # Run the system
    async with run_with_tcp(1, *workers, topo_agent):
        # Give time for neighborhood setup and broadcasts
        await asyncio.sleep(0.2)

    # Show what each worker received
    print("Received IDs per agent:")
    for w in workers:
        print(f"{w.aid}: {sorted(w.received_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
