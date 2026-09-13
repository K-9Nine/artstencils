from PIL import Image, ImageDraw, ImageFilter
import random
random.seed(1)
W,H = 900, 950
im = Image.new("RGB",(W,H),(232,226,214))
d = ImageDraw.Draw(im)
# noisy sky/ground texture
for _ in range(20000):
    x,y=random.randrange(W),random.randrange(H); v=random.randint(-14,14)
    d.point((x,y),(232+v,226+v,214+v))
# buildings (pink) with dark windows
for bx in [0,520]:
    d.rectangle([bx,180,bx+330,440],fill=(214,180,170))
    d.rectangle([bx,160,bx+330,185],fill=(120,110,105))  # roof line
    for wx in range(bx+30,bx+300,90):
        for wy in [220,320]:
            d.rectangle([wx,wy,wx+45,wy+60],fill=(150,140,135))
d.rectangle([110,360,150,440],fill=(200,70,50))  # red door
# chimneys
for cx in [70,180,700,800]:
    d.rectangle([cx,120,cx+22,180],fill=(190,140,120))
# road
d.rectangle([0,440,W,470],fill=(150,150,145))
d.rectangle([0,760,W,800],fill=(140,140,135))
# cab: black box with white window island
d.polygon([(360,80),(640,60),(640,520),(480,520),(480,170)],fill=(35,38,40))
d.rectangle([500,110,600,190],fill=(232,226,214))
# wheels: black rim with white disc inside (island)
for (cx,cy,r) in [(260,640,80),(580,620,105)]:
    d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=(30,30,30))
    d.ellipse([cx-r+14,cy-r+14,cx+r-14,cy+r-14],fill=(225,220,210))
    d.ellipse([cx-10,cy-10,cx+10,cy+10],fill=(30,30,30))
# frame
d.line([(260,640),(400,470),(480,520)],fill=(30,30,30),width=12)
d.line([(330,330),(400,470)],fill=(30,30,30),width=10)
# rider: brown coat, bowler
d.rectangle([390,230,470,420],fill=(140,110,80))
d.ellipse([395,175,455,235],fill=(215,190,170))
d.rectangle([390,160,460,185],fill=(30,30,30))
# small figure + dog
d.rectangle([700,380,712,440],fill=(60,60,60)); d.ellipse([740,425,760,440],fill=(60,60,60))
im = im.filter(ImageFilter.GaussianBlur(0.8))
im.save("test_scene.png"); print("ok")
