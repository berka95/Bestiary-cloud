"""Generate timestamped Roger narration and render long-form BESTIARY."""
import base64
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np

ROOT = Path(__file__).resolve().parent
MODEL = "eleven_v4"
VOICE = "CwhRBWXzGAHq8TQ4Fs17"
FPS = 30
API = "https://api.elevenlabs.io/v1"


def run(*args):
    subprocess.run(args, check=True)


def api(path, payload=None):
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise ValueError("Missing ELEVENLABS_API_KEY GitHub secret.")
    req = Request(API+path, headers={"xi-api-key":key,"Content-Type":"application/json",
                  "Accept":"application/json"},
                  data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode())
    try:
        with urlopen(req,timeout=120) as response:
            return json.load(response), response.headers
    except HTTPError as exc:
        raise ValueError(f"ElevenLabs returned HTTP {exc.code}; check access and included credits.") from None
    except (URLError,TimeoutError):
        raise ValueError("Could not reach ElevenLabs reliably.") from None


def preflight(voice_id, chapters):
    subscription,_=api("/user/subscription")
    remaining=int(subscription["character_limit"])-int(subscription["character_count"])
    models,_=api("/models")
    model=next((x for x in models if x.get("model_id")==MODEL),{})
    if not model.get("can_do_text_to_speech"):
        raise ValueError("Eleven v4 text-to-speech is unavailable on this account.")
    voice,_=api("/voices/"+quote(voice_id,safe=""))
    factor=max(1.0,float(model.get("token_cost_factor") or 1))
    estimate=math.ceil(sum(len(c["text"]) for c in chapters)*factor)
    if estimate>remaining:
        raise ValueError(f"Included credits are insufficient. Available {remaining}; estimated {estimate}.")
    print(f"Voice {voice.get('name','Roger')} | {MODEL} | about {estimate} included credits")
    return estimate


def aligned_captions(text, alignment, duration):
    chars=alignment.get("characters",[])
    starts=alignment.get("character_start_times_seconds",[])
    ends=alignment.get("character_end_times_seconds",[])
    if "".join(chars)!=text or len(chars)!=len(starts) or len(chars)!=len(ends):
        raise ValueError("ElevenLabs timing did not match the submitted narration.")
    words=list(re.finditer(r"\S+",text))
    groups=[]
    current=[]
    for word in words:
        trial=(text[current[0].start():word.end()] if current else word.group())
        if current and len(trial)>34:
            groups.append(current)
            current=[word]
        else:
            current.append(word)
    if current:
        groups.append(current)
    cues=[]
    for group in groups:
        first,last=group[0],group[-1]
        start=max(0.0,float(starts[first.start()])-.06)
        end=min(duration,float(ends[last.end()-1])+.12)
        caption=text[first.start():last.end()]
        # keep captions readable and within a phone safe area
        if len(caption)>38:
            split=caption.rfind(" ",0,34)
            if split>10:
                midpoint=first.start()+split
                cues.append([start,min(duration,float(ends[midpoint-1])+.08),
                             caption[:split]+"\n"+caption[split+1:]])
                continue
        cues.append([start,end,caption])
    for i in range(len(cues)-1):
        cues[i][1]=min(cues[i][1],cues[i+1][0])
    return cues


def probe(path):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams",
                    "-show_format","-of","json",str(path)]))


def pad_wav(path, target_seconds):
    with wave.open(str(path),"rb") as wav:
        params=wav.getparams()
        frames=wav.readframes(wav.getnframes())
    target_frames=round(target_seconds*params.framerate)
    if target_frames>len(frames)//params.nchannels//(params.sampwidth):
        silence=b"\0"*(target_frames*params.nchannels*params.sampwidth-len(frames))
        with wave.open(str(path),"wb") as out:
            out.setparams(params)
            out.writeframes(frames+silence)


