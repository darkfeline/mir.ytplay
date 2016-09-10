import asyncio
from concurrent.futures import CancelledError
import logging
import os
import signal
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, cancel_all_tasks)
    future = asyncio.ensure_future(play_urls(sys.stdin))
    try:
        loop.run_until_complete(future)
        logger.info('Finished normally')
    except CancelledError:
        logger.debug('CancelledError caught')
    finally:
        loop.close()


def cancel_all_tasks():
    tasks = asyncio.Task.all_tasks()
    logger.debug('%d tasks', len(tasks))
    for task in tasks:
        logger.debug('Canceled')
        task.cancel()


async def play_urls(file):
    buffered_songs = Channel()
    player_future = asyncio.ensure_future(play_songs(buffered_songs))
    async with buffered_songs:
        for video_url in file:
            video_url = video_url.rstrip()
            print(video_url)
            song = await BufferedSong.start_buffering(video_url)
            await buffered_songs.put(song)
    await player_future


async def play_songs(buffered_songs):
    while True:
        song = await buffered_songs.get()
        if song is Channel.DONE:
            break
        await song.play()


class BufferedSong:

    def __init__(self, url, buffer_pipe):
        self.url = url
        self.buffer_pipe = buffer_pipe

    @classmethod
    async def start_buffering(cls, url):
        reader, writer = os.pipe()
        logger.debug('Created pipe %d, %d for %s', reader, writer, url)
        proc = await youtube_dl(url, writer)
        future = asyncio.ensure_future(proc.wait())
        future.add_done_callback(lambda future: os.close(writer))
        logger.info('Buffering %s %s', url, proc)
        return cls(url, reader)

    async def play(self):
        proc = await start_player(self.buffer_pipe)
        logger.info('Player started %s %s', self, proc)
        future = asyncio.ensure_future(proc.wait())
        future.add_done_callback(lambda future: os.close(self.buffer_pipe))
        await future
        logger.info('Player exited %s %s', self, proc)

    def __repr__(self):
        return 'Song({!r})'.format(self.url)


async def youtube_dl(video_url, pipe):
    """Returns a Process."""
    return await asyncio.create_subprocess_exec(
        'youtube-dl', '-q', '-o', '-', video_url,
        stdout=pipe,
    )


async def start_player(pipe):
    """Returns a Process."""
    return await asyncio.create_subprocess_exec(
        'mpv', '--really-quiet', '--no-video', '-',
        stdin=pipe,
    )


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
