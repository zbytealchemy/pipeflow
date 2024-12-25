import asyncio
from pipeflow.integrations.rabbitmq import (
    RabbitMQConfig, 
    RabbitMQSourcePipe, 
    RabbitMQSinkPipe, 
    RabbitMQMessage
)

async def send_messages(sink, message, count):
    try:
        for i in range(count):
            rabbit_message = RabbitMQMessage(
                value=f"{message} - {i+1}",
                body=f"{message} - {i+1}",
            )
            await sink.process(rabbit_message)
            print(f"Sent message: {rabbit_message.body}")
        print(f"Sent {count} messages")
    except Exception as e:
        print(f"Error during send: {e}")

async def process_stream(source):
    try:
        async for message in source.process_stream():
            print(f"Received message: {message.body}")
            # Add your processing logic here
            await asyncio.sleep(0.1)  # Simulate some processing time
    except Exception as e:
        print(f"Error during stream processing: {e}")

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

    try:
        await sink.start()
        await source.start()

        send_task = asyncio.create_task(send_messages(sink, "Hello, RabbitMQ!", 100))
        
        process_task = asyncio.create_task(process_stream(source))

        await asyncio.gather(send_task, process_task)

    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        await sink.stop()
        await source.stop()


async def main_():
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

    try:
        await sink.start()
        await source.start()

        await send_messages(sink, "Hello, RabbitMQ!", 100)
        await process_stream(source)


    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        await sink.stop()
        await source.stop()


if __name__ == "__main__":
    asyncio.run(main_())