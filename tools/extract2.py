import json, math, sys
import numpy as np
from load import read_xml
def R(axis, deg):
    t=math.radians(deg); c,s=math.cos(t),math.sin(t)
    if axis=='X': return np.array([[1,0,0],[0,c,-s],[0,s,c]])
    if axis=='Y': return np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])
def f(v):
    try: return float(v)
    except: return 0.0
def thick(cp, prod):
    c=cp.get('Comment').lower(); n=cp.get('Name').lower(); t=cp.get('Type')
    if c.startswith('16mm'): return 16
    if c.startswith('12mm') or '12mm' in c and ('view' in c or 'display' in c) or ('skin' in n): return 12
    if t in ('Door','DrawerFront') or n.startswith('door'): return 18
    return 16
def ops(cp):
    o=[]
    for po in cp.iter('PartOpsXml'):
        for e in po:
            a=e.attrib
            if a.get('Hide')=='True': continue
            if e.tag=='OperationHole': o.append(['h',f(a.get('X')),f(a.get('Y')),f(a.get('Diameter') or a.get('Dia') or 5)])
            elif e.tag=='OperationGroove': o.append(['g',f(a.get('X')),f(a.get('Y')),f(a.get('Len')),f(a.get('Width')),f(a.get('Ang'))])
    return o
import os, re as _re
import re
def extract_room(path, rn):
    room=read_xml(path); out=[]
    M2T=np.array([[1,0,0],[0,0,1],[0,-1,0]])  # mozaik(x,y,z)->three(x,z,-y)
    WL=list(room.find('Walls')) if room.find('Walls') is not None else []
    def wall_place(a):
        # Product sits on wall <index>_<side> (index = position in the Walls list, 1-based).
        # Side 1: x runs from the wall start, cabinet on the right-hand (room) side.
        # Side 2: other face of the wall, x runs from the wall end, turned 180 degrees.
        m=re.fullmatch(r'(\d+)_(\d+)',a.get('Wall','') or '')
        if not m or not (1<=int(m.group(1))<=len(WL)): return np.eye(3),np.zeros(3),None,1
        wi,side=int(m.group(1)),int(m.group(2)); w=WL[wi-1].attrib
        A=math.radians(f(w.get('Ang'))); d=np.array([math.cos(A),math.sin(A),0]); n=np.array([math.sin(A),-math.cos(A),0])
        o=np.array([f(w.get('PosX')),f(w.get('PosY')),0.0])
        if side==2: return R('Z',f(w.get('Ang'))+180),o+f(w.get('Len'))*d-f(w.get('Thickness'))*n,wi,2
        return R('Z',f(w.get('Ang'))),o,wi,1
    for pi,p in enumerate(room.find('Products')):
        a=p.attrib; X=f(a['X']); E=f(a['Elev']); D=f(a['Depth']); O=f(a['Outset'])
        WR,WO,wi,side=wall_place(a)
        if f(a.get('Rot',0)): WR=WR@R('Z',-f(a['Rot']))
        prod={'id':pi+1,'cab':a['CabNo'],'numbered':a['Numbered']=='True','name':a['ProdName'],'notes':a.get('Notes',''),
              'W':f(a['Width']),'H':f(a['Height']),'D':D,'X':X,'Elev':E,'wall':wi,'side':side,'parts':[]}
        for cp in p.find('CabProdParts'):
            c=cp.attrib
            if f(c['Quan'])<=0 or f(c['L'])<=0 or f(c['W'])<=0: continue
            if c['Type'] in ('Metal','SPECIAL'): continue
            Rm=np.eye(3)
            for ax,an in ((c['R1'],c['A1']),(c['R2'],c['A2']),(c['R3'],c['A3'])):
                if f(an): Rm=R(ax,f(an))@Rm
            pos=np.array([X+f(c['X']), (D+O)*-1+f(c['Y']), E+f(c['Z'])])  # y: wall at 0 => y_world = y - (D+O)
            # three coords
            Rt=M2T@WR@Rm; pt=M2T@(WO+WR@pos)
            sh=cp.find('PartShapeXml'); pts=[(f(s.get('X')),f(s.get('Y'))) for s in sh] if sh is not None else []
            prod['parts'].append({'name':c['Name'],'rep':c.get('ReportName',''),'type':c['Type'],'view':c['UsageType']=='2','cutOnly':c['UsageType']=='1','q':f(c['Quan']),'comment':c['Comment'],
                'L':f(c['L']),'W':f(c['W']),'T':thick(cp,p),'rad':f(c['Radius']),'shape':pts,
                'ops':ops(cp),'m':[round(v,4) for v in Rt.T.flatten().tolist()], 'p':[round(v,2) for v in pt.tolist()]})
        out.append(prod)
    
    for p in out:
        p['room']=rn; p['mz']=f"R{rn}{'C' if p['numbered'] else 'N'}{p['cab']}"
        p['label']=f"Cab {p['mz']}"
        for i,x in enumerate(p['parts']): x['k']=f"r{rn}c{p['id']}-p{i+1}"
    ws=room.find('Walls'); w=ws[0] if ws is not None and len(ws) else None
    wl=f(w.get('Len')) if w is not None else max([p['X']+p['W'] for p in out] or [1000])
    wh=f(w.get('Height')) if w is not None else max([p['Elev']+p['H'] for p in out]+[2400])
    walls={str(i+1):{'len':f(w.get('Len')),'h':f(w.get('Height'))} for i,w in enumerate(WL)}
    return {'n':rn,'name':room.get('Name'),'wallLen':wl,'wallH':wh,'walls':walls,'products':out}
if __name__=='__main__':
    job,folder,outf=sys.argv[1:4]
    files=sorted([fn for fn in os.listdir(folder) if _re.fullmatch(r'Room[1-9]\d*\.des',fn)],key=lambda s:int(s[4:-4]))
    rooms=[extract_room(os.path.join(folder,fn),int(fn[4:-4])) for fn in files]
    json.dump({'job':job,'rooms':rooms},open(outf,'w'),separators=(',',':'))
    for r in rooms: print(r['n'],r['name'],len(r['products']),sum(len(p['parts']) for p in r['products']))
