"""Original chiptune with cues timed to the gameplay actions."""
import argparse
import importlib.util
import json
from pathlib import Path
import wave

import numpy as np

spec=importlib.util.spec_from_file_location("bestiary_mix",Path(__file__).with_name("EP17")/"sound.py")
mix=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mix)


def main(episode):
    parser=argparse.ArgumentParser()
    for name in ("timing","video","voice","output"):
        parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args()
    timing=json.loads(args.timing.read_text())
    rate=48000
    audio=np.zeros(round(rate*timing["duration"]),dtype=np.float32)
    beats=[cue[0] for cue in timing["captions"]]
    track=(55,62,65,62,53,60,64,60) if episode=="EP19" else (48,55,60,63,46,53,58,62)

    def play(start,freq,length,gain,slide=0):
        idx=round(start*rate)
        count=min(len(audio)-idx,round(length*rate))
        if count<=0:
            return
        t=np.arange(count)/rate
        phi=2*np.pi*(t*freq+slide*t*t)
        shape=np.minimum(1,t*90)*np.exp(-5*t/length)
        audio[idx:idx+count]+=gain*shape*(np.sin(phi)+.25*np.sin(3*phi))

    for i,beat in enumerate(np.arange(.15,timing["duration"],.46)):
        note=440*2**((track[i%8]-69)/12)
        play(beat,note,.43,.018)
        if i%4==0:
            play(beat,note/2,.60,.027)
    play(beats[4],564,.17,.035)
    if episode=="EP19":
        play(beats[6],1100,.38,.065,-1150)
        play(beats[7]+.73,212,.42,.055,-170)
    else:
        play(beats[3],490,.23,.046)
        play(beats[7]+.55,525,.30,.058,100)
        play(beats[7]+1.34,657,.30,.058,100)
    for i,freq in enumerate((523,659,784)):
        play(beats[9]+.65+i*.14,freq,.33,.039)
    bed=args.video.with_suffix(".wav")
    stereo=np.stack((audio,audio),axis=-1)
    with wave.open(str(bed),"wb") as out:
        out.setparams((2,2,rate,0,"NONE","not compressed"))
        out.writeframes(np.round(np.clip(stereo,-1,1)*32767).astype("<i2").tobytes())
    mix.mix(args.video,bed,args.voice,timing["duration"],args.output)
