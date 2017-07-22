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
import sys

from mir import ytplay

__version__ = '0.2.0'

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level='DEBUG')
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    loop.run_until_complete(ytplay.play_urls(loop, sys.stdin))


if __name__ == '__main__':
    main()
