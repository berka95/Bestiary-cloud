"""Build a bilingual BESTIARY episode from a topic or an existing plan."""
import argparse
import datetime
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from cinema import Stage, score

ROOT=Path(__file__).resolve().parent
PRESET=ROOT/"presets"/"ep15"
VOICE="M5iZBikqML8Qf1IzbJ31"


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


def dump(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")


def probe(path):
    p=run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],capture_output=True)
    return json.loads(p.stdout)


def duration(path):
    return float(probe(path)["format"]["duration"])


def plan(topic, episode, folder):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Tambahkan OPENAI_API_KEY di GitHub Actions Secrets untuk topik baru.")
    prompt = (ROOT/"PLANNER.md").read_text()
    prompt += "\n\nCONTOH FORMAT\n" + (PRESET/"episode.json").read_text()
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({
            "model": os.getenv("BESTIARY_RESEARCH_MODEL") or "gpt-5-mini",
            "instructions": prompt,
            "input": json.dumps({"topic":topic,"episode":episode},ensure_ascii=False),
            "tools": [{"type":"web_search","external_web_access":True}],
            "tool_choice": "required",
            "include": ["web_search_call.action.sources"],
            "text": {"format":{"type":"json_object"}},
            "max_output_tokens": 7000,
            "store": False,
        }).encode(),
        headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
    )
    try:
        with urllib.request.urlopen(request,timeout=240) as response:
            data=json.load(response)
    except urllib.error.HTTPError as err:
        raise ValueError(f"Riset OpenAI gagal (HTTP {err.code}). Periksa akses, model dan kuota API.") from None
    outputs=data.get("output",[])
    searches=[item for item in outputs if item.get("type")=="web_search_call" and item.get("status")=="completed"]
    if data.get("status")!="completed" or not searches:
        raise ValueError("Riset web belum selesai. Cek akses web search dan jalankan lagi.")
    answer="".join(content["text"] for item in outputs if item.get("type")=="message"
        for content in item.get("content",[]) if content.get("type")=="output_text")
    spec=json.loads(answer)
    if not spec.get("error"):
        cited={source.get("url","").rstrip("/") for item in searches
            for source in item.get("action",{}).get("sources",[])}
        cited.update(item.get("action",{}).get("url","").rstrip("/") for item in searches)
        cited.update(annotation["url"].rstrip("/") for item in outputs if item.get("type")=="message"
            for content in item.get("content",[]) for annotation in content.get("annotations",[])
            if annotation.get("type")=="url_citation" and annotation.get("url"))
        if any(source["url"].rstrip("/") not in cited for source in spec["sources"]):
            raise ValueError("Ada sumber storyboard yang tidak muncul di jejak pencarian.")
        dump(folder/"research.json",{"response_id":data.get("id"),"model":data.get("model"),
            "sources":spec["sources"]})
    return spec


