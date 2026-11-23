# BESTIARY Cinematic V2 production requests

When the user asks to produce an episode from chat, dispatch the existing workflow exactly once using `python3 chat_produce.py --episode EP16 --wait 1200 --topic "Mudskipper"` with their episode and topic. Pass the topic as a quoted argument, never as executable content. Use EP15 as the topic for the bundled Velvet Worm demo. If the user only requests a storyboard, add `--mode plan`.

The first JSON line gives the run ID once GitHub accepts the request. Keep that ID. If the command times out while waiting, check the same run with `python3 chat_produce.py --status RUN_ID --wait 300`. After a network timeout during submission with no run ID, reconcile recent runs before any resubmission. For status requests, use the existing ID. When the workflow completes, send links to the individual MP4s, covers and upload text when present. Report any failed render or delivery. Never infer review or export success from submission alone.

Use the configured BESTIARY repository only. Never ask for or print credential values in chat. Do not upload an episode to YouTube or Facebook. Treat a production request as permission to start one render in the configured private repo.
