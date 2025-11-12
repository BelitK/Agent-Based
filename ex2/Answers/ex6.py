# exercise6_topology_compare.py
# pip install mango-agents
import asyncio
from typing import Any, List
from mango import Agent, run_with_tcp

N_WORKERS = 10
K_PER_SIDE = 2  # for small-world (each node connected to i±1, i±2)


class WorkerAgent(Agent):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._neighbor_addrs: List[Any] = []
        self.received_ids: set[str] = set()
        self.expected_neighbors = 0
        self.got_neighborhood = asyncio.Event()
        self.got_all_ids = asyncio.Event()
        self.msg_count = 0  # track messages sent

    def handle_message(self, content: Any, meta: dict[str, Any]):
        mtype = content.get("type")

        if mtype == "NEIGHBORHOOD":
            self._neighbor_addrs = list(content["neighbor_addrs"])
            self.expected_neighbors = len(self._neighbor_addrs)
            self.got_neighborhood.set()

            # send my ID to all neighbors
            for naddr in self._neighbor_addrs:
                self.schedule_instant_message({"type": "ID", "from": self.aid}, naddr)
                self.msg_count += 1

        elif mtype == "ID":
            self.received_ids.add(content["from"])
            if len(self.received_ids) >= self.expected_neighbors:
                self.got_all_ids.set()


class TopologyAgent(Agent):
    def __init__(self, workers: list[WorkerAgent]):
        super().__init__()
        self.workers = workers
        self.total_msgs = 0

    def send_topology(self, connections):
        """connections: list of lists of neighbor indices"""
        addrs = [w.addr for w in self.workers]
        for i, w in enumerate(self.workers):
            neighbors = [addrs[j] for j in connections[i]]
            self.schedule_instant_message(
                {"type": "NEIGHBORHOOD", "neighbor_addrs": neighbors}, w.addr
            )
            self.total_msgs += 1  # count neighborhood message

    def ring_topology(self):
        n = len(self.workers)
        return [[(i - 1) % n, (i + 1) % n] for i in range(n)]

    def small_world_topology(self, k=K_PER_SIDE):
        n = len(self.workers)
        conn = []
        for i in range(n):
            neighbors = set()
            for off in range(1, k + 1):
                neighbors.add((i - off) % n)
                neighbors.add((i + off) % n)
            conn.append(sorted(neighbors))
        return conn


async def run_topology(topology_name: str, topo_agent: TopologyAgent, connections):
    # reset counters
    for w in topo_agent.workers:
        w.received_ids.clear()
        w.got_neighborhood.clear()
        w.got_all_ids.clear()
        w.msg_count = 0
    topo_agent.total_msgs = 0

    # distribute topology
    topo_agent.send_topology(connections)

    # wait for completion
    await asyncio.gather(*(w.got_neighborhood.wait() for w in topo_agent.workers))
    await asyncio.gather(*(w.got_all_ids.wait() for w in topo_agent.workers))

    # compute totals
    total_id_msgs = sum(w.msg_count for w in topo_agent.workers)
    total_msgs = topo_agent.total_msgs + total_id_msgs

    print(f"\nTopology: {topology_name}")
    print(f"Neighborhood messages: {topo_agent.total_msgs}")
    print(f"ID messages: {total_id_msgs}")
    print(f"Total messages: {total_msgs}")


async def main():
    workers = [WorkerAgent(f"worker_{i}") for i in range(N_WORKERS)]
    topo_agent = TopologyAgent(workers)

    async with run_with_tcp(1, *workers, topo_agent):
        # run ring first
        await run_topology("Ring (k=1)", topo_agent, topo_agent.ring_topology())
        # then small-world
        await run_topology("Small-World (k=2)", topo_agent, topo_agent.small_world_topology(k=2))


if __name__ == "__main__":
    asyncio.run(main())
