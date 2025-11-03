### Ex3 

Reflexive agent, because the agent just sends back a message as a result of getting a message without any logical proccessing, reasoning or planning. Static set of instructions.

--------------------------
### Ex5 

The separation makes the system easier to manage. Agents handle behavior and decisions, while Containers handle running, connecting, and messaging between agents. This keeps logic and communication separate and makes the system more modular and scalable.

---

### Ex6 

The agent lifecycle in mango has several steps:

- Create: The agent object is made in code but not yet active.

- Register: The agent is added to a container so it can be managed and found.

- Activate: The agent starts running and can send or receive messages.

- Run: The agent performs its main tasks and reacts to messages.

- Shutdown: The agent stops and is removed from the container.

- Actions:

  - During activate/run, an agent can send, receive, or schedule messages.

  - In other phases, it mostly just initializes or cleans up.

---
### Ex8 = 

For one house, agents are not really needed. A simple control system can handle using and storing its own solar energy.

For many houses selling energy, agents are a good idea. Each house can act on its own, talk to others, and make better decisions together.

In short: one house -> too simple for agents; many houses → agents fit well.
