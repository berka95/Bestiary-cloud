"""Original procedural pixel-art animation, 17s retention pilot."""
import argparse, json, math, random, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=270,480,30
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
rng=random.Random(23)
particles=[(rng.randrange(W),rng.randrange(H),rng.uniform(2,12),rng.randrange(1,3)) for _ in range(100)]
stones=[(rng.randrange(W),rng.randrange(380,480),rng.randrange(8,30)) for _ in range(34)]
def smooth(x): 
    x=max(0,min(1,x)); return x*x*(3-2*x)
def bolt(d,x,y,tx,ty,seed):
    r=random.Random(seed); p=[(x,y)]
    for j in range(1,9):
        a=j/9; p.append((x+(tx-x)*a+r.randint(-9,9),y+(ty-y)*a+r.randint(-10,10)))
    p.append((tx,ty))
    for c,w in [('#205965',9),('#27b8c7',5),('#b9ffff',2),('#ffffff',1)]:
        d.line(p,fill=c,width=w)
def frame(t,timing):
    dur=timing['duration']; phase=t/dur*math.tau
    caps=timing['captions']
    reveal=caps[3][0]; approach=caps[4][0]; shock=caps[6][0]
    hit=max(0,1-abs(t-.32)/.45,1-abs(t-shock-.25)/.7)
    zoom=1+.15*smooth(t/1.3)+.25*smooth((t-reveal)/.6)-.4*smooth((t-approach)/.6)
    loop=smooth((t-(dur-.75))/.75); zoom=zoom*(1-loop)+loop
    im=Image.new('RGB',(W,H)); d=ImageDraw.Draw(im)
    for y in range(0,H,4):
        d.rectangle((0,y,W,y+3), fill=(7+int(y*.017),39-int(y*.038),48-int(y*.035)))
    for i in range(5):
        x=25+i*61+10*math.sin(phase+i)
        d.polygon([(x,0),(x+18,0),(x-30,390),(x-65,390)],fill=(10,39,44))
    for x,y,r in stones:
        d.ellipse((x-r,y-r//3,x+r,y+r//3),fill='#233f37',outline='#345448')
    for i in range(18):
        x=(i*29+7)%W
        pts=[(x+int(7*math.sin(phase+j*.6+i)),470-j*9) for j in range(11)]
        d.line(pts,fill='#315f47',width=3)
    for x,y,s,r in particles:
        px=int((x+12*math.sin(phase+y))%W); py=int((y+8*math.cos(phase+x))%H)
        d.rectangle((px,py,px+r,py+r),fill='#326466')
    hx=182+9*math.sin(phase); hy=228+8*math.cos(phase)
    hx+=18*smooth((t-approach)/.6)*(1-loop)
    points=[]
    for j in range(43):
        a=j/42; x=hx-178*a*zoom; y=hy+24*math.sin(a*7-phase)*a*zoom+64*a*a
        points.append((int(x),int(y)))
    for j in range(len(points)-1,0,-1):
        a=j/42; x,y=points[j]; width=max(3,int((15-12*a)*zoom))
        d.ellipse((x-width,y-width//2,x+width,y+width//2),fill='#182c26')
        # Thin tail segments have no room for an inset ellipse.
        if width >= 4:
            d.ellipse((x-width+2,y-width//2+2,x+width-2,y+width//2-1),fill='#a28a48')
            d.line((x-width+3,y-width//3,x+width-3,y-width//3),fill='#d3b76c',width=2)
    d.ellipse((hx-24*zoom,hy-13*zoom,hx+25*zoom,hy+13*zoom),fill='#b8a05a',outline='#352c21',width=2)
    d.ellipse((hx+8,hy-6,hx+13,hy-1),fill='#171c1e')
    d.point((int(hx+10),int(hy-5)),fill='white')
    d.line((hx+12,hy+6,hx+24,hy+3),fill='#483a28',width=2)
    preyx=240-19*smooth((t-approach)/.9)*(1-loop); preyy=hy-36+6*math.sin(phase*2)
    preyy+=10*math.sin(t*45)*hit
    d.polygon([(preyx+8,preyy),(preyx+19,preyy-7),(preyx+19,preyy+7)],fill='#a8b6a1')
    d.ellipse((preyx-12,preyy-6,preyx+10,preyy+6),fill='#b8d5ce',outline='#536b6b')
    d.point((int(preyx-7),int(preyy-1)),fill='#091821')
    if hit>.05:
        for i in range(3):
            bolt(d,hx-18+i*8,hy-5,preyx,preyy+i*5,int(t*12)+i*53)
    if reveal<=t<approach:
        f=ImageFont.truetype(FONT,30); d.text((125,125),'860 V',font=f,anchor='mm',fill='#fff4a1',stroke_width=2,stroke_fill='#0b2326')
        for j in range(6):
            x=54+j*25; height=9+int(19*(.5+.5*math.sin(t*8+j)))
            d.rectangle((x,158-height,x+15,158),fill='#62dce0')
    # Pixel art fills canvas; subtitles stay inside mobile-safe area.
    im=im.resize((1080,1920),Image.Resampling.NEAREST); d=ImageDraw.Draw(im)
    cap=next((c for a,b,c in caps if a<=t<b),None)
    if cap:
        words=cap.upper().split(); rows=[' '.join(words)]
        if len(rows[0])>18:
            k=(len(words)+1)//2; rows=[' '.join(words[:k]),' '.join(words[k:])]
        font=ImageFont.truetype(FONT,64)
        for i,row in enumerate(rows):
            size=64
            while d.textlength(row,font=font)>790:
                size-=2; font=ImageFont.truetype(FONT,size)
            d.text((495,1275+i*78),row,font=font,anchor='mm',fill='#fff9e8',stroke_width=6,stroke_fill='#102028')
    return im
def main():
    p=argparse.ArgumentParser(); p.add_argument('--timing',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    timing=json.loads(a.timing.read_text())
    proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1080x1920','-framerate','30','-i','-','-an','-c:v','libx264','-threads','3','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',str(a.output)],stdin=subprocess.PIPE)
    try:
        for i in range(round(timing['duration']*FPS)):
            proc.stdin.write(frame(i/FPS,timing).tobytes())
    finally:
        proc.stdin.close()
        if proc.wait(): raise RuntimeError('FFmpeg failed')
if __name__=='__main__': main()
