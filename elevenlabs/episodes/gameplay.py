"""Pixel gameplay levels for EP19 and EP20."""
import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import random
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H, F = 270, 480, 4
INK = (236,241,218)
MINT = (149,237,188)
GOLD = (255,217,144)
DARK = (9,29,42)
rng = random.Random(982)
DUST = [(rng.randrange(310),rng.randrange(252),rng.randrange(34)) for _ in range(140)]
PEBBLES = [(rng.randrange(510),rng.randrange(62),rng.randrange(5)) for _ in range(740)]
MONO="/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS=next(str(p) for p in (Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                           Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"))
          if p.exists())


def ease(t,a,b):
    x = min(1,max(0,(t-a)/max(.05,b-a)))
    return x*x*(3-2*x)


def blend(a,b,x):
    return tuple(round(i+(j-i)*x) for i,j in zip(a,b))


@lru_cache(maxsize=48)
def font(size,mono=True):
    return ImageFont.truetype(MONO if mono else SANS, size*F)


def point(x,y):
    return round(x),round(y)


def plant(d,x,y,phase,h,color,bright):
    for j in range(5):
        stem=[point(x+(j-2)*(2+u*5)+u*5*math.sin(phase+j+u),y-h*u*(.71+j*.07))
              for u in (0,.25,.5,.75,1)]
        d.line(stem,fill=color,width=2)
        for k,(sx,sy) in enumerate(stem[1:4]):
            sign=(-1)**(k+j)
            d.polygon([(sx,sy+2),(sx+7*sign,sy-6),(sx+4*sign,sy-7)],fill=bright)