def srt_time(seconds):
    ms=round(seconds*1000)
    h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    plan=json.loads((ROOT/"LONG01.json").read_text())
    chapters=plan["chapters"]
    if not chapters or any(not c["text"].strip() for c in chapters):
        raise ValueError("Longform plan has an empty chapter.")
    voice_id=os.environ.get("ELEVENLABS_VOICE_ID") or VOICE
    preflight(voice_id,chapters)
    out=ROOT.parent/"output"/"LONG01"
    out.mkdir(parents=True,exist_ok=True)
    captions_all=[]
    timeline=[]
    wave_paths=[]
    offset=0.0
    with tempfile.TemporaryDirectory(prefix="bestiary-long-") as tmp:
        tmp=Path(tmp)
        for index,chapter in enumerate(chapters,1):
            payload={"text":chapter["text"],"model_id":MODEL,"language_code":"id",
                     "voice_settings":{"stability":0.5,"similarity_boost":0.75}}
            data,_=api("/text-to-speech/"+quote(voice_id,safe="")+
                       "/with-timestamps?output_format=mp3_44100_128",payload)
            if not data.get("alignment"):
                raise ValueError("ElevenLabs returned audio without word timing.")
            mp3=tmp/f"voice-{index:02}.mp3"
            mp3.write_bytes(base64.b64decode(data["audio_base64"],validate=True))
            info=probe(mp3)
            raw_duration=float(info["format"]["duration"])
            duration=math.ceil(raw_duration*FPS)/FPS
            wav=tmp/f"voice-{index:02}.wav"
            run("ffmpeg","-v","error","-y","-i",str(mp3),"-ac","2","-ar","48000",
                "-c:a","pcm_s16le",str(wav))
            pad_wav(wav,duration)
            wave_paths.append(wav)
            cues=aligned_captions(chapter["text"],data["alignment"],raw_duration)
            timeline.append({"id":chapter["id"],"scene":chapter["scene"],
                "depth_m":chapter["depth_m"],"duration":duration,"captions":cues})
            for start,end,text in cues:
                captions_all.append((offset+start,offset+end,text))
            offset+=duration
            print(f"Chapter {index}/{len(chapters)} generated.")
        if offset<180:
            raise ValueError("Longform runtime must be at least 3 minutes.")
        timeline_path=tmp/"timeline.json"
        timeline_path.write_text(json.dumps({"chapters":timeline},ensure_ascii=False))
        picture=tmp/"picture.mp4"
        run(sys.executable,str(ROOT/"render.py"),"--timeline",str(timeline_path),
            "--output",str(picture))
        voice_joined=tmp/"voice.wav"
        with wave.open(str(wave_paths[0]),"rb") as first:
            params=first.getparams()
        with wave.open(str(voice_joined),"wb") as joined:
            joined.setparams(params)
            for wav_path in wave_paths:
                with wave.open(str(wav_path),"rb") as part:
                    joined.writeframes(part.readframes(part.getnframes()))
        final=out/"BESTIARY_16BIT_LONG01_DEEP_OCEAN_FINAL_ID.mp4"
        # A low-level filtered pink-noise bed provides quiet underwater ambience.
        duration_arg=f"{offset:.3f}"
        run("ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(picture),
            "-i",str(voice_joined),"-f","lavfi","-i",
            f"anoisesrc=color=pink:amplitude=0.025:sample_rate=48000:duration={duration_arg}",
            "-filter_complex","[1:a]volume=1.0[v];[2:a]lowpass=f=240,volume=0.10[a];[v][a]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[aout]",
            "-map","0:v:0","-map","[aout]","-t",duration_arg,"-c:v","copy",
            "-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",str(final))
        srt=[]
        for i,(start,end,text) in enumerate(captions_all,1):
            srt.extend([str(i),f"{srt_time(start)} --> {srt_time(end)}",text.replace("\n"," "), ""])
        (out/"BESTIARY_16BIT_LONG01_DEEP_OCEAN_ID.srt").write_text("\n".join(srt),encoding="utf-8")
        info=probe(final)
        video=next(s for s in info["streams"] if s["codec_type"]=="video")
        audio=next(s for s in info["streams"] if s["codec_type"]=="audio")
        checks=(video["codec_name"],video["width"],video["height"],video["r_frame_rate"],
                audio["codec_name"],audio["sample_rate"])
        if checks!=("h264",1080,1920,"30/1","aac","48000"):
            raise ValueError(f"Final format check failed: {checks}")
        if abs(float(info["format"]["duration"])-offset)>0.06:
            raise ValueError("Final duration differs from narration timeline.")
        (out/"qa.json").write_text(json.dumps({"duration_seconds":offset,
             "video":checks[:4],"audio":checks[4:]},indent=2)+"\n")
        pub=(ROOT/"publishing.txt").read_text()
        (out/"PAKET_PUBLIKASI.txt").write_text(pub+"\n\n"+str(offset/60)+" minutes\n")
        print(final)


if __name__=="__main__":
    try:
        main()
    except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as exc:
        sys.exit(f"BESTIARY LONGFORM: {exc}")