def validate(spec):
    if spec.get("error"):
        raise ValueError(spec["error"])
    if not re.fullmatch(r"EP\d{2,4}",spec["episode"]) or not 2<=len(spec["name"])<=36:
        raise ValueError("Nama hewan atau nomor episode tidak valid.")
    if spec["habitat"] not in {"forest","desert","water","sky"} or spec["action"] not in {"slime","dash","leap","swim"}:
        raise ValueError("Habitat/action di luar pilihan renderer.")
    rig=spec["rig"]
    if rig["kind"] not in {"worm","quad","snake","fish","wing"} or rig["legs"] not in {0,2,4,6,8,13} or not 6<=rig["bulk"]<=20:
        raise ValueError("Rig di luar pilihan renderer.")
    if rig["kind"]=="quad" and rig["legs"]<2:
        raise ValueError("Rig quad perlu minimal dua kaki.")
    for key in ["color","light"]:
        if not re.fullmatch(r"#[a-fA-F0-9]{6}",rig[key]):
            raise ValueError("Warna rig harus hex RGB.")
    urls={source["url"] for source in spec["sources"] if source["supports"] and source["url"].startswith("https://")}
    if len(urls)<2 or len(spec["beats"])!=5:
        raise ValueError("Perlu dua sumber HTTPS berbeda dan lima beat storyboard.")
    if type(spec["target"]) is not bool or (spec["action"]=="slime" and not spec["target"]):
        raise ValueError("Adegan slime perlu target serangga.")
    for lang in ["en","id"]:
        info=spec[lang]
        lines=info["lines"]
        marks=info["marks"]
        word_count=len(" ".join(lines).split())
        if not 35<=word_count<=64 or not 6<=len(lines)<=12 or any(not 1<=len(line)<=56 for line in lines):
            raise ValueError(f"{lang}: gunakan 35–64 kata dan 6–12 caption pendek (maks. 56 karakter).")
        if len(marks)!=4 or not 0<marks[0]<marks[1]<marks[2]<marks[3]<len(lines):
            raise ValueError(f"{lang}: indeks adegan tidak valid.")
        if not info["tags"] or not info["caption"] or not info["title"] or len(info["title"])>100:
            raise ValueError(f"{lang}: metadata belum lengkap.")


def tokens(text):
    return re.findall(r"[^\W_]+",text.casefold())


def timed_words(lines, words):
    """Match service timing to the spoken text. Never invent word timings."""
    if not words:
        raise ValueError("Provider tidak mengirim timing kata.")
    flat=[]
    cursor=0.0
    for word in words:
        start=word.get("start_time",word.get("start",cursor))
        end=word.get("end_time",word.get("end"))
        if end is None:
            raise ValueError("Timing kata tidak lengkap.")
        flat.extend((part,float(start),float(end)) for part in tokens(word.get("text",word.get("word",""))))
        cursor=float(end)
    cues=[]
    index=0
    for line in lines:
        expected=tokens(line)
        group=flat[index:index+len(expected)]
        if [item[0] for item in group]!=expected:
            raise ValueError(f"Timing VO tidak cocok dengan naskah: {line}")
        cues.append((group[0][1],group[-1][2],line))
        index+=len(expected)
    if index!=len(flat):
        raise ValueError("Provider mengirim kata tambahan.")
    return cues


def remote_voice(lines,lang,directory,key):
    payload={"text":" ".join(lines),"voice_id":VOICE,"language":lang,"engine":"heygen_voice"}
    request=urllib.request.Request("https://api.heygen.com/v3/voices/speech",
        data=json.dumps(payload).encode(),headers={"X-Api-Key":key,"Content-Type":"application/json"})
    response_file=directory/"heygen-response.json"
    if response_file.exists():
        data=json.loads(response_file.read_text())
    else:
        with urllib.request.urlopen(request,timeout=75) as response:
            data=json.load(response)["data"]
        dump(response_file,data)
    url=data["audio_url"]
    if not url.startswith("https://"):
        raise ValueError("Audio HeyGen tidak memiliki URL HTTPS.")
    raw=directory/"heygen-audio"
    if not raw.exists():
        with urllib.request.urlopen(url,timeout=40) as response:
            raw.write_bytes(response.read())
    voice=directory/"voice.wav"
    run(["ffmpeg","-v","error","-y","-i",str(raw),"-ar","48000","-ac","1",str(voice)])
    return voice,timed_words(lines,data.get("word_timestamps")),f"HeyGen REST · {VOICE}"


def stamp(value):
    ms=round(value*1000)
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"


def valid_cues(cues,voice_length):
    prior=0
    for start,end,text in cues:
        if not math.isfinite(start) or not math.isfinite(end) or start<prior-.04 or end<=start or end>voice_length+.06:
            raise ValueError(f"Timing VO tidak valid untuk caption: {text}")
        prior=end


