"""Animate a Hawaiian bobtail squid with the BESTIARY HUD and pixel palette."""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "EP17"))
from render import (W, H, FPS, MONO_FONT, TITLE_FONT, CAPTION_FONT,
                    DITHER, INK, MINT, WARM, XX, YY, morph, particles)

rng = random.Random(1804)
SAND = [(rng.randrange(320),rng.randrange(110),rng.randrange(5),rng.randrange(5))
        for _ in range(1350)]
FLECKS = [(rng.randrange(-54,48),rng.randrange(-42,34),rng.random()) for _ in range(430)]
SPORES = [(rng.random(),rng.random(),rng.random()) for _ in range(95)]
MANTLE = [(-54,0),(-54,-10),(-50,-22),(-40,-32),(-25,-37),(-8,-36),
          (8,-30),(20,-21),(26,-10),(27,7),(21,19),(10,29),(-6,32),
          (-24,31),(-41,24),(-50,15)]


def rgbmix(left, right, amount):
    return tuple(round(a+(b-a)*amount) for a,b in zip(left,right))


def ocean(t, dawn, cx, cy, light, look):
    surface = np.exp(-((XX-157)/133)**2-((YY-55)/226)**2)
    beams = sum(np.exp(-((XX-o-(YY-30)*s+4*math.sin(t*.7+o))/w)**2)
                for o,s,w in ((40,.12,19),(99,-.24,12),(164,.21,24),(204,.09,7)))
    beams *= np.clip(1-YY/360,0,1)
    sea = surface*.73+beams*.13+.18*np.exp(-((YY-298)/106)**2)
    halo = light*np.exp(-((XX-cx)/62)**2-((YY-cy-19)/49)**2)
    base = np.stack([4+sea*(17+29*dawn)+18*halo,
                     13+sea*(58+9*dawn)+52*halo,
                     29+sea*(77-27*dawn)+47*halo],axis=-1)
    base += look*np.exp(-((YY-165)/100)**2)[...,None]*[7,15,19]
    base = np.clip(np.floor(base/3+DITHER[...,None])*3,0,255).astype(np.uint8)
    return Image.fromarray(base).convert("RGBA")


def floor_level(x, camera):
    return 306 + round(6*math.sin((x+camera*.54)/45)+3*math.sin((x+camera)/17))


def seabed(im, t, camera, dawn, front):
    d=ImageDraw.Draw(im)
    ground=[(x,floor_level(x,camera)) for x in range(-4,W+5,4)]
    if not front:
        reef=[(x,288+round(8*math.sin((x+camera*.24)/25)+
                          4*math.sin((x+camera*.24)/8))) for x in range(-4,W+5,4)]
        d.polygon(reef+[(W+4,H),(-4,H)],fill=rgbmix((11,42,56),(33,64,70),dawn))
        for x,y in reef[1:-1:3]:
            d.line([(x,y),(x-3,y-9),(x-2+2*math.sin(x+t),y-15)],fill=(20,54,65))
    edge=[(x,y+(15 if front else 0)) for x,y in ground]
    body=rgbmix((30,60,67),(83,84,67),dawn)
    if front:
        body=rgbmix(body,(7,19,37),.27)
    d.polygon(edge+[(W+4,H),(-4,H)],fill=body)
    for x,y,w,shade in SAND:
        x=round((x-camera*(.95 if front else .54))%310)-20
        if front and y>81:
            continue
        if not front and y>15:
            continue
        y+=floor_level(x,camera)+(15 if front else 0)
        color=rgbmix(body,(128,137,100),.09*shade) if shade else rgbmix(body,(5,23,39),.55)
        d.line((x,y,x+w,y),fill=color)
    if not front:
        d.line(ground,fill=rgbmix((59,93,92),(139,135,100),dawn))


