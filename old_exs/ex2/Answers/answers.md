## Ex3:

Each agent stores its neighborhood in a list called self._neighbor_addrs

## Ex5:

They’re identical only when the topology is symmetric (every connection is mutual) and all messages are delivered.
If links are one-way or some messages fail, received_ids and neighborhood will differ.

## Ex6:

The small-world topology sends more messages than the simple ring:
≈30 messages for the ring vs ≈50 for the small-world (k=2) because each node contacts more neighbors.

## Ex7:

You’d need to make the topology fully connected, meaning every agent is a neighbor of every other agent.
In practice, the topology agent would send each agent a neighborhood list containing all other agents’ addresses, so when they broadcast their IDs, everyone receives them.

## Ex9

Coordinator strategy:
In this approach, each queen is a QueenAgent, and one CoordinatorAgent oversees them all. The coordinator manages communication and ensures that no two queens threaten each other.

How it works:

Each QueenAgent proposes a column to the coordinator.

The CoordinatorAgent checks for conflicts (same column or diagonal).

If conflicts exist, it tells specific queens to move.

The process repeats until all queens are safe.

Why it works:

- The coordinator prevents random or conflicting moves.

- Communication stays organized and efficient.

- The system reaches a stable, conflict-free solution faster.