import asyncio
from pipeflow.integrations.rabbitmq import (
    RabbitMQConfig, 
    RabbitMQSourcePipe, 
    RabbitMQSinkPipe, 
    RabbitMQMessage
)

async def send_and_receive_message(sink, source):
    try:
        message = RabbitMQMessage(
            value="Hello, RabbitMQ!",
            body="Hello, RabbitMQ!",
        )
        await sink.process(message)
        print(f"Sent message: {message.body}")

        received_message: RabbitMQMessage = await source.process()
        if received_message:
            print(f"Received message: {received_message.body}")
        else:
            print("No message received")
    except Exception as e:
        print(f"Error during send/receive: {e}")
    finally:
        await sink.stop()
        await source.stop()

async def main():
    config = RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        vhost="/",
        queue="test-queue",
        exchange=""
    )

    sink = RabbitMQSinkPipe(config)
    source = RabbitMQSourcePipe(config)

    await sink.start()
    await source.start()

    await send_and_receive_message(sink, source)


if __name__ == "__main__":
    asyncio.run(main())
