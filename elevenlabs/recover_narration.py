"""Retrieve a previously generated episode narration without synthesizing speech."""
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from bestiary import API, MODEL, VOICE, api

episode = sys.argv[1]
if not re.fullmatch(r"EP[0-9]+", episode):
    raise SystemExit("Expected an episode ID.")
spec=json.loads((Path("episodes")/episode/"episode.json").read_text())
script=" ".join(" ".join(line.split()) for line in spec["captions"])
voice=os.environ.get("ELEVENLABS_VOICE_ID") or VOICE
filters={"page_size": 10, "source": "TTS", "voice_id": voice, "model_id": MODEL,
         "date_after_unix": int(time.time())-86400, "search": script[:65]}
try:
    data,_=api("/history?"+urlencode(filters))
except ValueError as exc:
    raise SystemExit(f"History lookup failed: {exc}") from None
record=next((item for item in data["history"] if item.get("text")==script
             and item.get("voice_id")==voice and item.get("model_id")==MODEL),None)
if not record:
    raise SystemExit("No matching recent narration in ElevenLabs History.")
identifier=quote(record["history_item_id"],safe="")
request=Request(API+f"/history/{identifier}/audio",
                headers={"xi-api-key":os.environ["ELEVENLABS_API_KEY"]})
try:
    with urlopen(request,timeout=45) as response:
        audio=response.read()
except HTTPError as exc:
    raise SystemExit(f"History audio download returned HTTP {exc.code}.") from None
target=Path("recovered")/episode
target.mkdir(parents=True,exist_ok=True)
(target/"voice.mp3").write_bytes(audio)
if isinstance(record.get("character_count_change_to"),int) and isinstance(
        record.get("character_count_change_from"),int):
    print("Original narration credits:",
          record["character_count_change_to"]-record["character_count_change_from"])
