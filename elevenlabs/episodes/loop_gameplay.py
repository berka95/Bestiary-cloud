"""Animated gameplay levels with a frame-matched return to the opening."""
import argparse
import json
import math
from pathlib import Path
import random
import subprocess

from PIL import Image, ImageDraw

from gameplay import W, H, F, DARK, GOLD, INK, MINT, ease, blend, font, plant, point

rng=random.Random(2122)
DUST=[(rng.randrange(305),rng.randrange(140,337),rng.randrange(15))
      for _ in range(160)]
GRAIN=[(rng.randrange(310),rng.randrange(100),rng.randrange(6)) for _ in range(1250)]
LEAVES=[(rng.randrange(260),rng.randrange(207,326),rng.randrange(5)) for _ in range(190)]
TWIGS=[(rng.uniform(0,1),rng.uniform(0,1),rng.uniform(0,1)) for _ in range(42)]


def landscape(t,forest,scroll):
    im=Image.new("RGB",(W,H))
    d=ImageDraw.Draw(im)
    for y in range(0,H,3):
        q=min(1,y/350)
        color=blend((22,55,53),(111,147,101),q) if forest else blend(
            (77,59,66),(215,157,108),q)
        d.rectangle((0,y,W,y+2),fill=color)
    for j in range(7):
        x=round(j*68-scroll*.4%68-26)
        if forest:
            d.polygon([(x-13,302),(x-8,99),(x+2,88),(x+11,108),(x+13,302)],
                      fill=(37,89,70))
            d.line((x+3,102,x+8,302),fill=(59,113,82),width=3)
            d.polygon([(x-30,113),(x-7,87),(x+30,103),(x+16,135)],fill=(41,94,69))
        else:
            d.polygon([(x-42,278),(x-15,166+j%3*9),(x+10,178+j%3*9),
                       (x+41,255),(x+64,278)],fill=(144,100,86))
            d.line((x-15,166+j%3*9,x+10,178+j%3*9,x+23,215),
                   fill=(171,121,95),width=2)
    for j in range(6):
        x=round(j*65-scroll*.77%65-20)
        y=284+int(4*math.sin(j*3+t))
        plant(d,x,y,t*.8+j,26+j%3*9,(51,102,74) if forest else (109,108,76),
              (92,137,74) if forest else (153,136,84))
    if forest:
        edge=[(x,292+round(3*math.sin((scroll+x)/28))) for x in range(-4,275,4)]
        d.polygon(edge+[(W+6,H),(-4,H)],fill=(58,92,64))
        d.line(edge,fill=(123,145,86),width=2)
        for x,y,k in LEAVES:
            gx=round((x-scroll*.9)%270)
            gy=292+(y%99)
            d.line((gx,gy,gx+5+k,gy-2),fill=(65+10*k,88+8*k,50+4*k))
    for x,y,k in DUST:
        xx=round((x-scroll*.26+t*(2+k*.24))%310)-12
        d.point((xx,y+round(math.sin(t+k)*3)),
                fill=(91+k*2,130+k*2,101) if forest else (198+k*2,144+k*2,98))
    return im


def ant(d,x,y,t,tilt,leg_energy=1):
    c,s=math.cos(tilt),math.sin(tilt)
    def p(a,b):
        return point(x+a*c-b*s,y+a*s+b*c)
    for side in (-1,1):
        for j in range(3):
            wave=math.sin(t*20+side+j*2)*2.4*leg_energy
            d.line([p(-4+j*4,side*2),p(-6+j*4+wave,side*7),
                    p(-8+j*6+wave,side*10)],fill=(54,34,40),width=1)
    for a,b,r in ((-7,0,5),(0,0,3),(6,0,4)):
        px,py=p(a,b)
        d.ellipse((px-r,py-r,px+r,py+r),fill=(78,42,43),outline=(43,31,40))
        d.point((px-1,py-2),fill=(190,110,74))
    for side in (-1,1):
        d.line([p(7,side*2),p(12,side*4),p(14,side*7)],
               fill=(59,36,37))


