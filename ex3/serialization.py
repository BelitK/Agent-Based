import asyncio
import mango

# codecs doc: https://mango-agents.readthedocs.io/en/latest/codecs.html

@mango.json_serializable
class Data:
    def __init__(self):
        self.a = "ABC"
        self.b = {"A": "B"}
        
    def __str__(self):
        return f"Data({self.a}, {self.b})"

async def main():
    codec = mango.JSON()
    codec.add_serializer(*Data.__serializer__())

    # container1 = mango.create_tcp_container("127.0.0.1:9995")
    # container2 = mango.create_tcp_container("127.0.0.1:9996")
    container1 = mango.create_tcp_container("127.0.0.1:9995", codec=codec)
    container2 = mango.create_tcp_container("127.0.0.1:9996", codec=codec)

    agent1 = container1.register(mango.PrintingAgent())
    agent2 = container2.register(mango.PrintingAgent())

    async with mango.activate(container1, container2):
        await agent1.send_message("Hi", agent2.addr)
        await agent1.send_message({"ABC": 2}, agent2.addr)
        await agent1.send_message(Data(), agent2.addr)

        # lazy sleep
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())