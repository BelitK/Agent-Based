## Ex3:

I implemented neighbors data as a list of 2, first one is the one to the left then right for 2 neighbors.

## Ex5:

They’re identical only when the topology is symmetric (every connection is mutual) and all messages are delivered.
If links are one-way or some messages fail, received_ids and neighborhood will differ.

## Ex6:

The small-world topology sends more messages than the simple ring:
≈30 messages for the ring vs ≈50 for the small-world (k=2) because each node contacts more neighbors.

## Ex7:

You’d need to make the topology fully connected, meaning every agent is a neighbor of every other agent.
In practice, the topology agent would send each agent a neighborhood list containing all other agents’ addresses, so when they broadcast their IDs, everyone receives them.