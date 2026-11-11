"""Bounded diagnostic spatial sampling. Boxes are sampled areas, never forgery locations."""
from PIL import Image,ImageOps
def official_view_layout(image):
 """Coordinates match the audited author's 528/576 preprocessing, including overlap."""
 image=ImageOps.exif_transpose(image);w,h=image.size
 if min(w,h)>576:
  scale=576/min(w,h);w,h=round(w*scale),round(h*scale)
 elif min(w,h)<528:
  import math
  scale=528/min(w,h);w,h=math.ceil(w*scale),math.ceil(h*scale)
 cx,cy=(w-528)//2,(h-528)//2
 boxes=[(x,cy,x+528,cy+528) for x in [0,cx,w-528]] if w>=h else [(cx,y,cx+528,y+528) for y in [0,cy,h-528]]
 return dict(width=w,height=h,boxes=[list(b) for b in boxes],distinct_regions=len(set(boxes)),basis='Coordinates on proportionally resized image; sampled areas, not anomaly locations')
def expanded_views(image):
 image=ImageOps.exif_transpose(image).convert('RGB');w,h=image.size
 # Global preserves the original aspect ratio; the model processor handles its token budget.
 global_view=image.copy();global_view.thumbnail((1536,1536),Image.Resampling.LANCZOS)
 images=[global_view];trace=[dict(label='整图概览',box=[0,0,w,h],kind='global')]
 side=max(1,round(min(w,h)*.6));seen=set()
 for row,fraction_y in enumerate([0,.5,1]):
  for col,fraction_x in enumerate([0,.5,1]):
   x=round((w-side)*fraction_x);y=round((h-side)*fraction_y);box=(x,y,x+side,y+side)
   if box in seen:continue
   seen.add(box);images.append(image.crop(box).resize((528,528),Image.Resampling.LANCZOS));trace.append(dict(label=f'第{row+1}行第{col+1}列',box=list(box),kind='local'))
 return images,trace
