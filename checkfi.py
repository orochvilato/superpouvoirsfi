import scrapy
import requests
import json

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


process.crawl(CandidatSpider)
process.start() # the script will block here until the crawling is finished
#with open('candidats.json','w') as f:
#    f.write(json.dumps(candidats))

e = requests.get("https://melenshack.fr/MODELS/requestajax.php?size=1000&sort=hot&startIndex=15&search=&pseudo=&tag=superpouvoir",verify=False)
superpouvoir = json.loads(e.content)
#with open('superpouv.json','w') as f:
#    f.write(json.dumps(superpouvoir))

#with open('candidats.json') as f:
#    candidats = json.loads(f.read())

#with open('superpouv.json') as f:
#    superpouvoir = json.loads(f.read())

shack_base = "https://melenshack.fr"
from fuzzywuzzy import fuzz
for c in sorted(candidats,key=lambda c:(c['depart'],c['circo'])):
    c['sp'] = []
    for sp in superpouvoir:
        nom = c['nom'].upper()
        tags = ' '.join(sp['tags'].split(',')).upper()
        titre = sp['titre'].upper()
        fztags=fuzz.token_set_ratio(tags,nom)
        fztitre=fuzz.token_set_ratio(titre,nom)

        #fzcirco1=fuzz.partial_ratio('%s-%d' % (c['dep'],c['circo']),sp['titre'])
        #fzcirco2=fuzz.partial_ratio('%s - %de' % (c['dep'],c['circo']),sp['titre'])

        if fztags>90 or fztitre>90:
            c['sp'].append({'thumb':shack_base+sp['urlThumbnail'],'img':shack_base+sp['urlSource']})


from jinja2 import Template
template =Template(open('tabletempl.html').read().decode('utf8'))
open('candidatsfi.html','w').write(template.render(candidats=sorted(candidats,key=lambda c:(c['depart'],c['circo']))).encode('utf-8'))
