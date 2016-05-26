import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import CancelledError
from functools import partial

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(play_urls(sys.stdin))
    loop.add_signal_handler(signal.SIGINT, cancel_futures_callback(future))
    try:
        loop.run_until_complete(future)
        logger.info('Finished normally')
    except CancelledError:
        pass
    finally:
        loop.close()


def cancel_futures_callback(*futures):
    return partial(cancel_futures, *futures)


def cancel_futures(*futures):
    for future in futures:
        future.cancel()


async def play_urls(file):
    buffered_songs = Channel()
    player_future = asyncio.ensure_future(play_songs(buffered_songs))
    async with buffered_songs:
        for video_url in file:
            video_url = video_url.rstrip()
            print(video_url)
            song = Song(video_url)
            await song.start_buffering()
            await buffered_songs.put(song)
    await player_future


async def play_songs(buffered_songs):
    while True:
        song = await buffered_songs.get()
        if song is Channel.DONE:
            break
        await song.play()


class Song:

    def __init__(self, url):
        self.url = url
        self.buffer = None

    async def start_buffering(self):
        reader, writer = os.pipe()
        proc = await self.youtube_dl(self.url, writer)
        logger.info('Buffering %s %s', self, proc)
        AsyncProcesses.wait_for_proc(proc, writer)
        self.buffer = reader

    @staticmethod
    async def youtube_dl(video_url, pipe):
        return await asyncio.create_subprocess_exec(
            'youtube-dl', '-q', '-o', '-', video_url,
            stdout=pipe,
        )

    async def play(self):
        proc = await self.start_player(self.buffer)
        logger.info('Playing %s %s', self, proc)
        await AsyncProcesses.wait_for_proc(proc, self.buffer)
        logger.info('Player exited %s', self)

    @staticmethod
    async def start_player(pipe):
        return await asyncio.create_subprocess_exec(
            'mpv', '--no-terminal', '--no-video', '-',
            stdin=pipe,
        )

    def __repr__(self):
        return 'Song({!r})'.format(self.url)


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


class AsyncProcesses:

    processes = set()

    @classmethod
    def wait_for_proc(cls, proc, *pipes):
        wait_coro = cls._wait_for_proc(proc, *pipes)
        wait_future = asyncio.ensure_future(wait_coro)
        cls.add_proc(wait_future)
        wait_future.add_done_callback(cls.remove_proc)
        return wait_future

    @classmethod
    def add_proc(cls, future):
        cls.processes.add(future)
        logger.debug('number of procs: %d', len(cls.processes))

    @classmethod
    def remove_proc(cls, future):
        cls.processes.discard(future)
        logger.debug('number of procs: %d', len(cls.processes))

    @staticmethod
    async def _wait_for_proc(proc, *pipes):
        logger.debug('Set up wait for %s', proc)
        await proc.wait()
        logger.debug('Cleaning up %s', proc)
        for pipe in pipes:
            os.close(pipe)

    @classmethod
    def cleanup(cls):
        cancel_futures(*list(cls.processes))
        cls.processes.clear()


if __name__ == '__main__':
    main()
