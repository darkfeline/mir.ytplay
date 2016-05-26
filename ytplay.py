import asyncio
import logging
import os
import signal
import stat
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    future = loop.create_future(url_player())
    loop.add_signal_handler(signal.SIGINT, cancel_futures_callback(future))
    try:
        loop.run_until_complete(future)
    finally:
        loop.close()


def cancel_futures_callback(*futures):
    def cancel_futures():
        logger.info('Canceling futures')
        loop = asyncio.get_event_loop()
        for future in futures:
            future.cancel()
            loop.run_until_complete(future)
    return cancel_futures


_MODES = [
    ('FIFO', stat.S_ISFIFO),
    ('SOCK', stat.S_ISSOCK),
    ('CHR', stat.S_ISCHR),
    ('BLK', stat.S_ISBLK),
    ('REG', stat.S_ISREG),
    ('DOOR', stat.S_ISDOOR),
]


async def url_player():
    mode = os.stat(sys.stdin.fileno()).st_mode
    logger.debug(
        'stdin mode: %o %s', mode,
        ' '.join(label for label, check in _MODES if check(mode)),
    )
    input_stream = sys.stdin
    input_stream = await AsyncTextStream.make(input_stream)
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
            await song.download()
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
        self.buffer = None

    async def download(self):
        reader, writer = os.pipe()
        logger.info('Buffering %s', self)
        proc = await self.youtube_dl(self.url, writer)
        loop = asyncio.get_event_loop()
        loop.create_task(wait_for_proc(proc, writer))
        self.buffer = reader

    @staticmethod
    async def youtube_dl(video_url, pipe):
        return await asyncio.create_subprocess_exec(
            'youtube-dl', '-q', '-o', '-', video_url,
            stdout=pipe,
        )

    async def play(self):
        logger.info('Playing %s', self)
        proc = await self.start_player(self.buffer)
        await wait_for_proc(proc, self.buffer)
        logger.info('Player exited %s', self)

    @staticmethod
    async def start_player(pipe):
        return await asyncio.create_subprocess_exec(
            'mpv', '--no-terminal', '--no-video', '-',
            stdin=pipe,
        )

    def __repr__(self):
        return 'Song({!r})'.format(self.url)


async def wait_for_proc(proc, *pipes):
    await proc.wait()
    for pipe in pipes:
        os.close(pipe)


class AsyncStream:

    """Wrap a regular file object for async access."""

    @classmethod
    async def make(cls, pipe):
        reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        loop = asyncio.get_event_loop()
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
