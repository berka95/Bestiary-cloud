"""Synthesize the original score and sound effects and mux the episode."""
import argparse
import json
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy import signal

BASE = Path(__file__).resolve().parent
RATE = 48000
TAU = 2*math.pi


def note_freq(midi):
    return 440 * 2**((midi-69)/12)


def band(samples, low, high):
    return signal.sosfilt(signal.butter(2, [low, high], btype="bandpass",
                                       fs=RATE, output="sos"), samples)


def score(timing, path):
    duration = timing["duration"]
    t = np.arange(round(duration*RATE))/RATE
    rng = np.random.default_rng(1717)
    bed = np.zeros((len(t),2))
    pink = band(rng.standard_normal(len(t)),70,420)
    bubble = band(rng.standard_normal(len(t)),310,1010)
    bed[:,0] += .027*pink*(1+.3*np.sin(TAU*.21*t))
    bed[:,1] += .027*np.roll(pink,429)*(1+.25*np.sin(TAU*.23*t+.6))
    bed[:,0] += .012*bubble
    bed[:,1] += .012*np.roll(bubble,193)

    def layer(start, length, pan, gen):
        first = max(0,round(start*RATE))
        last = min(len(t),round((start+length)*RATE))
        if last <= first:
            return
        local = t[first:last]-start
        shape = gen(local, length)
        bed[first:last,0] += math.cos((pan+1)*math.pi/4)*shape
        bed[first:last,1] += math.sin((pan+1)*math.pi/4)*shape

    # Slow, overlapping synthesizer chords under a spare, original chip motif.
    for start,chord in ((-.2,(38,45,53)),(5.8,(34,41,48)),(11.8,(36,43,51)),
                        (17.8,(33,45,52)),(23.8,(38,45,53))):
        for index,midi in enumerate(chord):
            f=note_freq(midi)

            def pad(tt,length,f=f,index=index):
                env=np.clip(tt/.95,0,1)*np.clip((length-tt)/1.3,0,1)
                phase=TAU*f*tt
                tone=np.sin(phase+.11*np.sin(TAU*.31*tt))
                overtone=.25*np.sin(phase*2.008)+.11*np.sin(phase*3)
                return env*(tone+overtone)*(.047 if index==0 else .021)

            layer(start,7.35,(-.38,.42,0)[index],pad)

    motif=(62,65,69,67,62,60,65,64)
    for i in range(math.ceil(duration/1.48)):
        f=note_freq(motif[i%len(motif)])
        start=.68+1.48*i

        def chip(tt,length,f=f):
            env=np.clip(tt/.035,0,1)*np.exp(-tt*4.4)
            p=TAU*f*tt
            return .034*env*(np.sin(p)+.31*np.sin(3*p)+.13*np.sin(5*p))

        layer(start,1.32,(-.48 if i%2==0 else .48),chip)
        layer(start+.21,1.30,(.56 if i%2==0 else -.56),
              lambda tt,length,chip=chip: .26*chip(tt,length))

    caps=timing["captions"]
    for j,pivot in enumerate((.13,caps[2][0],caps[7][0]+.28,caps[8][0]-.12)):
        def sweep(tt,length,index=j):
            env=np.sin(np.pi*np.clip(tt/length,0,1))**1.9
            f=84+index*13
            return .048*env*np.sin(TAU*(f*tt-16*tt*tt)) + .044*env*band(
                rng.standard_normal(len(tt)),240+100*index,980+220*index)

        layer(pivot-.10,.48,-.25+j*.16,sweep)

    for i,pivot in enumerate((caps[5][0]+.25,caps[7][0]+.42,caps[9][0]+.12)):
        def sonar(tt,length,index=i):
            env=np.clip(tt/.025,0,1)*np.exp(-tt*7)
            f=(351,448,526)[index]
            return env*.053*(np.sin(TAU*f*tt)+.20*np.sin(TAU*2.02*f*tt))

        layer(pivot,.85,.30,sonar)

    bed *= (np.clip(t/.075,0,1)*np.clip((duration-t)/.27,0,1))[:,None]
    pcm = np.rint(32767*np.clip(bed,-1,1)).astype("<i2")
    with wave.open(str(path),"wb") as out:
        out.setparams((2,2,RATE,0,"NONE","not compressed"))
        out.writeframes(pcm.tobytes())


def mix(video, music, voice, duration, output):
    command=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),
             "-i",str(music)]
    if voice:
        command += ["-i",str(voice),"-filter_complex",
                    "[2:a]highpass=f=70,loudnorm=I=-16:TP=-2:LRA=8,aresample=48000,"
                    "aformat=channel_layouts=stereo,apad[n];"
                    "[1:a]volume=0.55[m];[n][m]amix=inputs=2:duration=first:"
                    "normalize=0,alimiter=limit=0.82:level=false[a]",
                    "-map","0:v:0","-map","[a]"]
    else:
        command += ["-map","0:v:0","-map","1:a:0"]
    command += ["-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000",
                "-ac","2","-t",str(duration),"-movflags","+faststart",str(output)]
    subprocess.run(command,check=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--timing",type=Path,default=BASE/"episode.json")
    parser.add_argument("--video",type=Path,required=True)
    parser.add_argument("--voice",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    timing=json.loads(args.timing.read_text())
    music=args.video.with_suffix(".wav")
    score(timing,music)
    mix(args.video,music,args.voice,timing["duration"],args.output)