def background(t,cam,crab):
    im=Image.new("RGB",(W,H))
    d=ImageDraw.Draw(im)
    palette=((13,46,67),(27,113,118),(12,36,56)) if crab else ((70,112,105),(151,188,143),(11,51,74))
    for y in range(0,H,3):
        if crab:
            value=max(0,1-abs(y-136)/260)
            color=blend(palette[2],palette[1],value*.63)
        elif y<210:
            color=blend(palette[0],palette[1],y/210)
        else:
            color=blend((46,133,128),palette[2],min(1,(y-210)/177))
        d.rectangle((0,y,W,y+2),fill=color)
    if crab:
        for idx in range(6):
            offset=idx*66-(cam*.16)%66
            d.polygon([(offset,81),(offset+9,81),(offset-47,244),(offset-67,269)],
                      fill=(22,77,88))
    else:
        d.ellipse((177,108,210,141),fill=(203,208,143))
    for idx in range(12):
        x=idx*30-(cam*.27)%30-17
        if crab:
            top=239+round(math.sin(idx*4)*21)
            d.polygon([(x-22,316),(x-16,top+27),(x-3,top),(x+13,top+3),(x+25,316)],
                      fill=(31,70,81))
            d.line([(x-16,top+27),(x-3,top),(x+13,top+3)],fill=(48,96,99))
        else:
            top=144+round(math.sin(idx*3)*22)
            d.rectangle((x-3,top,x+3,214),fill=(59,106,91))
            d.polygon([(x,171),(x-27,top+21),(x-16,top+8),(x,top),
                       (x+14,top+8),(x+24,top+27)],fill=(75,130,98))
    floor=303 if crab else 324
    edge=[(x,floor+round(5*math.sin((x+cam)/48)+3*math.sin((x+cam)/19))) for x in range(-4,275,4)]
    soil=(75,88,80) if crab else (45,85,84)
    d.polygon(edge+[(W,H),(0,H)],fill=soil)
    d.line(edge,fill=(132,142,104) if crab else (85,144,121),width=2)
    for x,y,k in PEBBLES:
        xx=round((x-cam*.83)%410)-15
        yy=floor+3+y+round(5*math.sin((xx+cam)/48))
        d.line((xx,yy,xx+k,yy),fill=blend(soil,(165,164,111),k*.10))
    for idx in range(9):
        x=idx*52-cam%52-32
        if crab or idx%2:
            plant(d,x,floor+1,t*2+idx,20+(idx*7)%38,(37,104,91),(76,140,102))
    for x,y,k in DUST:
        xx=round((x+t*(1+k*.15)-cam*.40)%300)-12
        yy=y+126
        if not crab and yy<215:
            continue
        d.point((xx,yy),fill=(63+k//2,109+k,105+k))
    return im


def status(t, starts, ep):
    if ep=="EP19":
        return ("MISI 01 / RAWA BAKAU", "JATUHKAN SERANGGA", "BIDIK SASARAN",
                "A  SEMBURKAN AIR", "KEJAR MANGSA", "SERANGGA TERTANGKAP",
                starts[2],starts[4],starts[6],starts[7],starts[9]+.48)
    return ("MISI 02 / TERUMBU", "RAKIT KAMUFLASE", "PUNGUT ALGA",
            "A  PASANG ALGA & SPONS", "MENYATU DENGAN TERUMBU", "KAMUFLASE TERPASANG",
            starts[2],starts[3],starts[7],starts[9],starts[9]+.68)


def overlay(im,t,timing,episode,starts):
    screen=im.resize((W*F,H*F),Image.Resampling.NEAREST)
    d=ImageDraw.Draw(screen)

    def box(x,y,r,b,fill,outline=None):
        d.rectangle(tuple(round(i*F) for i in (x,y,r,b)),fill=fill,outline=outline,width=F)

    def txt(x,y,msg,size,color,anchor="lt",mono=True):
        d.text((round(x*F),round(y*F)),msg,fill=color,font=font(size,mono),anchor=anchor)

    level,mission,aim,act,resolve,win,ready,aim_at,action_at,resolve_at,win_at = status(t,starts,episode)
    box(18,49,237,82,DARK,(78,142,141))
    txt(25,55,"BESTIARY 16-BIT",10,INK)
    txt(229,55,episode,10,GOLD,"rt")
    txt(25,71,level,7,MINT)
    box(172,70,229,74,(29,65,76))
    box(172,70,172+57*t/timing["duration"],74,GOLD)
    if t<ready:
        box(30,101,223,136,DARK,(75,145,141))
        txt(126,108,mission,11,GOLD,"mt")
        name = "IKAN PEMANAH" if episode=="EP19" else "KEPITING DEKORATOR"
        txt(126,123,name,8,INK,"mt")
    elif t>=win_at:
        box(40,102,216,144,DARK,MINT)
        txt(128,108,"LEVEL CLEAR",16,MINT,"mt")
        txt(128,130,win,7,INK,"mt")
    else:
        box(29,102,226,123,DARK,(67,126,130))
        label = resolve if t>=resolve_at else act if t>=action_at else aim if t>=aim_at else mission
        txt(127,108,label,9,MINT if t>=resolve_at else GOLD,"mt")
    if episode=="EP20" and aim_at<t<win_at:
        box(21,140,103,155,DARK,(51,110,114))
        txt(27,144,"KAMUFLASE",7,INK)
        for i in range(2):
            box(76+i*11,143,83+i*11,150,MINT if t>=action_at+i*.84+.53 else (45,77,79))
    for start,end,body in timing["captions"]:
        if start<=t<end:
            lines=body.splitlines()
            box(18,333,237,374 if len(lines)>1 else 357,DARK)
            box(18,333,20,374 if len(lines)>1 else 357,MINT)
            for i,line in enumerate(lines):
                txt(127,339+16*i,line,14,INK,"mt",False)
            break
    for x,y,char in ((25,386,"<"),(40,371,""),(40,386,""),(55,386,">"),(40,401,"v")):
        if y==371:
            continue
        active=char==">" and (t<aim_at or resolve_at<=t<win_at)
        box(x-7,y-7,x+7,y+7,GOLD if active else (22,60,69),(75,126,125))
        if char:
            txt(x,y-4,char,8,DARK if active else INK,"mt")
    active=action_at-.12<=t<=action_at+.57 or (episode=="EP20" and action_at+.80<=t<=action_at+1.3)
    box(198,379,226,402,GOLD if active else (22,60,69),(91,158,143))
    txt(212,385,"A",11,DARK if active else MINT,"mt")
    return screen


def bug(d,x,y,t,falling):
    if falling:
        for side in (-1,1):
            wing=round(5*math.sin(t*34)*side)
            d.polygon([(x,y),(x+side*8,y+wing-6),(x+side*4,y+5)],fill=(206,174,111))
    d.ellipse((x-4,y-3,x+4,y+3),fill=(49,34,44),outline=(23,26,36))
    d.point((x+2,y-2),fill=(220,172,80))
    for n in range(3):
        d.line([(x-3+n*2,y+2),(x-5+n*3,y+6)],fill=(52,32,39))


def archer(t,starts):
    fire, drop, catch=starts[6],starts[7],starts[9]+.25
    pan=18*t+21*ease(t,drop,catch)
    im=background(t,pan,False)
    d=ImageDraw.Draw(im)
    for x in range(0,W,6):
        top=211+round(2*math.sin(t*3+x*.15))
        d.line((x,top,x+4,top),fill=(151,216,172))
        if x%3==0:
            d.line((x+2,top+2,x+5,top+2),fill=(83,169,144))
    bx,by=191-8*ease(t,0,fire),153
    branch=[(W,147),(227,150),(209,157),(176,159),(161,165)]
    d.line(branch,fill=(67,74,49),width=7)
    d.line(branch,fill=(151,136,75),width=2)
    for i in range(9):
        x=166+i*11
        y=159-(i//2)*3
        airy=round(2*math.sin(t*3+i))
        direction=(-1)**i
        d.polygon([(x,y),(x+8,y+direction*(8+airy)),(x+16,y+direction*(5+airy)),
                   (x+9,y+direction*2)],fill=(89,142,78))
    swim=ease(t,0,starts[4])
    dash=ease(t,drop+.08,catch)
    px=76+25*swim+61*dash
    py=249-15*swim-22*dash+3*math.sin(t*3)
    angle=-.13-.18*ease(t,starts[3],fire)+.27*dash
    c,s=math.cos(angle),math.sin(angle)
    base=(187,207,176)
    def p(x,y):
        return point(px+x*c-y*s,py+x*s+y*c)
    def poly(pts,color,outline=None):
        d.polygon([p(x,y) for x,y in pts],fill=color,outline=outline)
    wag=6*math.sin(t*9)
    poly([(-40,0),(-56,-13+wag),(-60,-9+wag),(-52,0),
          (-58,11+wag),(-44,6),(-36,5)],(109,160,152),(30,79,88))
    poly([(-25,-13),(-16,-25+wag*.35),(-5,-23+wag*.35),(5,-14)],
         (118,165,137),(41,103,104))
    poly([(-47,1),(-35,-11),(-21,-17),(-5,-20),(15,-17),(27,-9),(34,-3),(35,3),
          (23,11),(6,17),(-13,16),(-32,10)],base,(30,77,83))
    poly([(-41,2),(-26,7),(-6,10),(11,10),(28,5),(29,10),(9,16),(-11,15),(-30,10)],
         (123,165,149))
    for x,yend in ((-30,6),(-16,9),(-1,10),(13,7)):
        top=-15 if x<-19 else -18
        poly([(x-4,top),(x+1,top-1),(x+5,0),(x+4,yend),(x,yend-1),
              (x-1,-2)],(55,86,90))
    poly([(-3,4),(-1,11),(-18,18+wag*.55),(-10,10+wag*.4)],(98,151,146),(42,98,100))
    d.line([p(-34,-10),p(-18,-16),p(-4,-19),p(15,-16)],fill=(230,235,193))
    ex,ey=p(23,-6)
    d.ellipse((ex-4,ey-4,ex+4,ey+4),fill=(233,215,130),outline=(44,80,79))
    d.ellipse((ex-2,ey-2,ex+3,ey+3),fill=(19,48,60))
    d.point((ex,ey-1),fill=INK)
    muzzle=p(35,1)
    if starts[4]<t<fire:
        for i in range(1,10):
            u=i/11
            d.point(point(muzzle[0]+(bx-muzzle[0])*u,muzzle[1]+(by-muzzle[1])*u),fill=GOLD)
        for dx in (-1,1):
            for dy in (-1,1):
                d.line([(bx+dx*6,by+dy*11),(bx+dx*11,by+dy*11),(bx+dx*11,by+dy*6)],fill=GOLD)
    duration=.53
    if fire<=t<=fire+duration:
        for i in range(25):
            u=(t-fire)*3.8-i*.044
            if 0<u<1:
                x,y=point(muzzle[0]+(bx-muzzle[0])*u,muzzle[1]+(by-muzzle[1])*u)
                d.rectangle((x-1,y-1,x+1,y+1),fill=(192,252,241) if i%3==0 else (117,214,220))
    if fire+.245<=t<catch:
        fallen=ease(t,fire+.245,drop+.75)
        bug(d,bx+round(8*fallen),by+round(58*fallen),t,True)
    elif t<fire+.245:
        bug(d,bx,by,t,False)
    ripple=ease(t,drop+.65,drop+1.55)
    if 0<ripple<1:
        r=round(5+24*ripple)
        d.ellipse((bx+8-r,208-round(r/5),bx+8+r,212+round(r/5)),
                  outline=blend((217,250,216),(62,148,132),ripple))
    return im


def decoration(d,x,y,t,kind,scale=1):
    if kind=="alga":
        plant(d,x,y,t*2,round(27*scale),(44,104,75),(116,169,92))
    else:
        for dx,dy,r in ((-9,-5,6),(0,-10,8),(9,-6,6),(1,-3,8)):
            cx,cy=point(x+dx*scale,y+dy*scale)
            rad=max(2,round(r*scale))
            d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad),fill=(182,118,112),outline=(110,78,91))
            d.ellipse((cx-2,cy-rad+1,cx+2,cy-rad+4),fill=(121,79,88))
            d.point((cx-2,cy),fill=(249,163,126))


def crab(t,starts):
    aim, detail, fit, finish=starts[3],starts[5],starts[7],starts[9]
    pan=11*t+16*ease(t,0,aim)
    im=background(t,pan,True)
    d=ImageDraw.Draw(im)
    carry=ease(t,aim,detail)
    mobile=1-ease(t,aim-.6,aim+.25)+.75*ease(t,finish-.36,finish+.50)
    cx=79+32*ease(t,0,aim)+34*ease(t,finish-.4,finish+.8)
    cy=270+2*math.sin(t*10)*mobile
    zoom=ease(t,detail-.35,detail+.22)-ease(t,fit-.22,fit+.36)
    scale=1+.39*zoom
    def p(x,y):
        return point(cx+x*scale,cy+y*scale)
    def poly(pts,color,outline=None):
        d.polygon([p(x,y) for x,y in pts],fill=color,outline=outline)

    for x in (170,197,221):
        decoration(d,x,292,t+x,"alga",1)
    decoration(d,214,304,t,"spons",1.2)
    if carry<.99:
        for i,kind in enumerate(("alga","spons")):
            x=round((142+i*16)*(1-carry)+(cx+35-i*8)*carry)
            y=round((298-i*5)*(1-carry)+(cy-10+i*10)*carry)
            decoration(d,x,y,t,kind,.53)
    # Eight independent walking legs and a pair of articulated claws.
    for side in (-1,1):
        for j in range(4):
            phase=t*12+side*1.9+j*2.5
            wag=math.sin(phase)*6*mobile
            lift=max(0,math.cos(phase))*6*mobile
            leg=[p(side*(12+j*2),7+j),p(side*(27+j*5),8-j*2),
                 p(side*(34+j*5)+wag,19+j*2-lift),p(side*(44+j*3)+wag,29+j-lift)]
            d.line(leg,fill=(45,59,63),width=6)
            d.line(leg,fill=(155-j*11,117-j*7,95-j*5),width=3)
            d.point(leg[1],fill=(214,164,122))
    mount=[ease(t,fit,fit+.75),ease(t,fit+.83,fit+1.55)]
    for i,side in enumerate((-1,1)):
        reach=math.sin(mount[i]*math.pi)
        hand=(side*(34-20*reach),-5-25*reach)
        path=[p(side*16,9),p(side*(28-7*reach),6-16*reach),p(*hand)]
        d.line(path,fill=(63,65,76),width=8)
        d.line(path,fill=(180,130,106),width=4)
        x,y=hand
        gape=3+2*math.sin(t*9+i)
        poly([(x-6,y+5),(x-7,y-3),(x-4,y-8),(x,y-10),(x+3,y-6),
              (x+2,y-2),(x+5,y-gape-2),(x+8,y-8),(x+8,y+1),(x+4,y+5)],
             (183,133,106),(78,70,79))

    shell=[(-28,1),(-26,-8),(-19,-17),(-10,-22),(3,-24),(15,-19),(24,-12),
           (29,-4),(29,5),(22,12),(11,15),(-4,16),(-20,11)]
    poly(shell,(151,123,100),(55,68,72))
    poly([(-25,0),(-18,-15),(-9,-20),(4,-22),(15,-17),(8,-9),
          (-2,-4),(-16,1)],(193,157,119))
    poly([(-25,5),(-11,8),(4,6),(17,4),(28,1),(26,8),(17,12),(6,15),
          (-9,13),(-20,10)],(113,100,91))
    for i in range(40):
        x=(i*13)%48-24
        y=(i*7)%30-19
        if (x/27)**2+((y+4)/20)**2<.91:
            d.point(p(x,y),fill=(114+(i%4)*19,100+(i%4)*12,86+(i%4)*12))
    for x in (-9,9):
        d.line([p(x,4),p(x,-6)],fill=(189,162,118),width=3)
        ex,ey=p(x,-6)
        d.ellipse((ex-3,ey-3,ex+3,ey+3),fill=(31,53,60))
        d.point((ex,ey-1),fill=(255,241,194))
    if zoom>.5:
        for x in range(-13,21,7):
            d.line([p(x,-19),p(x+1,-24),p(x+4,-25),p(x+4,-22)],fill=(237,221,156))
        d.line([p(19,-25),p(36,-45),p(55,-45)],fill=(237,221,156))
        d.text(p(58,-48),"KAIT",font=font(6).font_variant(size=7),fill=(238,233,170))
    if carry>=.99:
        for i,kind in enumerate(("alga","spons")):
            u=mount[i]
            from_x,from_y=((35,-10),(26,0))[i]
            to_x,to_y=((-9,-18),(10,-18))[i]
            x,y=p(from_x+(to_x-from_x)*u,from_y+(to_y-from_y)*u-23*math.sin(u*math.pi))
            decoration(d,x,y,t,kind,.67)
    return im


def frame(index,timing,episode):
    t=index/30
    starts=[start for start,_,_ in timing["captions"]]
    canvas=archer(t,starts) if episode=="EP19" else crab(t,starts)
    return overlay(canvas,t,timing,episode,starts)


def main(episode):
    parser=argparse.ArgumentParser()
    parser.add_argument("--timing",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stills",action="store_true")
    args=parser.parse_args()
    timing=json.loads(args.timing.read_text())
    if args.stills:
        grid=Image.new("RGB",(W*5,H*2))
        for i,(a,b,_) in enumerate(timing["captions"]):
            grid.paste(frame(round((a+b)*15),timing,episode).resize((W,H)),
                       (i%5*W,i//5*H))
        grid.save(args.output)
        return
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",
         "1080x1920","-framerate","30","-i","-","-an","-c:v","libx264","-threads","3",
         "-preset","veryfast","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",
         "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709",str(args.output)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as job:
        try:
            for index in range(round(timing["duration"]*30)):
                job.stdin.write(frame(index,timing,episode).tobytes())
        finally:
            job.stdin.close()
        if job.wait():
            raise RuntimeError("Gameplay render failed.")
