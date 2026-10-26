import json, sys
src, outf, title = sys.argv[1:4]
d=json.load(open(src))
for r in d['rooms']:
    for p in r['products']:
        for x in p['parts']: x.pop('ops',None)
t=open('template2.html').read().replace('__DATA__',json.dumps(d,separators=(',',':'))).replace('__TITLE__',title)
i=t.index('<div class="wrap">')
head='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
page=head+t[:i].replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')+'</head>\n<body>\n'+t[i:]+'\n</body>\n</html>\n'
page=page.replace('body{font-family','body{margin:0;font-family')
open(outf,'w').write(page); print(outf, len(page))
