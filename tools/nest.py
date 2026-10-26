from shapely.geometry import Polygon
from shapely import affinity
def poly(p):
    sh=p.find('Shape'); pts=[(float(s.get('X')),float(s.get('Y'))) for s in sh.iter('ShapePoint')] if sh is not None else []
    L=float(p.get('Length')); W=float(p.get('Width'))
    if len(pts)<3: pts=[(0,0),(L,0),(L,W),(0,W)]
    return Polygon(pts).buffer(0)
def place(p,l,variant=('y','ccw')):
    g=poly(p); rot=float(l.get('Rotation')); fl=l.get('Flipped')=='True'
    if fl: g=affinity.scale(g, -1 if variant[0]=='x' else 1, -1 if variant[0]=='y' else 1, origin=(0,0))
    g=affinity.rotate(g, rot if variant[1]=='ccw' else -rot, origin=(0,0))
    minx,miny,_,_=g.bounds
    return affinity.translate(g, float(l.get('X'))-minx, float(l.get('Y'))-miny)
