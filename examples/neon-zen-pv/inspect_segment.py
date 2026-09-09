import sys,cv2,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
p=Path(__file__).parent;n=int(sys.argv[1]);s=p/f'segment-{n:02d}';cap=cv2.VideoCapture(str(s/'generation/source.mp4'));frames=[]
while True:
 ok,f=cap.read()
 if not ok:break
 frames.append(Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB)))
frames[-1].save(s/'last.png')
indices=sorted(set([0,*range(12,len(frames),12),len(frames)-1]));board=Image.new('RGB',(1280,220*((len(indices)+3)//4)),'#15181b');d=ImageDraw.Draw(board)
for j,i in enumerate(indices):
 im=frames[i].resize((320,180));x=j%4*320;y=j//4*220;board.paste(im,(x,y));d.text((x+5,y+185),f'{i} / {i/24:.2f}s',fill='white')
board.save(s/'contact.jpg');(s/'inspection.json').write_text(json.dumps({'frames':len(frames),'fps':cap.get(cv2.CAP_PROP_FPS),'size':frames[0].size,'last_frame_index':len(frames)-1,'last_frame_sha256':hashlib.sha256((s/'last.png').read_bytes()).hexdigest()},indent=2))
print(s/'contact.jpg')
