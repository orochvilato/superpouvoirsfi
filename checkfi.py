# -*- coding: utf-8 -*-
import scrapy
import requests
import json
import jinja2
import os

from scrapy.crawler import CrawlerProcess

candidats = []

class CandidatSpider(scrapy.Spider):
    name = "candidats"
    base_url = 'https://legislatives2017.lafranceinsoumise.fr'

    def start_requests(self):
        urls = ['https://legislatives2017.lafranceinsoumise.fr']

        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_main)

    def parse_main(self, response):
        for opt in response.xpath("//select[@id='dep']/option"):
            dpt = opt.xpath('@value').extract()[0]

            request = scrapy.Request(url="%s/departement/%s" % (self.base_url,dpt), callback=self.parse_departement)
            request.meta['dep'] = opt.xpath('text()').extract()[0]
            yield request

    def parse_departement(self, response):
        for circ in response.xpath("//a[contains(@href,'circonscription')]/@href"):
            circurl = circ.extract()
            request = scrapy.Request(url="%s%s" % (self.base_url,circurl), callback=self.parse_circo)
            request.meta['dep'] = response.meta['dep']
            yield request

    def parse_circo(self, response):

        liens = response.xpath("//div[contains(@class,'liens')]//a[contains(@href,'mailto:')]/text()").extract()

        for cand in response.xpath("//div[contains(@class,'candidat col-sm-6')]"):
            depart = response.url.split('/')[-3]
            circo = response.url.split('/')[-1]
            nom = cand.xpath("div[@class='nom']/h4/text()").extract()
            role = cand.xpath("div[@class='nom']/text()").extract()[1].replace('\n','').strip()
            bio = cand.xpath("div[@class='bio']/p/text()").extract()
            photo = cand.xpath("div[@class='photo']/img/@src").extract()
            candidats.append({
             'url':response.url,
             'dep':depart,
             'depart':('000'+depart)[-3:],
             'depart_nom':response.meta['dep'],
             'circo':int(circo),
             'nom':nom[0] if nom[0] else '',
             'role':role,
             'mail':liens[0] if liens else "",
             'bio':bio[0] if bio else "",
             'photo':(self.base_url+photo[0]) if photo else ''})



process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
})
DEBUG = False
if not DEBUG:
    process.crawl(CandidatSpider)
    process.start() # the script will block here until the crawling is finished
    #with open('candidats.json','w') as f:
    #    f.write(json.dumps(candidats))
else:
    with open('candidats.json') as f:
        candidats = json.loads(f.read())

def renderTemplate(tpl_path, **context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(**context)


sp_dict= {}
def loadSPTag(sp_dict,tag):
    elts_dict = {'e':1}
    index = 1
    while len(elts_dict)>0:
        e = requests.get("https://melenshack.fr/MODELS/requestajax.php?size=1000&sort=hot&startIndex=%d&search=&pseudo=&tag=%s" % (index,tag),verify=False)
        elts_dict = dict((elt['id'],elt) for elt in json.loads(e.content))

        index += len(elts_dict)
        sp_dict.update(elts_dict)


loadSPTag(sp_dict,'superpouvoir')
loadSPTag(sp_dict,'super pouvoir')
superpouvoir = sp_dict.values()


#with open('superpouv.json') as f:
#    superpouvoir = json.loads(f.read())

shack_base = "https://melenshack.fr"
done = []
stats = {}
spcount = 0
from fuzzywuzzy import fuzz
for c in sorted(candidats,key=lambda c:(c['depart'],c['circo'])):
    if not c['depart_nom'] in stats.keys():
        stats[c['depart_nom']] = { 'dep':c['depart_nom'],'Titulaire':{'n':0,'total':0},u'Suppléant':{'n':0,'total':0}}
    c['sp'] = []
    stats[c['depart_nom']][c['role']]['total'] += 1
    for sp in superpouvoir:
        nom = c['nom'].upper()
        tags = ' '.join(sp['tags'].split(',')).upper()
        titre = sp['titre'].upper()
        fztags=fuzz.token_set_ratio(tags,nom)
        fztitre=fuzz.token_set_ratio(titre,nom)

        #fzcirco1=fuzz.partial_ratio('%s-%d' % (c['dep'],c['circo']),sp['titre'])
        #fzcirco2=fuzz.partial_ratio('%s - %de' % (c['dep'],c['circo']),sp['titre'])

        if fztags>90 or fztitre>90 or '%s-%d-%s' % (c['dep'],c['circo'],'titulaire' if c['role'][0]=='T' else 'suppleant') in sp['tags'].split(','):
            spcount += 1
            if not c['sp']:
                stats[c['depart_nom']][c['role']]['n'] += 1
            done.append(sp['id'])
            c['sp'].append({'thumb':shack_base+sp['urlThumbnail'],'img':shack_base+sp['urlSource']})



from jinja2 import Environment, PackageLoader, select_autoescape,FileSystemLoader
env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
todos = [ {'titre':s['titre'],
           'tags':s['tags'],
           'thumb':shack_base+s['urlThumbnail'],
           'url':'https://melenshack.fr/index.php?'+ '&'.join([ 'tag=%s' % tag for tag in s['tags'].split(',')])
           } for s in superpouvoir if not s['id'] in done]
templ = env.get_template('todotempl.html').render(todos=todos).encode('utf-8')

stats = sorted([ {'dep':s['dep'], 'pct': 100*float(s['Titulaire']['n'])/s['Titulaire']['total']} for s in stats.values()],key=lambda d:d['pct'],reverse=True)
statsdep = [ {'dep':s['dep'],'pos':i+1,'pct':'%.1f %%' % s['pct'] } for i,s in enumerate(stats)]
open('todos.html','w').write(templ)
open('candidatsfi.html','w').write(env.get_template('tabletempl.html').render(spcount=spcount,sptotal=len(candidats),candidats=sorted(candidats,key=lambda c:(c['depart'],c['circo']))).encode('utf-8'))
open('stats.html','w').write(env.get_template('statstempl.html').render(stats=statsdep).encode('utf-8'))
