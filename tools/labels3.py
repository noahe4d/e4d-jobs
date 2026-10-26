import json, math, os, qrcode, sys
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from loadopt import read_opt
from nest import place, poly
URL='https://noahe4d.github.io/e4d-jobs/tester-claude-learn/'
JOB='/mnt/user-data/uploads/tester Claude learn'
d=json.load(open('job.json'))
mats=sys.argv[1:] or ['White HMR 16mm']
# room-part lookup for QR keys
def keymap(r,mat):
    used=set(); m={}
    for op in r.findall('OptimizePart'):
        a=op.attrib; assy=a['AssyNo']; mz=('R1'+assy) if assy.startswith('N') else 'R1C'+assy
        L,W=float(a['Length']),float(a['Width'])
        c=[(p,x) for p in d['products'] if p['mz']==mz for x in p['parts'] if not x['view'] and x['k'] not in used and x['rep']==a['Name']]
        if not c: continue
        sc=lambda px: min(abs(px[1]['L']-L)+abs(px[1]['W']-W), abs(px[1]['L']-W)+abs(px[1]['W']-L))
        b=min(c,key=sc); used.add(b[1]['k']); m[a['PartID']]=(b[0],b[1])
    return m
W,H=100*mm,73*mm
fmt=lambda n: f"{round(n):,}" if abs(n-round(n))<0.05 else f"{n:,.1f}"
out=f"tester-Claude-learn-labels-{'-'.join(m.split()[0] for m in mats)}.pdf"
c=canvas.Canvas(out,pagesize=(W,H))
def fit(t,font,size,maxw):
    while c.stringWidth(t,font,size)>maxw and size>5: size-=0.5
    return size
def draw_poly(g,T,fill=False,lw=0.4):
    for geom in getattr(g,'geoms',[g]):
        pts=list(geom.exterior.coords); pth=c.beginPath(); pth.moveTo(*T(*pts[0]))
        for q in pts[1:]: pth.lineTo(*T(*q))
        pth.close(); c.setLineWidth(lw); c.drawPath(pth,stroke=1,fill=1 if fill else 0)
def part_drawing(op,bx,by,bw,bh):
    g=poly(op); minx,miny,maxx,maxy=g.bounds; sx,sy=maxx-minx or 1,maxy-miny or 1
    sc=min(bw/sx,bh/sy)*0.94; ox=bx+(bw-sx*sc)/2; oy=by+(bh-sy*sc)/2
    T=lambda a,b:(ox+(a-minx)*sc, oy+(b-miny)*sc)
    draw_poly(g,T,lw=0.9)
    for h in op.iter('OperationHole'):
        if h.get('Hide')=='True': continue
        x,y=T(float(h.get('X')),float(h.get('Y'))); r=max(float(h.get('Diameter'))*sc/2,0.5)
        c.circle(x,y,r,stroke=1,fill=0 if h.get('FlipSideOp')=='True' else 1)
    for lb in op.iter('OperationLineBore'):
        a=math.radians(float(lb.get('Ang'))); x0,y0=float(lb.get('X')),float(lb.get('Y'))
        for i in range(int(float(lb.get('Quan')))):
            x,y=T(x0+32*i*math.cos(a), y0+32*i*math.sin(a)); c.circle(x,y,max(float(lb.get('Diameter'))*sc/2,0.5),stroke=1,fill=1)
    from shapely.geometry import Point
    cx0,cy0=(minx+maxx)/2,(miny+maxy)/2
    for n,a,b,side in edges(op):
        c.setLineWidth(2.4); c.line(*T(*a),*T(*b))
        mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2; X1,Y1=T(mx,my); X0,Y0=T(cx0,cy0)
        dx,dy=X0-X1,Y0-Y1; dl=(dx*dx+dy*dy)**.5 or 1
        c.setFont('Helvetica-Bold',6); c.drawCentredString(X1+dx/dl*7,Y1+dy/dl*7-2,f"E{n}")
    c.setLineWidth(0.25)
    for gr in op.iter('OperationGroove'):
        x0,y0,l,a=float(gr.get('X')),float(gr.get('Y')),float(gr.get('Len')),math.radians(float(gr.get('Ang')))
        c.line(*T(x0,y0),*T(x0+l*math.cos(a),y0+l*math.sin(a)))
def sheet_drawing(sheet,P,me_loc,sw,sl,bx,by,bw,bh):
    sc=min(bw/sl,bh/sw); ox=bx; oy=by+(bh-sw*sc)/2
    T=lambda a,b:(ox+a*sc, oy+b*sc)
    c.setLineWidth(0.6); c.rect(ox,oy,sl*sc,sw*sc,stroke=1,fill=0)
    for l in sheet.findall('OptimizePartLocation'):
        me = l is me_loc
        c.setFillGray(0 if me else 1)
        draw_poly(place(P[l.get('PartID')],l),T,fill=True,lw=0.35)
    c.setFillGray(0)
