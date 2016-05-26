import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(url_player())
    loop.close()


async def url_player():
    loop = asyncio.get_event_loop()
    input_stream = await AsyncTextStream.make(loop, sys.stdin)
    buffer_channel = Channel()
    play_channel = Channel()
    await asyncio.gather(
        read_urls(input_stream, buffer_channel),
        buffer_streams(buffer_channel, play_channel),
        play_streams(play_channel),
    )


async def read_urls(input_stream, buffer_channel):
    async with buffer_channel:
        async for video_url in input_stream:
            if not video_url:
                break
            print(video_url)
            song = Song(video_url)
            await buffer_channel.put(song)


async def buffer_streams(buffer_channel, play_channel):
    async with play_channel:
        while True:
            song = await buffer_channel.get()
            if song is Channel.DONE:
                break
            await song.buffer()
            await play_channel.put(song)


async def play_streams(play_channel):
    while True:
        song = await play_channel.get()
        if song is Channel.DONE:
            break
        await song.play()


class Song:

    def __init__(self, url):
        self.url = url
        self.buffer_proc = None
        self.buffer_out = None
        self.buffer_in = None
        self.player_proc = None

    async def buffer(self):
        self.buffer_out, self.buffer_in = os.pipe()
        logger.info('Buffering %s', self)
        self.buffer_proc = await self.youtube_dl(self.url, self.buffer_in)
        loop = asyncio.get_event_loop()
        loop.create_task(wait_for_proc(self.buffer_proc, self.buffer_in))

    @staticmethod
    async def youtube_dl(video_url, pipe):
        return await asyncio.create_subprocess_exec(
            'youtube-dl', '-q', '-o', '-', video_url,
            stdout=pipe,
        )

    async def play(self):
        logger.info('Playing %s', self)
        self.player_proc = await self.start_player(self.buffer_out)
        await self.player_proc.wait()
        os.close(self.buffer_out)
        logger.info('Player exited %s', self)

    @staticmethod
    async def start_player(pipe):
        return await asyncio.create_subprocess_exec(
            'mpv', '--no-terminal', '--no-video', '-',
            stdin=pipe,
        )

    def __repr__(self):
        return 'Song({!r})'.format(self.url)

    def __str__(self):
        return 'Song {!s} {}'.format(self.url, self.status)

    @property
    def status(self):
        if self.buffer_proc is None:
            return 'Queued'
        elif self.player_proc is None:
            return 'Buffering'
        elif self.player_proc.returncode < 0:
            return 'Playing'
        else:
            return 'Finished'


async def wait_for_proc(proc, *pipes):
    await proc.wait()
    for pipe in pipes:
        os.close(pipe)


class AsyncStream:

    """Wrap a regular file object for async access."""

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

    """Implement Golang-like channel closing on a queue."""

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
