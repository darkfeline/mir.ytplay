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
import tempfile
import os
from unittest import mock

from mir import ytplay


async def fake_start_download(loop, video_url, pipe):
    return await asyncio.create_subprocess_exec(
        'printf', '%s', video_url, stdout=pipe, loop=loop)


def make_fake_player(outfile):
    async def fake_start_player(loop, pipe):
        data = os.read(pipe, 50).decode()
        return await asyncio.create_subprocess_exec(
            'printf', '%s', data, stdout=outfile, loop=loop)
    return fake_start_player


def test_play_urls():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    player_output = tempfile.SpooledTemporaryFile()
    reader, writer = os.pipe()
    os.write(writer, b'https://www.youtube.com/watch?v=tSdpxQMp-Ok')
    os.close(writer)
    fake_start_player = make_fake_player(player_output)
    with mock.patch.object(ytplay, '_start_download', fake_start_download), \
         mock.patch.object(ytplay, '_start_player', fake_start_player):
        loop.run_until_complete(ytplay.play_urls(loop, os.fdopen(reader)))
        loop.close()
    player_output.seek(0)
    assert player_output.read() == b'https://www.youtube.com/watch?v=tSdpxQMp-Ok'