def antlion(t,starts):
    builds,climb,shoot,slide,catch=starts[2],starts[4],starts[6],starts[7],starts[8]+.45
    im=landscape(t,False,10*ease(t,0,builds))
    d=ImageDraw.Draw(im)
    mid=142
    pit_top=230
    pit_depth=67
    lip=74
    def sand(x):
        return pit_top+pit_depth*max(0,1-abs(mid-x)/lip)**1.08
    edge=[point(x,sand(x)) for x in range(-4,275,2)]
    d.polygon(edge+[(W+5,H),(-4,H)],fill=(142,98,71))
    for j in range(7):
        band=[(x,y+4+j*7) for x,y in edge]
        d.line(band,fill=(164-4*j,115-3*j,78-2*j),width=3)
    d.line(edge,fill=(241,178,110),width=2)
    for x,y,k in GRAIN:
        if x>=W:
            continue
        sy=round(sand(x)+3+y*.88)
        d.line((x,sy,x+(k%3),sy),fill=(141+k*14,94+k*10,64+k*8))
    # At the lowest point the larva is partly hidden with only its head and jaws exposed.
    flick=math.sin(max(0,t-shoot)*27)*math.exp(-max(0,t-shoot)*.9) if shoot<=t<slide+.3 else 0
    head_x,head_y=mid+int(2*flick),round(sand(mid)-6+2*flick)
    d.polygon([(head_x-12,head_y+6),(head_x-10,head_y-4),(head_x-6,head_y-7),
               (head_x+3,head_y-7),(head_x+8,head_y-4),(head_x+12,head_y+6)],
               fill=(94,56,49),outline=(58,35,37))
    d.line((head_x-5,head_y-3,head_x,head_y-6,head_x+5,head_y-3),
           fill=(193,120,79))
    grab=ease(t,catch-.35,catch)
    for side in (-1,1):
        d.line([(head_x+side*7,head_y+1),(head_x+side*(14-3*grab),head_y-8),
                (head_x+side*(12-6*grab),head_y-18),(head_x+side*(7-4*grab),head_y-23)],
               fill=(61,35,39),width=3)
        d.point((head_x+side*(7-round(4*grab)),head_y-23),fill=(206,133,84))
    approach=ease(t,0,builds)
    trial=ease(t,builds,climb)
    retry=ease(t,climb,shoot)
    loss=ease(t,shoot+.25,catch)
    ax=28+43*approach+52*trial-31*retry+50*loss
    ay=sand(ax)-7-3*math.sin(t*9)*retry*(1-loss)
    if t<catch:
        direction=math.pi-.62 if climb<=t<shoot else .64 if ax>=mid-lip else 0
        ant(d,ax,ay,t,direction)
    if shoot<=t<catch+.2:
        for i,(u,v,k) in enumerate(TWIGS):
            age=t-shoot-1.22*u
            if not 0<age<.72:
                continue
            x=head_x-age*(36+72*v)
            y=head_y-age*(103+69*k)+age*age*127
            px,py=point(x,y)
            d.line((px,py,px+1+i%2,py),fill=(240,179+i%25,108))
    if slide-.45<t<catch:
        for i,(u,v,k) in enumerate(TWIGS):
            x=70+(t*43+60*u)%71
            y=sand(x)-v*6
            px,py=point(x,y)
            d.line((px,py,px+2,py+1),fill=(224,150+round(k*43),96))
    return im


def trinket(d,x,y,style):
    if style==0:
        for j in range(7):
            xx=x+j*2
            yy=y-j
            d.line((xx,yy,xx+3,yy-4),fill=(91+j*12,152+j*10,234),width=2)
        d.line((x-2,y+1,x+13,y-7),fill=(165,223,255))
    else:
        for dx,dy in ((0,-4),(-4,-1),(4,-1),(-2,3),(2,3)):
            d.ellipse((x+dx-2,y+dy-2,x+dx+2,y+dy+2),fill=(80,155,234))
        d.rectangle((x-1,y-1,x+1,y+1),fill=(201,217,157))


