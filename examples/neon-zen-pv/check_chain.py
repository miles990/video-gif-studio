from pathlib import Path
import cv2,json,hashlib,numpy as np
from PIL import Image,ImageDraw
p=Path(__file__).parent;records=[];sheet=Image.new('RGB',(960,4*310),(18,22,28));d=ImageDraw.Draw(sheet)
for n in range(2,6):
 prev=Image.open(p/f'segment-{n-1:02d}/last.png').convert('RGB'); supplied=Image.open(p/f'segment-{n:02d}/start.png').convert('RGB');cap=cv2.VideoCapture(str(p/f'segment-{n:02d}/generation/source.mp4'));ok,f=cap.read();cap.release();assert ok;first=Image.fromarray(cv2.cvtColor(f,cv2.COLOR_BGR2RGB));a=np.asarray(prev).astype(float);b=np.asarray(first).astype(float);r={'join':n-1,'previous_tail_equals_supplied_start':np.array_equal(a,np.asarray(supplied)),'decoded_boundary_rgb_mae':float(np.abs(a-b).mean())};records.append(r)
 for col,im in enumerate([prev,first]):
  im=im.copy();im.thumbnail((480,270));sheet.paste(im,(col*480,(n-2)*310));
 d.text((10,(n-2)*310+275),f'Join {n-1}: previous tail / next decoded first; RGB MAE {r["decoded_boundary_rgb_mae"]:.3f}',fill='white')
sheet.save(p/'joins.jpg');(p/'chain-qc.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records))
