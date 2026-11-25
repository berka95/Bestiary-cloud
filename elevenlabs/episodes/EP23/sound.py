"""Original chip score and synchronized electric sound; ElevenLabs is narration only."""
import argparse,json,sys,wave
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'EP17'))
from sound import mix
def main():
    p=argparse.ArgumentParser()
    for key in ('timing','video','voice','output'): p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); timing=json.loads(a.timing.read_text()); dur=timing['duration']; rate=48000
    t=np.arange(round(dur*rate))/rate; rng=np.random.default_rng(23)
    bed=.025*np.sin(2*np.pi*55*t)+.015*np.sin(2*np.pi*110*t)
    for i in range(int(dur*2)):
        z=t-i*.5; env=np.exp(-np.maximum(z,0)*9)*(z>=0)*(z<.5)
        bed+=.023*env*np.sin(2*np.pi*[165,196,220,147][i%4]*z)
    for pivot in (.08,timing['captions'][3][0],timing['captions'][6][0]):
        z=t-pivot; env=np.exp(-np.maximum(z,0)*10)*(z>=0)*(z<.65)
        bed+=env*(.16*rng.standard_normal(len(t))+.12*np.sin(2*np.pi*(230*z-90*z*z)))
    bed*=np.minimum(1,t/.03)*np.minimum(1,np.maximum(0,(dur-t)/.08))
    stereo=np.stack((bed,np.roll(bed,50)),axis=1)
    music=a.video.with_suffix('.wav')
    with wave.open(str(music),'wb') as f:
        f.setparams((2,2,rate,0,'NONE','not compressed')); f.writeframes((np.clip(stereo,-1,1)*32767).astype('<i2').tobytes())
    mix(a.video,music,a.voice,dur,a.output)
if __name__=='__main__': main()
