import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import CancelledError
from weakref import WeakKeyDictionary

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(play_urls(sys.stdin))
    loop.add_signal_handler(signal.SIGINT, cancel_futures_callback(future))
    loop.add_signal_handler(signal.SIGINT, AsyncProcesses.cleanup)
    try:
        loop.run_until_complete(future)
        logger.info('Finished normally')
    except CancelledError:
        pass
    finally:
        loop.close()


def cancel_futures_callback(*futures):
    def cancel_futures():
        for future in futures:
            future.cancel()
    return cancel_futures


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
        logger.debug('Created pipe %d, %d for %s', reader, writer, self)
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
            'mpv', '--really-quiet', '--no-video', '-',
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

    processes = WeakKeyDictionary()

    @classmethod
    def wait_for_proc(cls, proc, *pipes):
        logger.debug('Set up wait for %s', proc)
        wait_future = asyncio.ensure_future(proc.wait())
        wait_future.add_done_callback(cls._close_pipes_callback(*pipes))
        wait_future.add_done_callback(cls.remove_proc)
        cls.add_proc(wait_future, proc)
        return wait_future

    @classmethod
    def add_proc(cls, future, proc):
        cls.processes[future] = proc

    @classmethod
    def remove_proc(cls, future):
        proc = cls.processes.pop(future, None)
        if proc is not None:
            logger.debug('Removing %s', proc)

    @staticmethod
    def _close_pipes_callback(*pipes):
        def close_pipes(future):
            for pipe in pipes:
                logger.debug('Closing pipe %d', pipe)
                os.close(pipe)
        return close_pipes

    @classmethod
    def cleanup(cls):
        for future, proc in cls.processes.items():
            logger.debug('Cleaning up %s', proc)
            proc.terminate()
            future.cancel()
        cls.processes.clear()


if __name__ == '__main__':
    main()
