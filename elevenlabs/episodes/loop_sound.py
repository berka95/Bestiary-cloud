"""Original gameplay music and effects with a continuous musical loop."""
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
    duration=timing["duration"]
    count=round(rate*duration)
    t=np.arange(count)/rate
    starts=[row[0] for row in timing["captions"]]
    ant=episode=="EP21"
    track=(50,57,60,57,48,55,58,55) if ant else (55,62,67,64,53,60,65,62)
    base=round(440*2**((track[0]-81)/12)*duration)/duration
    audio=.010*np.sin(2*np.pi*t*base)*(.75+.25*np.cos(2*np.pi*t/duration*8))
    beat=duration/48

    def play(start,freq,length,gain,slide=0,wrap=False):
        n=round(length*rate)
        begin=round(start*rate)
        if not wrap:
            n=min(n,count-begin)
        if n<=0:
            return
        phase_t=np.arange(n)/rate
        angles=2*np.pi*(phase_t*freq+slide*phase_t*phase_t)
        env=np.minimum(1,phase_t*92)*np.exp(-5*phase_t/length)*np.clip((length-phase_t)*33,0,1)
        ix=np.arange(n)
        audio[(ix+begin)%count]+=gain*env*(np.sin(angles)+.24*np.sin(3*angles))

    for k in range(48):
        freq=440*2**((track[k%8]-69)/12)
        play((k+.13)*beat,freq,beat*1.25,.019,wrap=True)
        if not k%4:
            play((k+.13)*beat,freq/2,beat*1.8,.018,wrap=True)
    if ant:
        for k in range(4):
            play(starts[6]+.13*k,480+k*28,.24,.049,-360)
        play(starts[7]+.19,244,.38,.040,-130)
        win=starts[8]+.52
    else:
        play(starts[4]+.08,558,.22,.045,120)
        play(starts[5]+.08,698,.25,.049,120)
        win=starts[7]+.62
    for j,freq in enumerate((523,659,784)):
        play(win+j*.12,freq,.25,.027)
    bed=args.video.with_suffix(".wav")
    with wave.open(str(bed),"wb") as out:
        out.setparams((2,2,rate,0,"NONE","not compressed"))
        out.writeframes(np.round(np.repeat(audio[:,None],2,axis=1)*32767).astype("<i2").tobytes())
    mix.mix(args.video,bed,args.voice,duration,args.output)
