import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(url_player(loop))
    loop.close()


async def url_player(loop):
    input_stream = await AsyncTextStream.make(loop, sys.stdin)
    url_channel = Channel()
    buffer_channel = Channel()
    tasks = []
    tasks.append(read_urls(input_stream, url_channel))
    tasks.append(buffer_streams(url_channel, buffer_channel))
    tasks.append(play_streams(buffer_channel))
    await asyncio.gather(*tasks)


async def read_urls(input_stream, url_channel):
    async with url_channel:
        async for video_url in input_stream:
            print(video_url)
            await url_channel.put(video_url)


async def buffer_streams(url_channel, buffer_channel):
    async with buffer_channel:
        while True:
            video_url = await url_channel.get()
            if video_url is Channel.DONE:
                break
            reader, writer = os.pipe()
            proc = await buffer_one_stream(video_url, writer)
            await buffer_channel.put(reader)


def buffer_one_stream(video_url, buffer):
    logger.info('Buffering %s', video_url)
    return asyncio.create_subprocess_exec(
        'youtube-dl', '-q', '-o', '-', video_url,
        stdout=buffer,
    )


async def play_streams(buffer_channel):
    while True:
        buffer = await buffer_channel.get()
        if buffer is Channel.DONE:
            break
        proc = await play_one_stream(buffer)
        await proc.wait()


def play_one_stream(buffer):
    logger.info('Playing %s', buffer)
    return asyncio.create_subprocess_exec(
        'mpv', '--no-terminal', '--no-video', '-',
        stdin=buffer,
    )


class AsyncStream:

    @classmethod
    async def make(cls, loop, pipe):
        reader = asyncio.StreamReader(loop=loop)
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: reader_protocol, pipe)
        return cls(reader)

    def __init__(self, reader):
        self.reader = reader

    async def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.readline()

    async def readline(self):
        return await self.reader.readline()


class AsyncTextStream(AsyncStream):

    async def readline(self):
        line = await super().readline()
        line = line.decode().rstrip()
        return line


class Channel(asyncio.Queue):

    DONE = object()

    async def close(self):
        return await self.put(self.DONE)

    async def get(self):
        item = await super().get()
        if item is self.DONE:
            await self.close()
        return item

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


if __name__ == '__main__':
    main()
