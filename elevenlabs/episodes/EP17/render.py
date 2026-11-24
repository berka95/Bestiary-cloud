"""Render original pixel sprites and underwater animation for BESTIARY EP17."""
import argparse
import json
import math
import random
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
W, H = 270, 480
FPS = 30
INK = (208, 238, 226)
MINT = (144, 236, 204)
WARM = (255, 233, 186)
FONT_DIR = Path("/usr/share/fonts/truetype")
TITLE_FONT = FONT_DIR / "dejavu/DejaVuSansCondensed-Bold.ttf"
MONO_FONT = FONT_DIR / "dejavu/DejaVuSansMono-Bold.ttf"
CAPTION_FONT = FONT_DIR / "liberation2/LiberationSans-Bold.ttf"
if not CAPTION_FONT.exists():
    CAPTION_FONT = FONT_DIR / "liberation/LiberationSans-Bold.ttf"
if not TITLE_FONT.exists():
    TITLE_FONT = FONT_DIR / "dejavu/DejaVuSans-Bold.ttf"

DOME = [(4,4),(0,-5),(0,-18),(4,-28),(11,-38),(22,-46),(34,-50),
        (49,-50),(61,-46),(70,-40),(78,-31),(82,-21),(82,-12),(77,-4),
        (69,1),(60,4),(43,8),(26,9),(13,8)]
BODY = [(-68,0),(-58,-1),(-43,-8),(-25,-14),(-4,-19),(6,-20),
        (16,-14),(21,-6),(32,-3),(49,-6),(62,-10),(74,-14),(81,-13),
        (83,-9),(80,-5),(84,-2),(82,3),(74,7),(63,12),(46,20),
        (23,26),(1,27),(-22,22),(-40,15),(-55,10),(-68,9)]
RNG = random.Random(1717)
SCALES = [(x + RNG.choice((0,1)), y, RNG.random()) for y in range(-16,29,3)
          for x in range(-66,74,4)]
MOTES = [[(RNG.uniform(0, W), RNG.uniform(0, H), RNG.uniform(0, 6.28),
           RNG.random()) for _ in range(n)] for n in (102, 49, 15)]
SILT = [(RNG.uniform(0,W), RNG.uniform(0,H), RNG.random()) for _ in range(10)]
YY, XX = np.mgrid[:H, :W].astype(np.float32)
DITHER = np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]],
                  dtype=np.float32)[(YY.astype(int) % 4), (XX.astype(int) % 4)] / 16
VIGNETTE = np.clip(1 - ((XX-135)/182)**2*.59 - ((YY-217)/290)**2*.43, .34, 1)


def smooth(x):
    x = max(0., min(1., x))
    return x*x*(3-2*x)


def morph(t, start, end):
    return smooth((t-start)/(end-start))


def stroke(d, points, color, width=1):
    d.line(points, fill=color, width=width)


def water(t, camera, scan):
    cx = 147 + 12*math.sin(t*.21) - camera*.27
    top = np.exp(-((XX-cx)/106)**2 - ((YY-134)/169)**2)
    haze = np.exp(-((XX-(107+11*math.sin(t*.18)))/134)**2 - ((YY-287)/106)**2)
    ray = np.zeros((H,W), dtype=np.float32)
    for origin, slope, width in ((211,.43,13),(183,.37,7),(235,.47,22),(143,.31,8)):
        beam_x = origin - (YY-43)*slope + 4*math.sin(t*.65+origin)
        ray += np.exp(-((XX-beam_x)/width)**2) * np.clip(1-YY/330,0,1)
    energy = (top*.65 + haze*.23 + ray*.16 +
              scan * np.exp(-((XX-159)/72)**2-((YY-216)/80)**2)*.13)*VIGNETTE
    rgb = np.stack([5+energy*22, 17+energy*65, 30+energy*75], axis=-1)
    rgb = np.floor(rgb/3+DITHER[...,None])*3
    return Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")