def get_voice(args,spec,lang,directory,preset):
    lines=spec[lang]["lines"]
    if preset:
        manifest=json.loads((PRESET/"timings.json").read_text())
        source=directory/"voice.wav"
        shutil.copyfile(PRESET/f"{lang}.wav",source)
        return source,timed_words(lines,manifest[lang]["original_words"]),f"HeyGen · {VOICE} · EP15 bundled"
    if args.recorded:
        voice=args.recorded/f"{lang}.wav"
        ranges=json.loads((args.recorded/f"{lang}.json").read_text())
        cues=[(float(a),float(b),line) for (a,b),line in zip(ranges,lines,strict=True)]
        shutil.copyfile(voice,directory/"voice.wav")
        return directory/"voice.wav",cues,"Rekaman manusia lokal · timing dari rekaman"
    key=os.getenv("HEYGEN_API_KEY")
    if not key:
        raise ValueError(f"{lang}: setel HEYGEN_API_KEY di repo atau gunakan paket voice rekaman.")
    try:
        return remote_voice(lines,lang,directory,key)
    except (urllib.error.URLError,TimeoutError,ValueError,KeyError) as err:
        detail=f"HTTP {err.code}" if isinstance(err,urllib.error.HTTPError) else type(err).__name__
        raise ValueError(f"{lang}: VO HeyGen gagal ({detail}). Gunakan draft dan rekaman sendiri bila akses atau kuota habis.") from None


