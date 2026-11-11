import bootstrap,unittest,ast,math
import numpy as np
from PIL import Image,ImageOps
from backend.image_regions import official_view_layout,expanded_views

class RegionTests(unittest.TestCase):
 def test_coordinates_reconstruct_author_views(self):
  # Execute the author's unchanged pure sampling function without importing GPU packages.
  path=bootstrap.ROOT/'vendor/smaug/smaug_image_detect.py';tree=ast.parse(path.read_text(encoding='utf-8'));node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='views');namespace=dict(Image=Image,ImageOps=ImageOps,math=math,CROP=528,SIDE=576);exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
  for width,height in [(1200,800),(800,1200),(320,500),(512,512)]:
   y,x=np.indices((height,width));im=Image.fromarray(np.stack([x%256,y%256,(x+y)%256],axis=-1).astype('uint8'));layout=official_view_layout(im)
   method=Image.Resampling.LANCZOS if min(width,height)>576 else Image.Resampling.BICUBIC
   resized=im.resize((layout['width'],layout['height']),method) if im.size!=(layout['width'],layout['height']) else im
   for actual,box in zip(namespace['views'](im,3),layout['boxes']):self.assertEqual(actual.tobytes(),resized.crop(box).tobytes())
 def test_duplicate_views_not_claimed_independent(self):
  self.assertEqual(official_view_layout(Image.new('RGB',(512,512)))['distinct_regions'],1)
 def test_expanded_regions_stay_inside_original(self):
  images,trace=expanded_views(Image.new('RGB',(1080,1920)));self.assertEqual(len(images),10)
  for item in trace:
   x1,y1,x2,y2=item['box'];self.assertTrue(0<=x1<x2<=1080 and 0<=y1<y2<=1920)
 def test_orientation_layout_matches_rotated_shape(self):
  image=Image.new('RGB',(1200,800));exif=image.getexif();exif[274]=6;image.info['exif']=exif.tobytes();layout=official_view_layout(image);self.assertGreater(layout['height'],layout['width'])
if __name__=='__main__':unittest.main()
