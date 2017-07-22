# Copyright (C) 2017 Allen Li
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import logging
import os

__version__ = '0.2.0'

logger = logging.getLogger(__name__)


async def play_urls(loop, file):
    reader = await _async_reader(loop, file)
    queue = asyncio.Queue(loop=loop)
    player_task = loop.create_task(_play_songs(loop, queue))
    async for line in reader:
        video_url = line.decode().rstrip()
        print(video_url)
        reader = await _download_song(loop, video_url)
        await queue.put(reader)
    await queue.put(None)
    await player_task


async def _download_song(loop, url):
    reader, writer = os.pipe()
    proc = await _start_download(loop, url, writer)
    future = loop.create_task(proc.wait())
    future.add_done_callback(lambda future: os.close(writer))
    return reader


async def _play_songs(loop, queue):
    while True:
        reader = await queue.get()
        if reader is None:
            break
        proc = await _start_player(loop, reader)
        await proc.wait()
        os.close(reader)


async def _async_reader(loop, file):
    reader = asyncio.StreamReader()
    reader_protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: reader_protocol, file)
    return reader


async def _start_download(loop, video_url, pipe):
    return await asyncio.create_subprocess_exec(
        'youtube-dl', '-q', '-o', '-', video_url,
        stdout=pipe, loop=loop)


async def _start_player(loop, pipe):
    return await asyncio.create_subprocess_exec(
        'mpv', '--really-quiet', '--no-video', '-',
        stdin=pipe, loop=loop)
