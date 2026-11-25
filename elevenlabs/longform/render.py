"""Animated 16-bit deep-ocean renderer for long-form BESTIARY."""
import argparse
import json
import math
import random
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 270, 480, 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
random.seed(1601)
PARTICLES = [(random.randrange(W), random.randrange(H), random.choice((1, 1, 2)),
              random.choice((7, 12, 18, 27))) for _ in range(110)]
DEPTHS = {"descent":"000 M", "twilight":"250 M", "barreleye":"700 M",
          "light":"1,100 M", "anglerfish":"1,600 M", "vampire_squid":"2,500 M",
          "siphonophore":"3,300 M", "hadal":"8,000 M"}
BACKGROUND = Image.new("RGB", (W,H))
_BG = ImageDraw.Draw(BACKGROUND)
for _yy in range(H):
    _k = _yy / H
    _BG.line((0,_yy,W,_yy), fill=(int(4+4*_k),int(12+15*_k),int(35+36*_k)))


def wrap(draw, text, font, max_width):
    lines, current = [], ""
    for word in text.replace("\n", " ").split():
        trial = (current + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fish(draw, x, y, scale, color, phase, dome=False):
    wag = int(math.sin(phase * 7) * 4 * scale)
    draw.ellipse((x-35*scale, y-15*scale, x+30*scale, y+15*scale),
                 fill=color, outline=(167, 219, 202))
    draw.polygon([(x-32*scale,y),(x-50*scale,y-12*scale+wag),
                  (x-49*scale,y+13*scale+wag)], fill=color)
    draw.polygon([(x+27*scale,y),(x+40*scale,y-7*scale),
                  (x+38*scale,y+8*scale)], fill=(225,166,116))
    draw.ellipse((x+16*scale,y-5*scale,x+20*scale,y-1*scale), fill=(236,246,207))
    if dome:
        draw.arc((x-10*scale,y-39*scale,x+29*scale,y+5*scale),180,355,
                 fill=(139,236,226),width=max(1,int(scale*2)))
        angle = 1 if int(phase*2)%4 == 0 else 0
        for ex in (x+2*scale,x+12*scale):
            ey = y-23*scale if angle else y-15*scale
            draw.ellipse((ex-3*scale,ey-7*scale,ex+3*scale,ey+7*scale),
                         fill=(108,239,180), outline=(215,255,225))


def draw_frame(t, chapter, active_caption):
    img = BACKGROUND.copy()
    d = ImageDraw.Draw(img)
    scene = chapter["scene"]
    # layered water particles provide continuous parallax motion
    for x,y,size,speed in PARTICLES:
        px = int((x - t*speed) % W)
        py = int((y + math.sin(t*.5+x)*2) % H)
        d.rectangle((px,py,px+size,py+size), fill=(44,92,120))
    # distant ROV beam and moving submersible
    drift = int(16*math.sin(t*.13))
    d.polygon([(120+drift,82),(40+drift,390),(235+drift,390)],
              fill=(11,28,54))
    sx = 115 + int(32*math.sin(t*.11))
    d.rounded_rectangle((sx-18,91,sx+18,108), radius=4, fill=(148,176,170))
    d.rectangle((sx-7,86,sx+7,92), fill=(90,154,158))
    d.ellipse((sx-5,96,sx+5,104), fill=(79,203,215))
    # visual focal subject varies by chapter
    y = 235 + int(8*math.sin(t*1.2))
    if scene == "barreleye":
        fish(d,145,y,1.15,(83,145,132),t,True)
    elif scene == "anglerfish":
        fish(d,145,y,1.25,(138,100,112),t)
        d.line((160,y-13,175,y-48-int(4*math.sin(t*3))),
               fill=(218,179,109),width=2)
        d.ellipse((170,y-56-int(4*math.sin(t*3)),180,y-46-int(4*math.sin(t*3))),
                  fill=(248,210,129))
        d.arc((154,y-2,174,y+12),10,160,fill=(245,197,151),width=2)
    elif scene == "vampire_squid":
        d.ellipse((122,y-22,153,y+23),fill=(126,72,116),outline=(235,145,190))
        for i in range(8):
            xx=125+i*4
            endx=xx+int(math.sin(t*1.8+i)*8)
            d.line((xx,y+12,endx,y+43+(i%3)*4),fill=(197,96,153),width=2)
        d.ellipse((132,y-5,136,y-1),fill=(255,216,189))
    elif scene == "siphonophore":
        for i in range(13):
            yy=150+i*17+int(5*math.sin(t+i*.5))
            xx=144+int(15*math.sin(t*.7+i*.5))
            d.ellipse((xx-4,yy-5,xx+4,yy+5),fill=(119,211,207),outline=(206,248,223))
            d.line((xx,yy+5,xx+int(7*math.sin(t+i)),yy+17),fill=(172,133,211),width=1)
    elif scene in ("migration","light"):
        for i in range(5):
            fish(d,60+i*38,y+int(math.sin(t+i)*28),.46,
                 (70,142,150),t+i,False)
            if scene=="light":
                d.ellipse((60+i*38,y+int(math.sin(t+i)*28)+4,
                           66+i*38,y+int(math.sin(t+i)*28)+10),
                          fill=(131,236,210))
    elif scene == "hadal":
        fish(d,145,y,1.0,(130,146,154),t)
        d.polygon([(0,415),(35,397),(78,416),(115,398),(165,416),(210,395),
                   (270,414),(270,480),(0,480)],fill=(24,35,53))
    elif scene == "whale_fall":
        d.arc((86,272,204,398),185,355,fill=(159,145,125),width=8)
        for xx in (103,120,138,158,179):
            d.line((xx,334,xx-8,390),fill=(170,157,130),width=5)
        for i in range(4):
            fish(d,45+i*52,365+int(math.sin(t+i)*8),.30,(120,149,136),t+i)
    else:
        fish(d,145,y,1.0,(94,139,139),t,False)
    # HUD
    font = ImageFont.truetype(FONT, 10)
    d.rounded_rectangle((10,12,260,47),radius=4,fill=(9,20,39),outline=(65,126,151))
    d.text((18,18),"BESTIARY // DEEP DIVE",font=font,fill=(147,230,216))
    d.text((205,31),DEPTHS.get(scene,""),font=font,fill=(241,208,137))
    d.rectangle((17,34,188,39),fill=(31,58,78))
    d.rectangle((17,34,17+int(170*min(1,t/45)),39),fill=(77,199,191))
    # chapter caption panel
    if active_caption:
        capfont = ImageFont.truetype(FONT, 12)
        lines = wrap(d, active_caption, capfont, 226)
        lines = lines[:3]
        panel_h = 18 + len(lines)*16
        top = 443-panel_h
        d.rounded_rectangle((12,top,258,447),radius=4,fill=(8,17,35),outline=(76,143,160))
        for i,line in enumerate(lines):
            d.text((22,top+9+i*16),line,font=capfont,fill=(245,244,228))
    return img


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--timeline",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    timeline=json.loads(Path(args.timeline).read_text())
    total=sum(c["duration"] for c in timeline["chapters"])
    proc=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-y",
      "-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
      "-an","-vf","scale=1080:1920:flags=neighbor","-r","30","-c:v","libx264",
      "-preset","veryfast","-crf","20","-pix_fmt","yuv420p",args.output],
      stdin=subprocess.PIPE)
    tick=0
    for chapter in timeline["chapters"]:
        duration=chapter["duration"]
        cues=chapter["captions"]
        cue_index=0
        frames=math.ceil(duration*FPS)
        for i in range(frames):
            local=i/FPS
            while cue_index+1<len(cues) and local>cues[cue_index][1]:
                cue_index+=1
            caption=cues[cue_index][2] if cues and cues[cue_index][0]<=local<=cues[cue_index][1] else ""
            frame=draw_frame(tick/FPS,chapter,caption)
            proc.stdin.write(frame.tobytes())
            tick+=1
    proc.stdin.close()
    if proc.wait()!=0:
        raise SystemExit("FFmpeg failed during pixel-art rendering.")

if __name__=="__main__":
    main()