import re as _re
_mt=open('/mnt/user-data/uploads/Data/MaterialTemplates.dat',encoding='utf-8',errors='replace').read()
def band_names(tname):
    i=_mt.find(f'<MaterialTemplate Name="{tname}"'); out={}
    if i<0: return out
    blk=_mt[i:_mt.find('</MaterialTemplate>',i)]
    for pt,mat in _re.findall(r'PartType="EdgeBand(\d?)" Mat="([^"]*)"',blk): out[int(pt or 1)]=mat
    return out
def edges(op):
    sh=op.find('Shape'); pts=list(sh.iter('ShapePoint')) if sh is not None else []
    res=[]
    for i,p in enumerate(pts):
        n=int(p.get('EBand') or 0)
        if n>0:
            q=pts[(i+1)%len(pts)]
            res.append((n,(float(p.get('X')),float(p.get('Y'))),(float(q.get('X')),float(q.get('Y'))),p.get('SideName') or ''))
    return res
rows=[]
for mat in mats:
    r=read_opt(f'{JOB}/{mat}.opt'); P={p.get('PartID'):p for p in r.findall('OptimizePart')}; km=keymap(r,mat)
    sw,sl=float(r.get('Width')),float(r.get('Length'))
    for si,s in enumerate(r.findall('OptimizeSheet'),1):
        for l in s.findall('OptimizePartLocation'):
            rows.append((mat,r,P,km,sw,sl,si,s,l))
n=len(rows); qrs=[]
for i,(mat,r,P,km,sw,sl,si,s,l) in enumerate(rows,1):
    op=P[l.get('PartID')]; a=op.attrib; prod,rx=km[a['PartID']]
    url=f"{URL}#{rx['k']}"; qrs.append(url)
    cab=prod['mz']; tex=os.path.splitext(os.path.basename(a.get('TextureName','').replace('\\','/')))[0]
    c.setLineWidth(0.6); c.setDash(1,1.5); c.roundRect(3.5*mm,3.5*mm,W-7*mm,H-7*mm,6,stroke=1,fill=0); c.setDash()
    nm=a['Name']+((' '+a['OpeningLetter']) if a.get('OpeningLetter') else '')
    c.setFont('Helvetica-Bold',fit(nm,'Helvetica-Bold',13,40*mm)); c.drawString(5*mm,H-10*mm,nm)
    c.setFont('Helvetica-Bold',fit(f"Cab: {cab}",'Helvetica-Bold',22,52*mm)); c.drawRightString(W-6*mm,H-15.5*mm,f"Cab: {cab}")
    lw=f"L= {fmt(float(a['Length']))} | W= {fmt(float(a['Width']))}"; c.setFont('Helvetica-Bold',fit(lw,'Helvetica-Bold',10,45*mm)); c.drawRightString(W-6*mm,H-25*mm,lw)
    eds=edges(op); bn=band_names(op.find('BandMatTmpSel').get('MissingTemplateName','') if op.find('BandMatTmpSel') is not None else '')
    if eds:
        codes=sorted({n for n,*_ in eds}); sides=', '.join(f"{side or '?'}" for n,a,b,side in eds)
        et=f"Edge: {len(eds)} side{'s' if len(eds)>1 else ''} ({sides}) " + ' '.join(f"E{n} {bn.get(n,'')}" for n in codes)
    else: et='Edge: none'
    c.setFont('Helvetica-Bold',fit(et,'Helvetica-Bold',7.5,46*mm)); c.drawRightString(W-6*mm,H-30*mm,et)
    job=f"Job: {d['job']}"; c.setFont('Helvetica-Bold',fit(job,'Helvetica-Bold',9,50*mm)); c.drawString(5*mm,H-22*mm,job)
    c.setFont('Helvetica-Bold',8); c.drawString(5*mm,H-27*mm,f"Room: {d['room']}")
    c.setFont('Helvetica',7); c.drawString(5*mm,H-31.5*mm,f"Material: {mat}")
    c.setFont('Helvetica',fit(f"Texture: {tex}",'Helvetica',8,50*mm)); c.drawString(5*mm,H-36*mm,f"Texture: {tex}")
    # bottom band: sheet layout | part drawing | QR
    sheet_drawing(s,P,l,sw,sl,5*mm,13.5*mm,40*mm,20*mm)
    part_drawing(op,47*mm,13*mm,20*mm,22*mm)
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=10,border=1); q.add_data(url); q.make(fit=True)
    qs=26*mm; qx=W-qs-5.5*mm; qy=8.5*mm
    c.drawImage(ImageReader(q.make_image().get_image()),qx,qy,qs,qs)
    c.setFont('Helvetica',5.5); c.drawCentredString(qx+qs/2,qy-2.6*mm,'Scan to see where it goes')
    c.setFont('Helvetica',7); c.drawString(5*mm,10*mm,f"Label: {i} / {n}")
    c.drawString(5*mm,5.8*mm,f"Sheet#: {si} | Part#: {l.get('PartNumber')}")
    c.showPage()
c.save(); json.dump(qrs,open(out+'.qr.json','w')); print(out,n)
