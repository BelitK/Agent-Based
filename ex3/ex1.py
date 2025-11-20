from mango import Agent, create_tcp_container, activate, JSON
import asyncio

class MyClass:
    def __init__(self, x, y):
        self.x = x
        self._y = y

    @property
    def y(self):
        return self._y

    def __asdict__(self):
        return {"x": self.x, "y": self.y}

    @classmethod
    def __fromdict__(cls, attrs):
        return cls(**attrs)

    @classmethod
    def __serializer__(cls):
        return (cls, cls.__asdict__, cls.__fromdict__)

class SimpleReceivingAgent(Agent):
    def __init__(self):
        super().__init__()

    def handle_message(self, content, meta):
        if isinstance(content, MyClass):
            print(content.x)
            print(content.y)


async def main():
    codec = JSON()
    codec.add_serializer(*MyClass.__serializer__())

    # codecs can be passed directly to the container
    # if no codec is passed a new instance of JSON() is created
    
    sending_container = create_tcp_container(addr=("127.0.0.1", 5556), codec=codec)
    receiving_container = create_tcp_container(addr=("127.0.0.1", 5555), codec=codec)
    sending_agent = sending_container.register(SimpleReceivingAgent())
    receiving_agent = receiving_container.register(SimpleReceivingAgent())

    async with activate(sending_container, receiving_container):
        # agents can now directly pass content of type MyClass to each other
        my_object = MyClass("abc", 123)
        await sending_agent.send_message(
            content=my_object, receiver_addr=receiving_agent.addr
        )
        await asyncio.sleep(0.1)

asyncio.run(main())