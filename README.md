# bunnytv

## To run
1. Install [ffmpeg](https://www.ffmpeg.org/)
2. `wget https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_640x360.m4v`
3. `uv run python main.py`
4. Go to http://localhost:8000/static/index.html


## Components
source: video file (big buck bunny)

producer
- reads in video file and convert video (at configurable rate)
- also adds metadata
- if consumer is slow, producer needs to drop frames, not accumulate them (to keep up with real time requirement)
- add a watermark

notes:
- original claude idea is to use ffmpeg to convert and put the output in a queue, to be read by a websockets server app
    - this would have lower latency and bidirectional communication
- asking claude about how to interface between ffmpeg and a web browser introduced the idea of HLS (dead simple interface - just files in a folder)
    - this may be simpler, but with higher latency and unidirectional (server->client)

consumer
- websocket endpoint which displays the video and metadata 

