# ring_per_node.py
# pip install mango-agents networkx

import asyncio
import networkx as nx
from typing import Any, Iterable

from mango import Agent, run_with_tcp, custom_topology, per_node


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
            neighbor_aids: Iterable[str] = content["neighbor_aids"]
            # Map AIDs to AgentAddress via the topology-populated neighbors()
            by_aid = {addr.aid: addr for addr in self.neighbors()}
            self._neighbor_addrs = [by_aid[aid] for aid in neighbor_aids if aid in by_aid]
            # Broadcast my ID to neighbors
            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)

        elif mtype == "ID":
            self.received_ids.add(content["from"])


class TopologyAgent(Agent):
    """
    On startup, announce each worker's neighborhood based on the ring topology.
    """
    def __init__(self, workers: list[WorkerAgent]):
        super().__init__()
        self.workers = workers

    def on_ready(self):
        # neighbors() is already set by the topology API
        for w in self.workers:
            neighbor_aids = [addr.aid for addr in w.neighbors()]
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_aids": neighbor_aids},
                w.addr,
            )


async def main():
    # Make a 10-node ring graph
    G = nx.cycle_graph(10)

    # Turn it into a mango topology without create_topology()
    topology = custom_topology(G)  # build from a networkx graph
    workers: list[WorkerAgent] = []

    # Add one WorkerAgent per node
    for i, node in enumerate(per_node(topology)):
        w = WorkerAgent(f"worker_{i}")
        node.add(w)
        workers.append(w)

    # Add the topology announcer
    topo_agent = TopologyAgent(workers)

    # Run the system
    async with run_with_tcp(1, *workers, topo_agent):
        await asyncio.sleep(0.2)

    # Show what each worker received
    print("Received IDs per agent:")
    for w in workers:
        print(f"{w.aid}: {sorted(w.received_ids)}")


if __name__ == "__main__":
    asyncio.run(main())
