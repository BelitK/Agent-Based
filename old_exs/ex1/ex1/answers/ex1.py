import mango
import asyncio

async def part1():
    # Create TCP container and agent
    container = mango.create_tcp_container(('127.0.0.1', 5555))
    agent = mango.PrintingAgent()
    
    try:
        # Try to send message without registration/activation
        await container.send_message('Moin!', agent.addr)
    except AttributeError as e:
        print(f"Part 1 Error: {e}, because agent is not registered and doesn't have an address.")

async def part2():
    # Create container and agent with registration
    container = mango.create_tcp_container(('127.0.0.1', 5555))
    agent = mango.PrintingAgent()
    
    # Register agent
    container.register(agent)
    
    # Try to send message without activation
    await container.send_message('Moin!', agent.addr)
    print("Part 2: Message sent but container not activated (TCP server is down), so agent can't receive it.")

async def part3():
    # Create container and agent with registration and activation
    container = mango.create_tcp_container(('127.0.0.1', 5555))
    agent = mango.PrintingAgent()
    
    # Register agent
    container.register(agent)
    
    # Activate container and send message
    async with mango.activate(container):
        await container.send_message('Moin!', agent.addr)

async def main():
    print("\n--- Part 1: No Registration or Activation ---")
    await part1()
    
    print("\n--- Part 2: With Registration ---")
    await part2()
    
    print("\n--- Part 3: With Registration and Activation ---")
    await part3()

if __name__ == "__main__":
    asyncio.run(main())