import re, xml.etree.ElementTree as ET
def read_opt(path):
    b=open(path,'rb').read()
    t=b.decode('utf-16') if b'\x00<\x00' in b[:400] else b.decode('utf-8','replace')
    t=t[t.find('<'):]; t=re.sub(r'<\?xml[^>]*\?>','',t,1); return ET.fromstring(t)