def bower(d,x,y,t,growth):
    for side in (-1,1):
        for i,(u,v,k) in enumerate(TWIGS):
            if u>growth:
                continue
            off=side*(18+25*u)
            height=17+round(42*k)
            x0=x+off
            y0=y+v*6
            bow=side*(10+6*math.sin(i))
            d.line([point(x0,y0),point(x0-bow*.45,y0-height*.51),
                    point(x0-bow,y0-height)],
                   fill=(91+round(k*64),65+round(k*43),47+round(k*34)),
                   width=1+(i%5==0))
    d.line((x-57,y+8,x+53,y+6),fill=(135,103,63))


def bird(d,x,y,t,facing,walk,dance,female=False):
    c=1 if facing>0 else -1
    reach=3*math.sin(t*7)*dance
    peck=6*dance*math.sin(t*13)
    def p(a,b):
        return point(x+a*c,y+b)
    def shape(coords,color,outline=None):
        d.polygon([p(a,b) for a,b in coords],fill=color,outline=outline)
    if female:
        body=(111,125,76); wing=(88,107,70); glint=(182,173,110); shade=(62,75,56)
    else:
        body=(37,59,91); wing=(50,77,123); glint=(99,147,190); shade=(23,37,60)
    for i in range(2):
        w=math.sin(t*16+i*math.pi)*walk
        d.line([p(-6+i*10,18),p(-5+i*8+5*w,26-w*2),p(-12+i*10+5*w,29-w*2)],
               fill=(159,133,103),width=2)
        d.line([p(-5+i*8+5*w,26-w*2),p(2+i*8+5*w,29-w*2)],
               fill=(159,133,103))
    tail=5*math.sin(t*6)*(.3+.7*dance)
    shape([(-15,7),(-37,15+tail),(-45,13+tail),(-30,4+tail),(-17,2)],shade,(15,35,46))
    shape([(-24,7),(-27,-2),(-24,-10),(-15,-16),(-3,-16),(10,-13),
           (17,-6),(18,3),(10,15),(-5,22),(-16,19)],body,shade)
    shape([(-23,1),(-18,-10),(-8,-13),(4,-8),(4,4+reach),
           (-9,12+reach),(-21,12)],wing,shade)
    for i in range(4):
        d.line([p(-19+i*4,-6+i*.7),p(-20+i*4,5+i+reach)],
               fill=blend(wing,glint,.35+i*.09))
    hx=13+peck*.38
    hy=-19+peck
    shape([(hx-9,hy+8),(hx-10,hy-2),(hx-6,hy-10),(hx+1,hy-12),
           (hx+9,hy-8),(hx+12,hy-1),(hx+9,hy+7),(hx+2,hy+11)],
          body,shade)
    d.line([p(hx-6,hy-8),p(hx,hy-10),p(hx+5,hy-8)],fill=glint)
    shape([(hx+9,hy-3),(hx+21,hy+1),(hx+10,hy+4)],(219,217,181),(84,96,104))
    ex,ey=p(hx+5,hy-4)
    d.ellipse((ex-2,ey-2,ex+2,ey+2),fill=(161,148,221),outline=(41,44,61))
    d.point((ex,ey),fill=(18,28,39))
    return p(hx+21,hy+2)


