"""Generate timestamped ElevenLabs narration and render a BESTIARY episode."""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
MODEL = "eleven_v4"
VOICE = "CwhRBWXzGAHq8TQ4Fs17"
VOICE_SETTINGS = {"stability": .5, "similarity_boost": .75}
API = "https://api.elevenlabs.io/v1"
FPS = 30


def save_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def api(path, payload=None):
    token = os.environ.get("ELEVENLABS_API_KEY")
    if not token:
        raise ValueError("Set ELEVENLABS_API_KEY as a cloud secret.")
    request = Request(API + path, headers={"xi-api-key": token,
                      "Content-Type": "application/json", "Accept": "application/json"},
                      data=None if payload is None else json.dumps(payload).encode())
    try:
        with urlopen(request, timeout=90) as response:
            return json.load(response), response.headers
    except HTTPError as exc:
        raise ValueError(f"ElevenLabs returned HTTP {exc.code}. Check permissions, model and quota.") from None
    except (URLError, TimeoutError):
        raise ValueError("ElevenLabs could not be reached reliably.") from None


def preflight(voice_id, text):
    subscription, _ = api("/user/subscription")
    if subscription.get("max_credit_limit_extension") != 0:
        raise ValueError("Turn off usage-based billing before generating narration.")
    remaining = subscription["character_limit"] - subscription["character_count"]
    voice, _ = api("/voices/" + quote(voice_id, safe=""))
    models, _ = api("/models")
    model = next((item for item in models if item["model_id"] == MODEL), {})
    if not model.get("can_do_text_to_speech"):
        raise ValueError("Eleven v4 TTS is unavailable on this account.")
    # Allow at least one credit per character even when the API quotes a lower factor.
    factor = max(1., float(model.get("token_cost_factor") or 1.))
    estimate = math.ceil(len(text) * factor)
    if remaining < estimate:
        raise ValueError(f"Insufficient included credits. Available {remaining}, estimated {estimate}.")
    print(f"Voice {voice['name']} | {MODEL} | {len(text)} characters | {remaining} included credits")
    return estimate


def speech(cache, payload, voice_id):
    response_path = cache / "speech.json"
    if response_path.exists():
        return json.loads(response_path.read_text())
    estimate = preflight(voice_id, payload["text"])
    marker = cache / "request-started"
    try:
        with marker.open("x") as out:
            out.write("One generation requested. Check ElevenLabs History before retrying.\n")
    except FileExistsError:
        raise ValueError(f"A generation was already attempted. Review ElevenLabs History and {marker}.") from None
    data, headers = api("/text-to-speech/" + quote(voice_id, safe="") +
                        "/with-timestamps?output_format=mp3_44100_128", payload)
    result = {"audio_base64": data["audio_base64"], "alignment": data.get("alignment"),
              "reported_credits": headers.get("character-cost"), "estimated_credits": estimate}
    save_json(response_path, result)
    return result


def aligned_cues(captions, alignment, tempo, duration):
    if not alignment:
        raise ValueError("ElevenLabs returned audio without original-text timing. Cached audio preserved.")
    text = " ".join(captions)
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    if "".join(chars) != text or len(chars) != len(starts) or len(chars) != len(ends):
        raise ValueError("ElevenLabs timing differs from the submitted script. Cached audio preserved.")
    cues = []
    pos = 0
    for caption in captions:
        length = len(caption)
        start = max(0., starts[pos]/tempo - .04)
        end = min(duration, ends[pos+length-1]/tempo + .08)
        cues.append([start, end, caption])
        pos += length + 1
    for index in range(len(cues)-1):
        cues[index][1] = min(cues[index][1], cues[index+1][0])
    if any(not (0 <= start < end <= duration) or end-start < .3
           for start, end, _ in cues):
        raise ValueError("Subtitle timing needs review. Cached audio preserved.")
    return cues


def run(*args):
    subprocess.run(args, check=True)


def probe(path, count=False):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", *(["-count_frames"] if count else []),
        "-show_streams", "-show_format", "-of", "json", str(path)
    ]))