def render(spec,lang,directory,voice,cues,provider):
    voice_length=duration(voice)
    valid_cues(cues,voice_length)
    total=math.ceil(max(21,voice_length+1.3)*30)/30
    if total>25:
        raise ValueError(f"{lang}: VO {voice_length:.1f}s terlalu panjang. Pendekkan naskah atau rekam ulang.")
    marks=[cues[i][0] for i in spec[lang]["marks"]]
    print(f"Render {lang.upper()} • {total:.2f} detik • {provider}",flush=True)
    (directory/"subtitles.srt").write_text("\n".join(
        f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n" for i,(a,b,text) in enumerate(cues,1)))
    dump(directory/"timeline.json",dict(zip(["reveal","action","payoff","endcard"],marks)))
    info=spec[lang]
    dump(directory/"upload.json",{key:info[key] for key in ["title","caption","tags"]})
    (directory/"upload.txt").write_text(f"{info['title']}\n\n{info['caption']}\n\n"+", ".join(info["tags"])+"\n")
    score(total,marks,directory)
    video=directory/"silent.mp4"
    unique=Stage(spec,lang).render(video,cues,marks,total)
    output=directory/("YouTube_Shorts_EN.mp4" if lang=="en" else "Facebook_Reels_ID.mp4")
    tmp=directory/"mix.mp4"
    inputs=[path for path in [video,voice,directory/"music.wav",directory/"sfx.wav"] for path in ["-i",str(path)]]
    mix=("[1:a]loudnorm=I=-17:TP=-2:LRA=7,aresample=48000,apad,asplit=2[narr][side];"
         "[2:a][side]sidechaincompress=threshold=0.025:ratio=4:attack=25:release=240[bed];"
         "[3:a]volume=0.62[fx];[narr][bed][fx]amix=inputs=3:duration=first:normalize=0,"
         "alimiter=limit=0.84:level=0:latency=1[a]")
    run(["ffmpeg","-v","error","-y",*inputs,"-filter_complex",mix,"-map","0:v","-map","[a]",
         "-c:v","copy","-c:a","aac","-ac","2","-b:a","192k","-t",str(total),"-movflags","+faststart",str(tmp)])
    stats=probe(tmp)
    video_stream,audio_stream=stats["streams"]
    frames=int(video_stream.get("nb_frames",0))
    if ((video_stream["width"],video_stream["height"],video_stream["avg_frame_rate"])!=(1080,1920,"30/1")
        or audio_stream["codec_name"]!="aac" or frames!=round(total*30) or unique<frames*.7
        or not 20<=float(stats["format"]["duration"])<=25.05):
        raise ValueError("QA teknis gagal. Video sementara disimpan untuk diagnosis.")
    run(["ffmpeg","-v","error","-xerror","-i",str(tmp),"-f","null","-"])
    scan=run(["ffmpeg","-hide_banner","-i",str(tmp),"-vn","-af","volumedetect","-f","null","-"],
             capture_output=True,text=True).stderr
    peak=float(re.search(r"max_volume: (-?[\d.]+) dB",scan)[1])
    if not -18<peak<-.1:
        raise ValueError(f"QA mix gagal: peak {peak} dBFS.")
    dump(directory/"qa.json",{
        "technical":"PASS","duration_seconds":float(stats["format"]["duration"]),"size":"1080x1920",
        "fps":30,"frames":frames,"unique_uncompressed_stage_frames":unique,"max_volume_dbfs":peak,
        "caption_box_px":[86,1282,949,1441],"voice":provider,"voice_duration_seconds":voice_length,
        "remaining_review":"Cek pelafalan, kenyamanan VO, kemiripan spesies, dan overlay aplikasi saat upload."})
    tmp.replace(output)
    video.unlink()
    print(output,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic",nargs="?",default="Velvet Worm")
    parser.add_argument("--episode")
    parser.add_argument("--plan",type=Path)
    parser.add_argument("--recorded",type=Path)
    parser.add_argument("--plan-only",action="store_true")
    args=parser.parse_args()
    for binary in ["ffmpeg","ffprobe"]:
        if not shutil.which(binary) and not args.plan_only:
            raise ValueError(f"{binary} belum terpasang.")
    topic=slug(args.topic)
    parent=Path(os.getenv("BESTIARY_OUTPUT",str(ROOT/"renders"))).expanduser().resolve()
    parent.mkdir(parents=True,exist_ok=True)
    folder=parent/f"{datetime.datetime.now():%Y%m%d-%H%M%S-%f}_{topic}"
    folder.mkdir()
    preset=not args.plan and topic in {"velvet-worm","ep15","onychophora"}
    episode=args.episode or next_episode(parent)
    if not re.fullmatch(r"EP\d{2,4}",episode):
        raise ValueError("Gunakan nomor seperti EP16.")
    spec=(json.loads(args.plan.read_text()) if args.plan else
          json.loads((PRESET/"episode.json").read_text()) if preset else plan(args.topic,episode,folder))
    validate(spec)
    dump(folder/"episode.json",spec)
    (folder/"storyboard.md").write_text(
        f"# {spec['episode']} · {spec['name']}\n\n"
        + "\n".join(f"{i}. {beat}" for i,beat in enumerate(spec["beats"],1))
        + "\n\n## Sumber\n\n" + "\n".join(
            f"- {source['supports']} [{source['url']}]({source['url']})" for source in spec["sources"])+"\n")
    print(f"Folder episode: {folder}",flush=True)
    if args.plan_only:
        return
    failures=[]
    for lang in ["en","id"]:
        directory=folder/lang
        directory.mkdir()
        try:
            voice,cues,provider=get_voice(args,spec,lang,directory,preset and not args.recorded)
            render(spec,lang,directory,voice,cues,provider)
        except (OSError,ValueError,KeyError,RuntimeError,subprocess.CalledProcessError) as err:
            failures.append(f"{lang.upper()} — {err}")
    if failures:
        raise ValueError("\n".join(failures))
    print(f"Selesai: {folder}")


def next_episode(parent):
    numbers=[15]
    for path in parent.glob("*/episode.json"):
        try:
            ep=json.loads(path.read_text())["episode"]
        except (OSError,ValueError,KeyError):
            continue
        if re.fullmatch(r"EP\d{2,4}",ep):
            numbers.append(int(ep[2:]))
    return f"EP{max(numbers)+1:02d}"


def slug(text):
    return re.sub(r"[^a-z0-9]+","-",text.lower()).strip("-")[:50] or "episode"


if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
        sys.exit(f"Produksi berhenti. {error}")