def particles(d, t, camera, near=False):
    for depth in ((2,) if near else (0,1)):
        for x, y, phase, strength in MOTES[depth]:
            xx = round((x + t*(2+depth*2.7) + 4*math.sin(t*.55+phase)
                        - camera*(.11+depth*.13)) % W)
            yy = round((y + t*(.7+depth*.65)+2*math.cos(t*.9+phase)) % H)
            v = int((13+18*depth+strength*20)*(.82+.18*math.sin(phase+t*1.6)))
            d.point((xx,yy), fill=(v//2, v, v+12))
            if depth==2 and strength>.49:
                d.line((xx-1,yy,xx+2,yy),fill=(v//2,v,v+13))
                d.point((xx,yy-1), fill=(v//2+8,v+12,v+15))
    if not near:
        for x,y,k in SILT:
            xx=round((x+t*(2+k)-camera*.19)%W)
            yy=round((y+math.sin(t*.6+k*8)*5)%H)
            d.line((xx-2,yy+2,xx,yy,xx+2,yy-1), fill=(13,46,59))
    else:
        # Nearby suspended organisms cross much faster than the distant marine snow.
        for offset, base_y, speed in ((-91,114,17),(81,299,21),(212,398,14)):
            x = (offset + t*speed - camera*.67) % (W+36) - 18
            y = base_y - t*2.1 + math.sin(t*1.1+offset)*6
            x,y=round(x),round(y)
            d.polygon([(x-3,y),(x,y-2),(x+5,y-1),(x+8,y+1),(x+3,y+2),(x-1,y+1)],
                      fill=(8,26,40))
            d.line((x,y-2,x+5,y-1), fill=(20,47,60))


def show_prey(d, x, y, t, opacity):
    if opacity < .04:
        return
    x,y=round(x),round(y)
    edge = (int(25+83*opacity),int(66+110*opacity),int(73+67*opacity))
    hot = (int(50+137*opacity),int(105+110*opacity),int(91+70*opacity))
    d.polygon([(x-2,y-1),(x+1,y-2),(x+3,y),(x+2,y+2),(x-1,y+2)], fill=edge)
    d.point((x+1,y),fill=hot)
    for offset in (-1,1):
        spread=round(2+2*math.sin(t*11+offset))
        stroke(d,[(x,y+offset),(x-3,y+offset*2),(x-6,y+offset*(3+spread))],edge)


def fish(im, t, cx, cy, z, pitch, rotation, fin_energy, jaw, glint):
    cos_pitch, sin_pitch = math.cos(pitch), math.sin(pitch)

    def p(x, y):
        return (round(cx+z*(x*cos_pitch-y*sin_pitch)),
                round(cy+z*(x*sin_pitch+y*cos_pitch)))

    def poly(d, points, color, outline=None):
        d.polygon([p(x,y) for x,y in points], fill=color, outline=outline)

    def line(d, points, color, width=1):
        stroke(d,[p(x,y) for x,y in points],color,width)

    d = ImageDraw.Draw(im)
    phase=t*5.25
    tail=math.sin(phase)*(.70+fin_energy*.65)
    tip=math.cos(phase)*3.5
    top_tip=(-99-tail*7,-24+tip)
    bottom_tip=(-95+tail*7,30+tip)
    tail_shape=[(-58,0),(-77,-1),(-89,-10+tip*.5),top_tip,(-103,-16+tip),
                (-96,1+tip),(-93,6+tip),(-101,18+tip),bottom_tip,
                (-86,22+tip*.6),(-76,13),(-58,9)]
    poly(d,tail_shape,(25,48,60),(14,29,42))
    poly(d,[(-66,3),(-83,0),top_tip,(-98,-12+tip),(-89,4+tip),(-78,9)],
         (43,73,83))
    poly(d,[(-77,7),(-93,12+tip),bottom_tip,(-85,21+tip*.6),(-75,12)],
         (23,40,55))
    for end_x,end_y in [top_tip,(-97,-13+tip),(-96,-6+tip),(-94,5+tip),
                        (-95,15+tip),bottom_tip]:
        line(d,[(-72,6),(-83,5+tip*.3),(end_x,end_y)],(52,76,81))
    line(d,[top_tip,(-89,-10+tip*.5),(-77,-1)],(82,121,125))
    wob=math.sin(phase+1.15)*2
    dorsal=[(-52,-8),(-36,-14),(-26,-31+wob),(-17,-34+wob),
             (-11,-30+wob),(-5,-16),(4,-12)]
    poly(d,dorsal,(27,52,66),(12,32,45))
    for j in range(6):
        line(d,[(-36+4*j,-14),(-28+2.8*j,-29+wob-j*.35)],(50+j*2,80+j*2,90+j*2))
    line(d,[(-52,-8),(-36,-14),(-26,-31+wob),(-17,-34+wob)],(71,116,119))
    poly(d,[(-33,12),(-19,18),(-23,38+wob),(-30,35+wob),(-40,16)],
         (23,44,57),(16,31,43))
    for j in range(4):
        line(d,[(-37+j*4,15),(-27+j,34+wob+j*.6)],(45,74,83))
    poly(d,BODY,(32,47,60),(11,23,35))
    poly(d,[(-66,1),(-47,-5),(-25,-12),(-2,-18),(7,-18),(21,-6),
            (7,-3),(-18,-1),(-43,4),(-65,6)],(48,73,83))
    poly(d,[(-52,8),(-29,10),(8,13),(42,10),(63,6),(77,1),(81,3),
            (64,10),(46,18),(23,25),(1,26),(-23,21),(-40,14)],(19,31,45))
    poly(d,[(-34,1),(-8,-5),(11,-4),(32,0),(44,5),(16,15),(-13,14)],(38,58,70))
    for x,y,q in SCALES:
        if x<-58:
            lo, hi = 1, 8
        elif x < -15:
            lo, hi = -5 + (-42-x)*.25, 16+(x+34)*.27
        elif x < 23:
            lo, hi = -8,23
        else:
            lo, hi = 1,23-(x-24)*.37
        if lo<y<hi and q>.26:
            v=int(19 + (1-abs(y-4)/23)*12 + q*24)
            line(d,[(x,y),(x+1,y-1),(x+2,y)],(v,v+12,v+23))
            if q>.85:
                d.point(p(x+1,y-1),fill=(v+12,v+26,v+34))
    line(d,[(-64,0),(-48,-4),(-27,-12),(-3,-17),(4,-18)],(84,125,127))
    line(d,[(-53,8),(-31,6),(-15,7),(1,5),(23,6)],(48,78,85))
    gill=math.sin(t*4.7)*.9
    line(d,[(9,-8),(16+gill,0),(17+gill,10),(13+gill,20),(9,23)],(15,30,42),2)
    line(d,[(10,-8),(17+gill,0),(18+gill,9),(14+gill,20)],(59,86,93))
    sweep=math.sin(t*7.1+.4)*(4+fin_energy*5)
    poly(d,[(16,8),(12,18),(5,27+sweep),(-18,32+sweep),
            (-15,27+sweep),(-3,14),(9,8)],(27,60,70),(14,37,48))
    for j in range(7):
        line(d,[(12-j*.5,8+j*.5),(-18+j*3.4,31+sweep-j*.7)],
             (43+j*2,78+j*2,88+j*2))
    line(d,[(11,8),(-3,14),(-15,27+sweep),(-18,32+sweep)],(76,119,123))
    # The shield transmits the surrounding water and tints the tissue beneath it.
    shield = Image.new("RGBA", im.size)
    sd = ImageDraw.Draw(shield)
    poly(sd,DOME,(39,136,145,71),(95,185,181,228))
    poly(sd,[(1,-10),(5,-26),(13,-37),(23,-44),(35,-48),(49,-49),(61,-44),
             (71,-36),(73,-31),(61,-37),(43,-41),(28,-38),(13,-29),(6,-13)],
         (66,195,193,55))
    poly(sd,[(1,-8),(6,1),(17,5),(32,6),(54,2),(71,-5),(79,-15),(80,-9),
             (70,1),(59,5),(43,9),(21,10),(10,7)],(29,100,115,163))
    poly(sd,[(11,-4),(17,-13),(29,-9),(34,-14),(44,-10),(54,-15),(63,-11),
             (59,-5),(44,0),(20,4)],(90,121,108,130))
    im.alpha_composite(shield)
    d = ImageDraw.Draw(im)

    def eye(base_x, base_y, size, dark):
        angle = rotation*1.43+.04
        ax,ay=math.sin(angle),-math.cos(angle)
        lx,ly=math.cos(angle),math.sin(angle)

        def ep(u,v):
            return (base_x+(lx*u+ax*v)*size,base_y+(ly*u+ay*v)*size)

        def e_poly(coords, c, border=None):
            poly(d,[ep(*part) for part in coords],c,border)

        def e_line(coords, c):
            line(d,[ep(*part) for part in coords],c)

        e_poly([(-7,-3),(6,-3),(9,4),(11,12),(10,20),(5,23),(-5,23),
                (-10,19),(-11,12),(-9,4)],(38,76,48),(20,53,39))
        e_poly([(3,-2),(8,4),(10,13),(8,18),(4,18),(3,9)],(83,120,58))
        e_poly([(-6,-3),(-3,-1),(-3,9),(-7,13),(-9,10)],(54,98,55))
        e_poly([(-11,13),(-11,17),(-8,21),(-4,23),(4,23),(8,21),(11,17),
                (11,13),(8,10),(4,9),(-4,9),(-8,10)],
               (91,139,52) if dark else (157,210,58),(30,71,36))
        e_poly([(-8,14),(-7,18),(-3,21),(4,21),(8,18),(9,14),(5,12),(-4,12)],
               (127,169,61) if dark else (196,230,82))
        e_poly([(-4,15),(-3,17),(0,19),(5,18),(6,16),(3,14),(-1,14)],
               (59,107,50) if dark else (96,152,44))
        e_line([(-7,17),(-4,20),(0,21)],(191,228,109) if dark else (233,249,150))
        d.point(p(*ep(-4,19)),fill=(237,255,187))
        d.point(p(*ep(-5,18)),fill=(214,250,124))

    eye(54,-12,.75,True)
    eye(28,-9,1,False)
    glass = Image.new("RGBA",im.size)
    gd=ImageDraw.Draw(glass)
    line(gd,[(2,-19),(7,-31),(14,-39),(23,-45),(34,-49),(49,-49),(59,-45)],
         (133,215,205,195))
    line(gd,[(10,-36),(21,-44),(32,-47),(46,-47)],(192,244,217,222),2)
    line(gd,[(25,-46),(34,-48),(39,-48)],(224,252,221,248))
    line(gd,[(59,-44),(68,-39),(76,-31),(80,-23)],(125,232,213,194))
    line(gd,[(7,-22),(8,-28),(14,-33),(19,-34)],(111,207,193,111))
    poly(gd,[(54,-44),(60,-41),(40,-24),(36,-25),(44,-34)],(143,219,207,25))
    poly(gd,[(66,-41),(70,-37),(57,-26),(51,-25),(57,-32)],(154,220,203,38))
    line(gd,[(3,-7),(11,2),(25,6),(39,6),(50,4)],(102,203,184,115))
    if glint>.03:
        stretch=12*glint
        line(gd,[(42-stretch,-46),(42,-47),(42+stretch,-46)],
             (228,255,235,round(170*glint)))
    im.alpha_composite(glass)
    d=ImageDraw.Draw(im)
    poly(d,[(63,-2),(70,-10),(77,-14),(81,-13),(84,-9),(81,-4),
             (84,0),(83,4),(76,7),(69,8),(64,4)],(47,72,77),(19,42,52))
    line(d,[(70,-9),(76,-12),(80,-11),(82,-8)],(105,153,147))
    for nx,ny,scale in [(72,-5,1),(79,-7,.68)]:
        poly(d,[(nx-2*scale,ny-1),(nx,ny-3*scale),(nx+2*scale,ny-2*scale),
                (nx+2*scale,ny),(nx,ny+1),(nx-2*scale,ny)],(12,30,38))
        line(d,[(nx-2*scale,ny-1),(nx,ny-3*scale)],(83,126,125))
    poly(d,[(74,2),(80,0),(84,0),(83,3+jaw),(78,5+jaw),(73,6)],
         (29,49,55),(17,28,35))
    line(d,[(76,2),(82,1),(84,0)],(10,21,29))
    if jaw>1.5:
        poly(d,[(78,2),(84,0),(83,2+jaw),(79,3+jaw)],(7,19,23))
    return p


def dashed(d, start, end, color, spacing=6):
    length = math.dist(start,end)
    if length < 1:
        return
    for i in range(0,round(length),spacing):
        a=i/length
        b=min(1,(i+2)/length)
        stroke(d,[(round(start[0]+(end[0]-start[0])*a),round(start[1]+(end[1]-start[1])*a)),
                  (round(start[0]+(end[0]-start[0])*b),round(start[1]+(end[1]-start[1])*b))],color)


def scene(t, timing):
    caps=timing["captions"]
    identify = caps[1][0]
    dome = caps[2][0]
    tubes = caps[3][0]
    hunt = caps[4][0]
    follow = caps[6][0]
    turn = caps[7][0]
    nares = caps[8][0]
    reveal = caps[9][0]
    final = timing["duration"]
    enter = morph(t,0,.9)
    macro = morph(t,dome-.32,dome+.66) - morph(t,hunt-.42,hunt+.22)
    tracking = morph(t,follow+.10,turn+.87)
    nose = morph(t,nares-.35,nares+.42)
    loop = morph(t,final-.55,final+.07)
    lens = morph(t,tubes-.1,tubes+.55)-morph(t,hunt-.4,hunt+.1)
    settle = morph(t,hunt+.05,hunt+.78)
    z = 1.02 + .12*enter + .61*macro - .08*settle + .94*nose
    z = z*(1-loop) + 1.03*loop
    cx = 111 + 10*enter - macro*73 - nose*107 + 4*math.sin(t*.77)
    cx = cx*(1-loop) + 110*loop
    cy = 228 - 6*enter + 11*macro + 8*nose + 3*math.sin(t*1.55)
    pitch = -.08 + .045*math.sin(t*1.6) - .09*tracking + .07*nose
    rotation=tracking*(1-loop)
    jaw=4*max(0,1-abs(t-(nares-.52))/.34)
    im=water(t,cx-120,macro)
    d=ImageDraw.Draw(im)
    particles(d,t,cx-120)
    appearance=morph(t,hunt-.07,hunt+.7) * (1-morph(t,nares-.57,nares-.42))
    p=fish(im,t,cx,cy,z,pitch,rotation,tracking,jaw,enter*(1-morph(t,1.1,1.8))+.45*macro)
    d=ImageDraw.Draw(im)
    particles(d,t,cx-120,near=True)

    strike=morph(t,nares-.99,nares-.51)
    mouth_x,mouth_y=p(86,0)
    px=(163+42*tracking+3*math.sin(t*2.2))*(1-strike)+mouth_x*strike
    py=(146+38*tracking+2*math.sin(t*2.7))*(1-strike)+mouth_y*strike
    show_prey(d,px,py,t,appearance)
    if appearance>.28:
        origin=p(29+14*tracking,-29+16*tracking)
        if tracking<.17 or tracking>.76:
            ink=(53,108,105) if tracking<.76 else (94,171,142)
            dashed(d,origin,(px,py),ink,6)
        px,py=round(px),round(py)
        offset = 7 + round(2*math.sin(t*4))
        for dx in [-1,1]:
            for dy in [-1,1]:
                stroke(d,[(px+dx*(offset-3),py+dy*offset),(px+dx*offset,py+dy*offset),
                          (px+dx*offset,py+dy*(offset-3))],(123,207,174))
    if lens>.45:
        a,b=p(29,-25)
        dashed(d,(a,b-6),(a,131),(86,162,146))
        stroke(d,[(a-10,131),(a+10,131)],MINT)
    if nose>.64 and loop<.25:
        a,b=p(73,-6)
        color=MINT if t>=reveal else (89,165,149)
        r=14
        for dx in (-1,1):
            for dy in (-1,1):
                stroke(d,[(a+dx*(r-5),b+dy*r),(a+dx*r,b+dy*r),(a+dx*r,b+dy*(r-5))],color)
        dashed(d,(a,b-r),(a,142),color)
        stroke(d,[(a-9,142),(a+9,142)],color)
    return im.convert("RGB"), (identify,dome,tubes,hunt,follow,turn,nares,reveal)


def overlay(t, timing, beats, factor):
    identify,dome,tubes,hunt,follow,turn,nares,reveal=beats
    im = Image.new("RGBA",(W*factor,H*factor))
    d = ImageDraw.Draw(im)
    left, right = 18, 237

    def coords(items):
        return tuple(round(v*factor) for v in items)

    def box(x1,y1,x2,y2,c):
        d.rectangle(coords((x1,y1,x2,y2)),fill=c)

    def text(x,y,words,font,size,color,anchor="lt",stroke_width=0):
        d.text(coords((x,y)),words,font=font_at(str(font),round(size*factor)),
               fill=color,anchor=anchor,stroke_width=round(stroke_width*factor),
               stroke_fill=(2,9,17,255))

    box(left,52,left+117,70,(8,34,32,239))
    box(left,52,left+2.5,70,MINT)
    text(left+8,56,"BESTIARY 16-BIT",MONO_FONT,10.4,INK)
    text(right,56,"EP17",MONO_FONT,9,WARM,"rt")
    box(left,70,right,70.28,(111,174,174,103))
    box(left,70,left+(right-left)*min(1,t/timing["duration"]),70.28,(146,203,174,208))
    center = (left+right)/2
    if t < identify:
        text(center,93,"BISA LIHAT",TITLE_FONT,19,INK,"mt",1)
        text(center,117,"LEWAT DAHI?",TITLE_FONT,22,MINT,"mt",1)
    elif t < dome:
        text(center,100,"BARRELEYE",TITLE_FONT,23,WARM,"mt",1)
        text(center,130,"Macropinna microstoma",MONO_FONT,8.2,MINT,"mt",.5)
    else:
        label = ("KUBAH TRANSPARAN" if t<tubes else "MATA TABUNG" if t<hunt else
                 "MENCARI MANGSA" if t<follow else "MELACAK MANGSA" if t<turn else
                 "MATA BERPUTAR" if t<nares else "DUA TITIK DI ATAS MULUT" if t<reveal
                 else "ORGAN PENCIUMAN")
        box(left,91,left+8,91.5,MINT)
        text(left,99,label,MONO_FONT,10.3,INK,"lt",.55)
    cap = next((words for start,end,words in timing["captions"] if start<=t<end), None)
    if cap:
        rows=cap.splitlines()
        top = 326 if len(rows)>1 else 335
        bottom = top+(43 if len(rows)>1 else 25)
        box(left,top,right,bottom,(2,13,20,237))
        box(left,top,left+2,bottom,MINT)
        y=top+5
        for row in rows:
            text(center,y,row,CAPTION_FONT,15,(255,250,231),"mt",1.15)
            y+=17
    return im


@lru_cache(maxsize=None)
def font_at(path, size):
    return ImageFont.truetype(path,size)


def frame(t, timing, factor):
    canvas, beats = scene(t,timing)
    canvas = canvas.resize((W*factor,H*factor),Image.Resampling.NEAREST).convert("RGBA")
    canvas.alpha_composite(overlay(t,timing,beats,factor))
    return canvas.convert("RGB")


def render(timing, output, factor):
    proc = subprocess.Popen([
        "ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo",
        "-pixel_format","rgb24","-video_size",f"{W*factor}x{H*factor}",
        "-framerate",str(FPS),"-i","-","-an","-c:v","libx264","-threads","3",
        "-preset","veryfast","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",
        "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709",str(output)
    ],stdin=subprocess.PIPE)
    try:
        for index in range(round(timing["duration"]*FPS)):
            proc.stdin.write(frame(index/FPS,timing,factor).tobytes())
    finally:
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError("FFmpeg video encoding failed")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--timing",type=Path,default=BASE/"episode.json")
    parser.add_argument("--size",type=int,choices=(1,2,4),default=4)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stills",action="store_true")
    args=parser.parse_args()
    timing=json.loads(args.timing.read_text())
    if args.stills:
        strip=Image.new("RGB",(270*5,480*2))
        for i,(start,end,_) in enumerate(timing["captions"]):
            strip.paste(frame((start+end)/2,timing,1),(270*(i%5),480*(i//5)))
        strip.save(args.output)
    else:
        render(timing,args.output,args.size)