def forest(t,starts):
    build,collect,show=starts[2],starts[3],starts[6]
    pan=17*ease(t,0,collect)-11*ease(t,show,starts[-1])
    im=landscape(t,True,pan)
    d=ImageDraw.Draw(im)
    shelf=298
    arch_x=190-round(pan*.45)
    built=ease(t,build-.10,collect)
    bower(d,arch_x,shelf-3,t,built)
    travel=ease(t,0,build)
    searching=ease(t,collect,show)
    dancing=ease(t,starts[7]-.2,starts[7]+.1)-ease(t,starts[8]-.2,starts[8]+.3)
    x=69+33*travel+40*searching+7*math.sin(t*6)*dancing
    lookback=ease(t,starts[9]-.1,starts[9]+.3)
    y=shelf-30-3*abs(math.sin(t*10))*(1-ease(t,show-.1,show+.5))
    i=ease(t,starts[4],starts[5])
    j=ease(t,starts[5],show+.2)
    if built<1:
        for k,(dx,dy,_) in enumerate(TWIGS[:8]):
            if k/8<built:
                continue
            xx=round(arch_x-40+38*dx)
            yy=round(shelf-8+11*dy)
            d.line((xx-3,yy+1,xx+8,yy-3),fill=(167,126,75))
    pick=ease(t,collect,starts[4])
    carry=1 if 0<pick<1 or 0<i<1 else 0
    female=ease(t,show-.1,starts[7]-.1)-ease(t,starts[8]+.4,starts[9]+.25)
    if female>.04:
        bird(d,306-78*female,shelf-31,t,-1,1-female,0,True)
    px,py=bird(d,x,y,t,-1 if lookback>.5 else 1,
               max(.2,1-ease(t,show-.13,show+.10)),dancing)
    for n,amount in enumerate((i,j)):
        x0,y0=132+n*29,shelf-2+n*7
        x1,y1=arch_x-33+n*16,shelf+4+n*3
        if 0<amount<1:
            gx=round(px+(x1-px)*ease(amount,.65,1))
            gy=round(py+(y1-py)*ease(amount,.65,1))
        elif amount>=1:
            gx,gy=x1,y1
        else:
            gx,gy=x0,y0
        trinket(d,gx,gy,n)
        if amount<.1 and (t<build or n==1):
            phase=(t*2.5+n*.5)%1
            if phase<.57:
                sx=gx+8
                sy=gy-11
                d.line((sx-3,sy,sx+3,sy),fill=(139,209,241))
                d.line((sx,sy-3,sx,sy+3),fill=(139,209,241))
    if carry and 0<built<1:
        d.line((px,py,px+12,py-4),fill=(165,119,73))
    if dancing>.2:
        trinket(d,px,py,0)
    return im