def verify(path, runtime):
    info = probe(path, count=True)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    if ((video["codec_name"], video["width"], video["height"], video["r_frame_rate"],
         int(video["nb_read_frames"]), audio["codec_name"], audio["sample_rate"])
        != ("h264", 1080, 1920, "30/1", round(runtime*FPS), "aac", "48000")
        or abs(float(info["format"]["duration"])-runtime) > .04):
        raise ValueError("The candidate MP4 did not meet the delivery specification.")
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-xerror", "-i", str(path), "-vf",
        "blackdetect=d=0.033:pix_th=0.07:pic_th=0.99,freezedetect=n=-55dB:d=0.5",
        "-af", "ebur128=peak=true", "-f", "null", "-"
    ], capture_output=True, text=True, check=True)
    peak = re.search(r"Peak:\s+(-?\d+\.\d+) dBFS", result.stderr)
    loudness = re.search(r"Integrated loudness:\s+I:\s+(-?\d+\.\d+) LUFS", result.stderr)
    if ("black_start:" in result.stderr or "freeze_start:" in result.stderr
        or not peak or float(peak[1]) > -1 or not loudness
        or not -24 <= float(loudness[1]) <= -12):
        raise ValueError("The candidate MP4 failed the black frame, freeze or audio check.")
    return {"duration": runtime, "frames": int(video["nb_read_frames"]),
            "loudness_lufs": float(loudness[1]), "peak_dbfs": float(peak[1])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", help="Episode folder name, e.g. EP17")
    parser.add_argument("--check", action="store_true", help="Check account without generating")
    args = parser.parse_args()
    if not re.fullmatch(r"EP[0-9]+", args.episode):
        raise ValueError("Expected an episode ID like EP17.")
    episode = ROOT / "episodes" / args.episode
    spec = json.loads((episode / "episode.json").read_text())
    runtime = spec["duration"]
    captions = spec["captions"]
    animal = spec["animal"]
    if not re.fullmatch(r"[A-Z0-9_]+", animal) or not 20 <= runtime <= 30 or runtime*FPS % 1:
        raise ValueError("Use an uppercase animal slug and a frame-aligned runtime of 20–30 seconds.")
    if not captions or any(not line.strip() for line in captions):
        raise ValueError("Each subtitle must contain text.")
    texts = [" ".join(caption.split()) for caption in captions]
    text = " ".join(texts)
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID") or VOICE
    if args.check:
        preflight(voice_id, text)
        return
    for name in ("render.py", "sound.py", "publishing.txt"):
        if not (episode/name).is_file():
            raise ValueError(f"Missing episode input {name}.")

    payload = {"text": text, "model_id": MODEL, "language_code": "id",
               "voice_settings": VOICE_SETTINGS}
    digest = hashlib.sha256(json.dumps([voice_id, payload], sort_keys=True).encode()).hexdigest()
    cache = ROOT / ".work" / args.episode / digest
    cache.mkdir(parents=True, exist_ok=True)
    result = speech(cache, payload, voice_id)
    mp3, wav = cache/"voice.mp3", cache/"voice.wav"
    mp3.write_bytes(base64.b64decode(result["audio_base64"], validate=True))
    raw_duration = float(probe(mp3)["format"]["duration"])
    # Keep short reads natural. Resize the episode before slowing speech past 0.82x.
    if raw_duration / (runtime - .65) < .82:
        runtime = max(20, math.ceil((raw_duration / .88 + .65) * FPS) / FPS)
    tempo = max(.80, raw_duration / (runtime - .65))
    if not .75 <= tempo <= 1.30:
        raise ValueError("Narration requires excessive retiming. Cached audio preserved.")
    run("ffmpeg","-v","error","-y","-i",str(mp3),"-af",f"atempo={tempo:.8f}",
        "-ac","1","-ar","48000",str(wav))
    cues = aligned_cues(texts, result["alignment"], tempo, runtime)
    for cue, caption in zip(cues, captions):
        cue[2] = caption
    timing = cache / "timing.json"
    save_json(timing, {"duration": runtime, "captions": cues})

    picture, candidate = cache/"picture.mp4", cache/"candidate.mp4"
    run(sys.executable,str(episode/"render.py"),"--timing",str(timing),"--output",str(picture))
    run(sys.executable,str(episode/"sound.py"),"--timing",str(timing),"--video",str(picture),
        "--voice",str(wav),"--output",str(candidate))
    qa = verify(candidate, runtime)
    output = ROOT / "output" / args.episode
    output.mkdir(parents=True, exist_ok=True)
    filename = f"BESTIARY_16BIT_{args.episode}_{animal}_FINAL_ID.mp4"
    candidate.replace(output/filename)
    reported = result["reported_credits"]
    credits = (f"Kredit narasi dilaporkan ElevenLabs {reported}."
               if reported is not None else
               f"Kredit aktual tidak ditampilkan. Estimasi {result['estimated_credits']}.")
    (output/"PAKET_PUBLIKASI.txt").write_text(
        (episode/"publishing.txt").read_text().rstrip() +
        f"\n\n{filename}\nBiaya render tambahan Rp0. {credits}\n")
    save_json(output/"qa.json", qa)
    print(output/filename)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, StopIteration, subprocess.CalledProcessError) as exc:
        sys.exit(f"BESTIARY: {exc}")
