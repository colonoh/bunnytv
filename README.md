# bunnytv

``` shell
uv run python main.py
```

http://localhost:8000/static/index.html



## Components
source: video file (big buck bunny)

producer
- reads in video file and convert video (at configurable rate)
- also adds metadata
- if consumer is slow, producer needs to drop frames, not accumulate them (to keep up with real time requirement)
- add a watermark

consumer
- websocket endpoint which displays the video and metadata 