def graphics(im,t,starts,timing,ep):
    screen=im.resize((W*F,H*F),Image.Resampling.NEAREST)
    d=ImageDraw.Draw(screen)

    def box(x,y,r,b,color,border=None):
        d.rectangle(tuple(round(i*F) for i in (x,y,r,b)),fill=color,outline=border,width=F)

    def txt(x,y,msg,size,color,anchor="lt",mono=True):
        d.text((round(x*F),round(y*F)),msg,fill=color,font=font(size,mono),anchor=anchor)

    a=ep=="EP21"
    name="LARVA UNDUR-UNDUR" if a else "NAMDUR SATIN"
    level="MISI 03 / CORONG PASIR" if a else "MISI 04 / HUTAN"
    border=(181,122,93) if a else (90,147,126)
    box(18,48,237,83,DARK,border)
    txt(25,54,"BESTIARY 16-BIT",10,INK)
    txt(229,54,ep,10,GOLD,"rt")
    txt(25,71,level,7,MINT)
    box(176,70,229,75,(43,67,71))
    box(176,70,176+53*min(1,t/timing["duration"]),75,GOLD)
    first=starts[2]
    done=starts[8]+.52 if a else starts[7]+.62
    done_end=max(done+.34,starts[9]+.12)
    if t<first:
        box(22,100,231,140,DARK,border)
        txt(126,107,"JEBAKAN PASIR" if a else "KOLEKSI WARNA BIRU",12,GOLD,"mt")
        txt(126,126,name,8,INK,"mt")
    elif done<=t<done_end:
        box(45,102,208,147,DARK,MINT)
        txt(126,109,"LEVEL CLEAR",16,MINT,"mt")
        txt(126,132,"JEBAKAN BERHASIL" if a else "ARENA PIKAT SIAP",7,INK,"mt")
    else:
        if t>=done_end:
            text="SEMUT BERIKUTNYA" if a else "CARI HIASAN BERIKUTNYA"
        elif a:
            text=("TUNGGU DI DASAR" if t<starts[4] else "SEMUT COBA NAIK" if t<starts[6]
                  else "A  LEMPAR PASIR" if t<starts[7] else "LERENG LONGSOR")
        else:
            text=("SUSUN LORONG RANTING" if t<starts[3] else "A  AMBIL HIASAN BIRU" if t<starts[6]
                  else "PAMERKAN HIASAN" if t<starts[8] else "BETINA MEMBUAT SARANG")
        box(27,104,226,126,DARK,border)
        txt(127,111,text,9,MINT if t>=done else GOLD,"mt")
    if not a and starts[3]<=t<done:
        box(21,145,82,160,DARK,border)
        count=int(t>=starts[5])+int(t>=starts[6])
        txt(27,149,f"BIRU {count}/2",7,(157,213,241))
    if a and starts[4]<=t<done:
        x=104
        box(x-8,180,x+8,194,DARK,border)
        txt(x,182,"!",8,GOLD,"mt")
    for start,end,text in timing["captions"]:
        if start<=t<end:
            lines=text.splitlines()
            box(18,333,237,374 if len(lines)>1 else 357,DARK)
            box(18,333,20,374 if len(lines)>1 else 357,MINT)
            for j,line in enumerate(lines):
                txt(127,339+j*16,line,14,INK,"mt",False)
            break
    for x,y,char in ((25,389,"<"),(40,389,""),(55,389,">"),(40,404,"v")):
        active=char==">" and (t<starts[2] or not a and starts[3]<=t<starts[6])
        box(x-7,y-7,x+7,y+7,GOLD if active else (27,52,61),border)
        if char:
            txt(x,y-4,char,8,DARK if active else INK,"mt")
    pressed=starts[6]-.05<=t<starts[6]+.55 if a else (
        starts[4]-.05<=t<starts[4]+.35 or starts[5]-.05<=t<starts[5]+.35)
    box(199,382,226,405,GOLD if pressed else (26,58,66),border)
    txt(213,388,"A",11,DARK if pressed else MINT,"mt")
    return screen


def picture(t,timing,ep):
    starts=[c[0] for c in timing["captions"]]
    im=antlion(t,starts) if ep=="EP21" else forest(t,starts)
    return graphics(im,t,starts,timing,ep)


def loop_frame(index,timing,episode,opening):
    end=round(timing["duration"]*30)-1
    if index>=end:
        return opening.copy()
    image=picture(index/30,timing,episode)
    # The reset occupies the final 20 frames. Finish on the exact opening frame.
    step=max(0,index-(end-20))
    if not step:
        return image
    for j,y in enumerate(range(0,H,12)):
        for k,x in enumerate(range(0,W,18)):
            if (j*7+k*11)%20<step:
                block=(x*F,y*F,min(W,x+18)*F,min(H,y+12)*F)
                image.paste(opening.crop(block),block)
    return image


def main(episode):
    parser=argparse.ArgumentParser()
    parser.add_argument("--timing",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--stills",action="store_true")
    args=parser.parse_args()
    timing=json.loads(args.timing.read_text())
    opening=picture(0,timing,episode)
    if args.stills:
        grid=Image.new("RGB",(W*5,H*2))
        times=[(a+b)*.5 for a,b,_ in timing["captions"]]
        times[-1]=timing["duration"]-1/30
        for i,t in enumerate(times):
            grid.paste(loop_frame(round(t*30),timing,episode,opening).resize((W,H)),
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
                job.stdin.write(loop_frame(index,timing,episode,opening).tobytes())
        finally:
            job.stdin.close()
        if job.wait():
            raise RuntimeError("Gameplay render failed.")