def squid(im,t,cx,cy,scale,pitch,light,macro,burial):
    d=ImageDraw.Draw(im)
    c,s=math.cos(pitch),math.sin(pitch)
    pulse=1+.065*math.sin(t*5)
    phase=t*5.6
    focus=1-burial*.2
    def xy(x,y):
        return round(cx+scale*(x*c-y*s)),round(cy+scale*(x*s+y*c))
    def poly(points,fill,edge=None):
        d.polygon([xy(x,y) for x,y in points],fill=fill,outline=edge)
    def line(points,fill,width=1):
        d.line([xy(x,y) for x,y in points],fill=fill,width=width)

    # Paired rounded lateral fins undulate independently of the contracting mantle.
    for side in (-1,1):
        wave=math.sin(t*7+side*1.5)*7
        fin=[(-45,side*14),(-51,side*(24+wave*.3)),(-45,side*(36+wave*.7)),
             (-32,side*(44+wave)),(-17,side*(40+wave)),(-4,side*(30+wave*.7)),
             (2,side*18),(-21,side*18)]
        poly(fin,(82,95,119) if side<0 else (139,108,118),(38,45,72))
        for idx in range(8):
            line([(-43+idx*4,side*21),(-45+idx*5,side*(33+wave*.7))],
                 (160,129,136) if side>0 else (106,126,148))
        line(fin[1:7],(172,150,156) if side>0 else (129,154,167))

    # Eight short arms and two longer, fine feeding tentacles.
    for idx in range(10):
        root=(idx-4.5)*2.7
        length=(56 if idx in (2,7) else 32+idx%3*4)*focus
        trail=[]
        for j in range(12):
            u=j/11
            x=28+length*u
            y=root+u*(root*.68+8*math.sin(phase-3*u+idx*.7)) + burial*9*u
            trail.append((x,y))
        line(trail,(32,38,63),round(scale*6))
        line(trail,(104+idx*6,72+idx*4,89+idx*4),round(scale*(2 if idx in (2,7) else 4)))
        for j in range(2,9,2):
            dx,dy=trail[j]
            d.point(xy(dx,dy+1),fill=(204,173,158))

    shadow=(54,48,77)
    poly([(x,y*pulse) for x,y in MANTLE],(125,88,105),shadow)
    poly([(-53,-5),(-46,-19),(-36,-28),(-22,-33),(-6,-31),(12,-25),
          (20,-15),(9,-6),(-9,-1),(-24,3),(-38,4)],(171,124,128))
    poly([(-49,8),(-41,17),(-20,23),(2,19),(18,10),(23,5),(24,13),
          (14,24),(-3,31),(-23,29),(-42,22)],(90,68,99))
    poly([(-51,0),(-47,-16),(-35,-26),(-24,-28),(-32,-21),(-36,-11),(-46,0)],(207,153,138))
    for x,y,v in FLECKS:
        if ((x+14)/39)**2+((y+1)/32)**2 > .84:
            continue
        q=.5+.5*math.sin(t*2+x*.19+y*.22)
        color=(91+round(v*42),54+round(v*30),71+round(v*34)) if v>.43+.13*q else (179,133,136)
        if v>.81:
            line([(x,y*pulse),(x+2,y*pulse)],color)
        else:
            d.point(xy(x,y*pulse),fill=color)
    line([(-49,-20),(-39,-30),(-25,-34),(-12,-34)],(229,184,162))

    poly([(13,-16),(23,-18),(35,-14),(40,-6),(41,6),(36,14),(24,17),
          (15,12),(10,1)],(144,112,130),(57,48,79))
    for x,y,rad in ((30,-10,6),(28,7,9)):
        poly([(x-rad,y),(x-rad+2,y-rad+2),(x,y-rad),(x+rad-2,y-rad+2),
              (x+rad,y),(x+rad-3,y+rad-1),(x-3,y+rad-1)],(175,172,175),(53,57,79))
        poly([(x-4,y-2),(x-2,y-5),(x+3,y-4),(x+5,y-1),(x+4,y+4),(x,y+5),
              (x-4,y+2)],(16,30,47))
        d.rectangle([xy(x-2,y-3),xy(x-2,y-3)],fill=(237,232,218))
    if light>.05:
        glow=(round(80+83*light),round(153+73*light),round(157+67*light))
        for x,y in ((-12,17),(3,16)):
            poly([(x-9,y),(x-7,y-4),(x,y-5),(x+7,y-3),(x+8,y+1),(x+3,y+4),
                  (x-5,y+4)],glow,(73,130,145))
            line([(x-3,y),(x+4,y-1)],(224,255,224),max(1,round(scale)))
    if macro>.5:
        for i,(u,v,_) in enumerate(SPORES[:28]):
            x=-19+28*u+1.5*math.sin(t*8+i)
            y=10+10*v+math.cos(t*6+i)
            d.point(xy(x,y),fill=(202,255,213))
    return xy


