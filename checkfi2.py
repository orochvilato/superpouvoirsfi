# -*- coding: utf-8 -*-
import requests
import json
import jinja2
import os

candidats = []
import requests
response = requests.get('https://docs.google.com/spreadsheets/d/1vYBAic2wg80lbT9aXvnmFwOOJ8bHi7TJvKkviaRXMFs/export?format=csv&id=1vYBAic2wg80lbT9aXvnmFwOOJ8bHi7TJvKkviaRXMFs&gid=0')
import csv
from cStringIO import StringIO
f = StringIO(response.content)
reader = csv.reader(f,delimiter=',',quotechar='"')
for i,row in enumerate(reader):
    print row
    if i<=1:
        continue
    candidats.append({
        'dep':row[0],
        'depart':('000'+row[0])[-3:],
        'depart_nom':row[1],
        'circo':int(row[2]),
        'nom':row[3].decode('utf8'),
        'parti':row[4],
        'pct1T':row[5],
        'adv':row[6].decode('utf8'),
        'adv_parti':row[7],
        'adv_pct':row[8],
        'argument':row[9].decode('utf8'),
        'argument_source':row[10].decode('utf8')})

def checksize(url,size):
    import urllib, os
    site = urllib.urlopen(url)
    meta = site.info()
    return int(meta.getheaders("Content-Length")[0])==size


def renderTemplate(tpl_path, **context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(**context)


sp_dict= {}
def loadSPTag(sp_dict,tag):
    elts_dict = {'e':1}
    index = 0
    while len(elts_dict)>0:
        e = requests.get("https://melenshack.fr/MODELS/requestajax.php?size=1000&sort=hot&startIndex=%d&search=&pseudo=&tag=%s" % (index,tag),verify=False)
        elts_dict = dict((elt['id'],elt) for elt in json.loads(e.content))

        index += len(elts_dict)
        sp_dict.update(elts_dict)


loadSPTag(sp_dict,'second tour')
#loadSPTag(sp_dict,'superpouvoir')
#loadSPTag(sp_dict,'super pouvoir')
superpouvoir = sp_dict.values()


#with open('superpouv.json') as f:
#    superpouvoir = json.loads(f.read())

import os
shack_base = "https://melenshack.fr"
done = []
stats = {}
spcount = 0
visuels = {}
import re
#for vis in os.listdir('candidats'):
#    m = re.match(r'([0-9]+)_([0-9]+)_',vis)
#    if m:
#        key = tuple(m.groups())
#        visuels[key] = visuels.get(key,[]) + [dict(thumb='candidats/thumb_%s' % vis,img='candidats/%s' % vis)]

from fuzzywuzzy import fuzz
spcount = 0
for c in sorted(candidats,key=lambda c:(c['depart'],c['circo'])):
    c['sp'] = []
    if (c['dep'],str(c['circo'])) in visuels.keys():
        c['photo'] = visuels[(c['dep'],str(c['circo']))][0]
    for sp in superpouvoir:
        nom = c['nom'].upper()
        tags = ' '.join(sp['tags'].split(',')).upper()
        titre = sp['titre'].upper()
        fztags=fuzz.token_set_ratio(tags,nom)
        fztitre=fuzz.token_set_ratio(titre,nom)

        #fzcirco1=fuzz.partial_ratio('%s-%d' % (c['dep'],c['circo']),sp['titre'])
        #fzcirco2=fuzz.partial_ratio('%s - %de' % (c['dep'],c['circo']),sp['titre'])

        if fztags>90 or fztitre>90 or '%s-%d-titulaire' % (c['dep'],c['circo']) in sp['tags'].split(',') or '%s-%d' % (c['dep'],c['circo']) in sp['tags'].split(','):
            if 'Second tour' in sp['tags'].split(','):
                spcount += 1
            c['sp'].append({'thumb':shack_base+sp['urlThumbnail'],'img':shack_base+sp['urlSource']})



from jinja2 import Environment, PackageLoader, select_autoescape,FileSystemLoader
env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
#todos = [ {'titre':s['titre'],
#           'tags':s['tags'],
#           'thumb':shack_base+s['urlThumbnail'],
#           'url':'https://melenshack.fr/index.php?'+ '&'.join([ 'tag=%s' % tag for tag in s['tags'].split(',')])
#           } for s in superpouvoir if not s['id'] in done]
#templ = env.get_template('todotempl.html').render(todos=todos).encode('utf-8')

#stats = sorted([ {'dep':s['dep'], 'pct': 100*float(s['Titulaire']['n'])/s['Titulaire']['total']} for s in stats.values()],key=lambda d:d['pct'],reverse=True)
#statsdep = [ {'dep':s['dep'],'pos':i+1,'pct':'%.1f %%' % s['pct'] } for i,s in enumerate(stats)]
#open('todos.html','w').write(templ)
open('candidatsfi.html','w').write(env.get_template('tabletempl2.html').render(spcount=spcount,sptotal=len(candidats),candidats=sorted(candidats,key=lambda c:(c['depart'],c['circo']))).encode('utf-8'))
#open('stats.html','w').write(env.get_template('statstempl.html').render(stats=statsdep).encode('utf-8'))
