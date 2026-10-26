import re, xml.etree.ElementTree as ET
def read_xml(path):
    t=open(path,'rb').read().decode('utf-8','replace'); t=t[t.find('<?xml'):]
    t=re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);)","&amp;",t)
    return ET.fromstring(t)