@lru_cache(maxsize=None)
def font(path,size):
    return ImageFont.truetype(str(path),size)


def overlay(t, meta, scale, phase):
    screen=Image.new("RGBA",(W*scale,H*scale))
    d=ImageDraw.Draw(screen)
    def box(x,y,r,b,fill):
        d.rectangle(tuple(round(v*scale) for v in (x,y,r,b)),fill=fill)
    def text(x,y,msg,size,face,fill,anchor="lt",stroke=0):
        d.text((round(x*scale),round(y*scale)),msg,font=font(face,round(size*scale)),
               fill=fill,anchor=anchor,stroke_width=round(stroke*scale),stroke_fill=(4,12,24))
    box(18,52,135,70,(8,34,32,239))
    box(18,52,20.5,70,MINT)
    text(26,56,"BESTIARY 16-BIT",10.4,MONO_FONT,INK)
    text(237,56,"EP18",9,MONO_FONT,WARM,"rt")
    box(18,70,237,70.5,(100,147,149,140))
    box(18,70,18+219*t/meta["duration"],70.5,MINT)
    if phase==0:
        text(127,94,"MENYALA UNTUK",19,TITLE_FONT,INK,"mt",1)
        text(127,119,"BERSEMBUNYI?",22,TITLE_FONT,MINT,"mt",1)
    elif phase==1:
        text(127,96,"CUMI BOBTAIL",23,TITLE_FONT,WARM,"mt",1)
        text(127,126,"Euprymna scolopes",9.5,MONO_FONT,MINT,"mt",.5)
    else:
        title=("BAKTERI PENGHASIL CAHAYA" if phase<4 else "CAHAYA DARI BAWAH" if phase<5
               else "KAMUFLASE SILUET" if phase<7 else "FAJAR DI HAWAII")
        box(18,92,27,93,MINT)
        text(18,100,title,10,MONO_FONT,INK,stroke=.55)
    cue=next((caption for start,end,caption in meta["captions"] if start<=t<end),None)
    if cue:
        lines=cue.splitlines()
        top=326 if len(lines)>1 else 335
        box(18,top,237,top+(43 if len(lines)>1 else 25),(2,13,20,237))
        box(18,top,20,top+(43 if len(lines)>1 else 25),MINT)
        for j,line in enumerate(lines):
            text(127.5,top+5+j*17,line,14,CAPTION_FONT,(255,250,231),"mt",1)
    return screen


