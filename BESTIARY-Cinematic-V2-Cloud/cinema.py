"""Pixel-stage renderer and original score for BESTIARY Cinematic V2."""
import hashlib
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 270, 480, 30
MAC_FONTS = Path("/System/Library/Fonts/Supplemental")
LINUX_FONTS = Path("/usr/share/fonts/truetype/liberation")
MONO = MAC_FONTS / "Courier New Bold.ttf" if MAC_FONTS.exists() else LINUX_FONTS / "LiberationMono-Bold.ttf"
BOLD = MAC_FONTS / "Arial Bold.ttf" if MAC_FONTS.exists() else LINUX_FONTS / "LiberationSans-Bold.ttf"


def font(size, face=MONO):
    return ImageFont.truetype(str(face), size)


def clamp(value):
    return min(1, max(0, value))


def ease(value):
    value = clamp(value)
    return value * value * (3 - 2 * value)


def ellipse(draw, x, y, rx, ry, fill, outline=None):
    draw.ellipse((round(x-rx), round(y-ry), round(x+rx), round(y+ry)), fill, outline)


def plus(x, y, vector):
    return x + vector[0], y + vector[1]


class Stage:
    def __init__(self, spec, lang):
        self.spec = spec
        self.lang = lang
        seed = int.from_bytes(hashlib.sha256(spec["name"].encode()).digest()[:8])
        rng = random.Random(seed)
        self.air = [(rng.randrange(480), rng.randrange(350), rng.random()) for _ in range(60)]
        palette = {
            "forest": ("#0b1d24", "#122f30", "#204039", "#1c3027", "#426246"),
            "desert": ("#241a27", "#47313b", "#624446", "#3b2931", "#a0664e"),
            "water": ("#091e36", "#15364a", "#20536b", "#183243", "#397782"),
            "sky": ("#172238", "#223452", "#395371", "#28394d", "#608898"),
        }
        dark, far, mid, soil, moss = palette[spec["habitat"]]
        self.planes = []
        backdrop = Image.new("RGB", (480, 580), dark)
        d = ImageDraw.Draw(backdrop)
        for y in range(580):
            if y % 8 == 0:
                a, b = [tuple(bytes.fromhex(c[1:])) for c in (dark, far)]
                strength = .85 * math.exp(-((y-200)/150)**2)
                color = tuple(int(u + (v-u)*strength) for u,v in zip(a,b))
                d.rectangle((0,y,480,y+7), fill=color)
        glow = Image.new("RGBA", backdrop.size)
        light_draw = ImageDraw.Draw(glow)
        for i in range(8):
            x=160+i*13
            light_draw.polygon([(x,0),(x+6,0),(x+156,350),(x+132,350)],(200,223,153,7+i))
        backdrop.paste(glow,(0,0),glow)
        self.planes.append((backdrop, .22))
        for depth, color, count in [(.45, far, 26), (.70, mid, 18)]:
            layer = Image.new("RGBA", backdrop.size)
            d = ImageDraw.Draw(layer)
            for _ in range(count):
                x, y, r = rng.randrange(480), rng.randrange(95,365), rng.randrange(8,30)
                if spec["habitat"] == "forest":
                    d.polygon([(x-r,0),(x,0),(x+r,390),(x,390)], color)
                    ellipse(d,x,y,r*2,r*.6,color)
                    for _ in range(10):
                        yy=rng.randrange(22,325)
                        xx=x-r+int(r*yy/390)+rng.randrange(0,r)
                        d.line((xx,yy,xx+1,yy+rng.randrange(4,24)),dark if depth<.5 else far,1)
                else:
                    d.polygon([(x-r*3,390),(x,y),(x+r*3,390)], color)
            self.planes.append((layer, depth))
        ground = Image.new("RGBA", backdrop.size)
        d = ImageDraw.Draw(ground)
        d.polygon([(0,332),(80,321),(180,330),(280,319),(392,322),(480,335),(480,580),(0,580)], soil)
        for _ in range(2200):
            x, y, n = rng.randrange(480), rng.randrange(335,580), rng.randrange(1,10)
            d.rectangle((x,y,x+n,y+rng.randrange(1,4)), fill=rng.choice([dark, far, mid, moss, soil]))
        for _ in range(120):
            x, y = rng.randrange(480), rng.randrange(322,361)
            ellipse(d,x,y,rng.randrange(3,12),rng.randrange(1,4),moss)
        self.planes.append((ground, 1))
        self.foliage = Image.new("RGBA", backdrop.size)
        d = ImageDraw.Draw(self.foliage)
        for _ in range(85):
            x, y, r = rng.randrange(480), rng.randrange(455,580), rng.randrange(8,26)
            d.polygon([(x-r,y+r),(x,y-r),(x+r,y),(x+r*2,y+r)], rng.choice([dark, far, mid]))
        if spec["habitat"] == "forest":
            for x, y, side in [(108,452,1),(371,464,-1),(96,360,1),(395,352,-1)]:
                d.line([(x,y+80),(x+side*9,y+44),(x+side*31,y)],"#142b27",3)
                for j in range(6):
                    stem=(x+side*j*4,y+56-j*9)
                    tip=(stem[0]+side*(19+(j%3)*5),stem[1]-14)
                    d.polygon([stem,(tip[0]-side*4,tip[1]+3),tip,
                               (tip[0]+side*4,tip[1]+11)],"#204038")
                    d.line([stem,tip],"#385649",1)
        self.label = font(11)
        self.title = font(23)
        self.vignette = Image.new("RGBA", (W,H))
        pixels = self.vignette.load()
        for y in range(H):
            for x in range(W):
                distance = ((x-W/2)/(W*.68))**2 + ((y-H*.48)/(H*.67))**2
                pixels[x,y] = (4,10,17,int(132*clamp(distance-.22)))

    def animal(self, d, x, y, t, energy):
        s = self.spec["rig"]
        kind, primary, light = s["kind"], s["color"], s["light"]
        ink = "#171822"
        phase = t * (7 + 12*energy)
        bob = math.sin(phase)*1.5
        y += bob
        if kind == "worm":
            points = [(x-i*8,y+math.sin(i*.6+phase)*2+i*.13) for i in range(13)]
            for i,(px,py) in enumerate(points):
                swing = math.sin(phase+i*.9)*4
                d.line([(px,py+3),(px-2,py+12),(px+swing,py+17-abs(swing)/2)], ink, 5)
                d.line([(px,py+3),(px-2,py+11),(px+swing,py+16-abs(swing)/2)], primary, 3)
            for i,(px,py) in reversed(list(enumerate(points))):
                radius = max(4, 11-i*.40)
                ellipse(d,px,py,radius+3,radius,primary,ink)
                ellipse(d,px,py-3,radius-2,max(2,radius*.45),light)
                d.point((round(px-3),round(py-4)),fill="#ffe3a0")
            for a in (-1,1):
                tip = (x+17+a*6,y-22+math.sin(phase*.6+a)*4)
                d.line([(x+2,y-5),(x+8+a*3,y-14),tip],ink,4)
                d.line([(x+2,y-5),(x+8+a*3,y-14),tip],light,2)
        elif kind == "snake":
            points = [(x-i*4,y+math.sin(i*.33+phase)*7+i*.11) for i in range(27)]
            d.line(points,ink,13)
            d.line(points,primary,10)
            d.line([(px,py-2) for px,py in points],light,3)
            ellipse(d,x,y,13,7,primary,ink)
            d.line((x+10,y+2,x+17+math.sin(phase)*3,y+1),"#f58b88",2)
        else:
            tail = math.sin(phase)*8
            d.polygon([(x-26,y),(x-65,y+tail-5),(x-58,y+tail+5),(x-20,y+9)],primary,ink)
            if kind == "quad":
                for i in range(s["legs"]):
                    offset = -8-(i//2)*max(4,39/(s["legs"]/2))
                    swing = math.sin(phase+(i%2)*math.pi+i*.45)*6
                    d.line([(x+offset,y+6),(x+offset+3,y+14),(x+offset+swing,y+20-abs(swing)*.5)],ink,5)
                    d.line([(x+offset,y+6),(x+offset+3,y+14),(x+offset+swing,y+19-abs(swing)*.5)],primary,3)
            else:
                flap = math.sin(phase)*17
                d.polygon([(x-14,y-3),(x-45,y-17-flap),(x-60,y-10-flap),(x-32,y+7)],light,ink)
                if kind == "fish":
                    d.polygon([(x-52,y),(x-70,y-13+tail),(x-70,y+13+tail)],primary,ink)
            ellipse(d,x-25,y,32,s["bulk"],primary,ink)
            ellipse(d,x-23,y-4,23,max(3,s["bulk"]//3),light)
            ellipse(d,x+3,y-3,13,10,primary,ink)
            if kind == "wing":
                d.polygon([(x+10,y-6),(x+25,y-2),(x+11,y+2)],"#e8ac6b",ink)
        ellipse(d,x+6,y-3,2,2,ink)
        d.point((round(x+6),round(y-4)), "#fff2be")

    def secondary(self, d, x, y, t, stuck):
        if not self.spec["target"]:
            return
        for i in range(6):
            px = x + i%3*4-5
            sign = -1 if i<3 else 1
            d.line([(px,y),(px-4,y+6*sign),(px-4+4*math.sin(t*27+i),y+10*sign)],"#a3ca88",1)
        ellipse(d,x,y,9,5,"#26382b","#0b171a")
        ellipse(d,x-1,y-2,6,2,"#a3ca88")
        ellipse(d,x+7,y,4,3,"#527a5c")
        if stuck:
            for i in range(7):
                px = x-10+i*3
                d.line([(px,y-8),(x+10-i,y+8)],"#65ecbd",1)

    def frame(self, t, marks, duration, cover=False):
        reveal, action, payoff, endcard = marks
        windup = ease((t-action+.65)/.60) * (1-ease((t-action)/.40))
        snap = math.exp(-max(0,t-action)*9) if t>=action else 0
        track = 9*math.sin(t*.42)+20*ease(t/3)
        lift = 4*math.sin(t*.7)+12*ease((t-action+.5)/.8)-9*ease((t-payoff)/1.4)
        shake = 7*math.sin((t-action)*73)*snap
        zoom = 1.04+.22*ease((t-reveal)/3)+.17*ease((t-action+.35)/.55)-.17*ease((t-payoff)/2)
        im = Image.new("RGBA",(W,H))
        for plane,depth in self.planes:
            ox = int(98+track*depth+shake*depth)
            oy = int(37+lift*depth)
            im.alpha_composite(plane.crop((ox,oy,ox+W,oy+H)).convert("RGBA"))
        d = ImageDraw.Draw(im)
        for i,(x,y,a) in enumerate(self.air):
            px = int((x-t*(1+a*5)-track*.4)%W)
            py = int((y-t*(1+a*7))%350)
            d.rectangle((px,py,px+(a>.85),py+(a>.85)),fill=("#2b605b","#52907e","#b7bc87")[int(a*3)])
        f = self.spec["action"]
        moving = self.spec["rig"]["kind"] in ("wing","fish")
        target_x = 220 - 34*ease(t/2.3)
        target_y = (216 if moving else 282) + math.sin(t*15)*(3 if t<action else 1)
        hide = ease((t-.35)/max(.6,reveal))
        x = -18 + 112*hide + 19*ease((t-reveal)/max(1,action-reveal)) - 7*windup
        if f=="slime":
            x += 18*ease((t-payoff)/2)
        y = (target_y-6 if moving else 277) + math.sin(t*2)*(7 if moving else 1)
        if f in ("dash","leap","swim"):
            x += (target_x-110)*ease((t-action)/.55)
        if f=="leap":
            y -= 54*math.sin(math.pi*clamp((t-action)/.78))
        ellipse(d,x-31,295,47,4,"#142420")
        self.secondary(d,target_x,target_y,t, f=="slime" and t>action+.24)
        self.animal(d,x,y,t, .8*snap+windup)
        if f=="slime" and 0 <= t-action <= 1.1:
            p = clamp((t-action)*4)
            for j, offset in enumerate((-7,5)):
                points = []
                for i in range(15):
                    u = p*i/14
                    points.append((x+10+(target_x-x-2)*u, y+offset*(1-u)+math.sin(u*17+j)*7*u))
                d.line(points,"#286f67",5)
                d.line(points,"#8af7c6",2)
        if .20 <= t-action < .95:
            for i in range(22):
                age=t-action-.20
                angle=i*2.399
                px=target_x+math.cos(angle)*i*age*5
                py=target_y+math.sin(angle)*i*age*4+age*age*24
                d.rectangle((px,py,px+2,py+2),fill="#99efc0" if f=="slime" else "#e9be80")
        shift = int(83+track*1.25+shake)
        im.alpha_composite(self.foliage.crop((shift,55,shift+W,55+H)))
        dw, dh = round(W/zoom), round(H/zoom)
        camera_bias = -18*ease((t-reveal)/1.2)+36*ease((t-action+.3)/.5)-18*ease((t-endcard)/1.2)
        left = max(0,min(W-dw,round((W-dw)/2+camera_bias)))
        top = round((H-dh)*.53 + (2*math.sin(t*.8) if H-dh>8 else 0))
        top = max(0,min(H-dh,top))
        im = im.crop((left,top,left+dw,top+dh)).resize((W,H),Image.Resampling.NEAREST)
        im.alpha_composite(self.vignette)
        d = ImageDraw.Draw(im)
        accent = "#aee8af"
        d.rectangle((22,67,137,83),fill="#102828")
        d.rectangle((22,67,24,83),fill=accent)
        d.text((30,76),"BESTIARY 16-BIT",font=self.label,fill=accent,anchor="lm")
        d.text((241,76),self.spec["episode"],font=self.label,fill="#f9dbab",anchor="rm")
        if cover or t>=endcard:
            for i,line in enumerate(self.wrap(d,self.spec["name"].upper(),self.title,222)):
                d.text((22,123+i*25),line,font=self.title,fill="#ffe0a4",stroke_width=2,stroke_fill="#122017")
        return im.convert("RGB")

    @staticmethod
    def wrap(draw,text,face,width):
        lines = [""]
        for word in text.split():
            trial = (lines[-1]+" "+word).strip()
            if lines[-1] and draw.textlength(trial,font=face)>width:
                lines.append(word)
            else:
                lines[-1]=trial
        return lines

    def caption(self, text):
        im = Image.new("RGBA",(1080,1920))
        d = ImageDraw.Draw(im)
        for size in range(60,35,-2):
            f=font(size,BOLD)
            lines=self.wrap(d,text,f,810)
            if len(lines)<=2 and max(d.textlength(line,font=f) for line in lines)<=810:
                break
        else:
            raise ValueError(f"Caption terlalu panjang: {text}")
        y=1360-(len(lines)-1)*34
        d.rounded_rectangle((86,y-44,949,y+len(lines)*68-21),radius=18,fill=(8,17,23,230))
        d.rectangle((88,y-38,95,y+len(lines)*68-28),fill="#86d8a0")
        for i,line in enumerate(lines):
            d.text((518,y+i*68),line,font=f,fill="#fff5e6",anchor="mm")
        return im

    def render(self, out, cues, marks, duration):
        overlays=[self.caption(text) for _,_,text in cues]
        cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",
             "1080x1920","-framerate","30","-i","-","-c:v","libx264","-preset","veryfast","-crf","21",
             "-pix_fmt","yuv420p","-threads","4",str(out)]
        unique=set()
        with subprocess.Popen(cmd,stdin=subprocess.PIPE) as ffmpeg:
            for i in range(round(duration*FPS)):
                t=i/FPS
                small=self.frame(t,marks,duration)
                unique.add(hashlib.blake2s(small.crop((18,196,249,312)).tobytes(),digest_size=8).digest())
                im=small.resize((1080,1920),Image.Resampling.NEAREST)
                for (start,end,_),overlay in zip(cues,overlays):
                    if start<=t<end:
                        im.paste(overlay,(0,0),overlay)
                        break
                ffmpeg.stdin.write(im.tobytes())
            ffmpeg.stdin.close()
            if ffmpeg.wait():
                raise RuntimeError("FFmpeg gagal encode video.")
        self.frame(marks[1]+.28,marks,duration,cover=True).resize(
            (1080,1920),Image.Resampling.NEAREST).save(out.with_name("cover.jpg"),quality=94)
        return len(unique)


def score(duration, marks, directory):
    import wave
    rate=48000
    count=round(duration*rate)
    music=np.zeros(count)
    effects=np.zeros(count)
    rng=np.random.default_rng(23)
    def put(track,start,seconds,tone,gain,shape):
        start=max(0,round(start*rate))
        n=min(round(seconds*rate),count-start)
        if n<=0:
            return
        t=np.arange(n)/rate
        env=np.minimum(t/.018,1)*np.maximum(0,1-t/seconds)**1.6
        track[start:start+n]+=gain*env*shape(t,tone)
    tri=lambda t,f: 2*np.arcsin(np.sin(2*np.pi*f*t))/np.pi
    notes=[146.83,220,261.63,329.63,130.81,196,220,293.66]
    for i in range(math.ceil(duration/.31)):
        put(music,i*.31,.6,notes[i%8],.078,tri)
        if i%4==0:
            put(music,i*.31,1.15,notes[i%8]/2,.12,tri)
    reveal, action, payoff, endcard=marks
    noise=lambda t,f: rng.uniform(-1,1,len(t))*.55+np.sin(2*np.pi*(f*t-94*t*t))*.45
    put(effects,.18,.42,160,.14,noise)
    for step in np.arange(reveal,action-.3,.43):
        put(effects,step,.10,105,.048,noise)
    put(effects,action,.36,410,.27,noise)
    put(effects,action+.23,.38,83,.30,tri)
    put(effects,payoff,.52,218,.13,noise)
    put(effects,endcard,.55,587,.12,tri)
    for name, track in [("music",music),("sfx",effects)]:
        fade=np.minimum(1,np.arange(count)/(rate*.22))
        fade*=np.minimum(1,np.arange(count,0,-1)/(rate*.45))
        samples=(np.clip(track*fade,-1,1)*32767).astype("<i2")
        with wave.open(str(directory/f"{name}.wav"),"wb") as wav:
            wav.setparams((1,2,rate,0,"NONE","not compressed"))
            wav.writeframes(samples.tobytes())