def scene(t, meta, factor):
    cues=meta["captions"]
    starts=[c[0] for c in cues]
    phase=max(i for i in range(10) if starts[i]<=t) if t>=starts[0] else 0
    macro=morph(t,starts[2]-.20,starts[2]+.45)-morph(t,starts[4]-.30,starts[4]+.33)
    look=morph(t,starts[5]-.05,starts[5]+.5)-morph(t,starts[7]-.43,starts[7]+.44)
    dawn=morph(t,starts[7]-.4,starts[8]+.7)
    bury=morph(t,starts[9]-.18,meta["duration"]-.21)
    dive=morph(t,starts[7]+.11,starts[9]+.38)
    glow=morph(t,.13,1.0)*(.78+macro*.2) + .13*math.sin(t*2.4)
    glow=max(0,glow*(1-dawn))
    reveal=morph(t,starts[6]-.23,starts[6]+.55)
    cx=118+11*math.sin(t*.51)-11*macro+19*dive
    cy=224+9*math.sin(t*1.8)+8*macro+54*dive+51*bury
    camera=(cx-122)*1.1
    im=ocean(t,dawn,cx,cy,glow,look)
    if look<.57:
        seabed(im,t,camera,dawn,False)
    particles(ImageDraw.Draw(im),t,camera)
    xy=squid(im,t,cx,cy,1.36+.54*macro-.17*dive,-.13+.13*math.sin(t*1.4)+.33*dive,
             glow,macro,bury)

    if look>.49:
        # Under-view comparison shows the effect on the silhouette, independent of the side-view sprite.
        d=ImageDraw.Draw(im)
        w=88
        for i,left in enumerate((29,150)):
            top=248
            d.rectangle((left,top,left+w,top+45),fill=(25,70,88),outline=(81,143,148))
            for y in range(top+1,top+45,3):
                col=round(42+(top+45-y)*.64)
                d.line((left+1,y,left+w-1,y),fill=(col//2,col,col+18))
            color=(6,19,32) if i==0 else rgbmix((6,19,32),(28,79,95),reveal)
            d.ellipse((left+11,top+14,left+61,top+28),fill=color)
            for arm in range(5):
                y=top+17+arm*2
                d.line([(left+53,y),(left+66,y-1),(left+74,y+(arm-2))],
                       fill=color,width=2)
            label="TANPA CAHAYA" if i==0 else "DENGAN CAHAYA"
            d.text((left+w//2,top+51),label,fill=(210,239,226),
                   font=font(MONO_FONT,8),anchor="mt")
    if t>=starts[8]-.1 and bury<.68:
        d=ImageDraw.Draw(im)
        px,py=xy(8,17)
        for i,(u,v,k) in enumerate(SPORES[:33]):
            flow=min(1.,max(0,(t-starts[8]-.42*u)/1.55))
            if 0<flow<1:
                x=px+flow*(16+35*u)
                y=py+flow*(6+24*v)+2*math.sin(t*5+i)
                d.point((round(x),round(y)),fill=rgbmix((142,224,198),(59,87,85),flow))
    if look<.57:
        seabed(im,t,camera,dawn,True)
    d=ImageDraw.Draw(im)
    if t>=starts[9]-.06:
        for i,(u,v,k) in enumerate(SPORES):
            age=(t-starts[9])-.53*u
            if 0<age<1.13:
                x=cx+(v-.49)*(35+age*138)
                y=floor_level(x,camera)+14-age*(18+48*k)+age**2*38
                d.line((round(x),round(y),round(x)+int(k*4),round(y)),
                       fill=rgbmix((165,155,109),(75,78,67),age/1.13))
    particles(d,t,camera,near=True)
    im=im.resize((W*factor,H*factor),Image.Resampling.NEAREST)
    im.alpha_composite(overlay(t,meta,factor,phase))
    return im.convert("RGB")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--timing",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stills",action="store_true")
    args=parser.parse_args()
    data=json.loads(args.timing.read_text())
    if args.stills:
        montage=Image.new("RGB",(W*5,H*2))
        for i,(start,end,_) in enumerate(data["captions"]):
            montage.paste(scene((start+end)/2,data,1),(W*(i%5),H*(i//5)))
        montage.save(args.output)
        return
    command=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format",
             "rgb24","-video_size","1080x1920","-framerate","30","-i","-","-an","-c:v",
             "libx264","-threads","3","-preset","veryfast","-crf","16","-pix_fmt","yuv420p",
             "-movflags","+faststart","-color_primaries","bt709","-color_trc","bt709",
             "-colorspace","bt709",str(args.output)]
    with subprocess.Popen(command,stdin=subprocess.PIPE) as proc:
        try:
            for i in range(round(data["duration"]*FPS)):
                proc.stdin.write(scene(i/FPS,data,4).tobytes())
        finally:
            proc.stdin.close()
        if proc.wait():
            raise RuntimeError("FFmpeg video encoding failed")


if __name__=="__main__":
    main()
