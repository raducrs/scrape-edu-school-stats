# -*- coding: utf-8 -*-
"""
Created on Tue Oct 20 22:51:29 2020

@author: Radu
"""

from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
import os
import json
import time
import random

#%%
# Variables
today_date = '2020-11-11'
home_dir = './'
slack_hook = '<slack-hook>'
home_url =  "https://www.edu.ro"
url = "https://www.edu.ro/comunicate-de-presa"
#%%


#%%

def convertToSearchableDate(dst):
    month_full = { '10': 'octombrie', '11' :'noiembrie'}
    month_short = { '10': 'oct', '11': 'noi'}
    
    comp = dst.split('-');
    regstr = f'{comp[2]}\s*({month_full[comp[1]]}|{month_full[comp[1]]})\s*'
    return re.compile(regstr)


def isEligible(test_title,search_date):
    tit_re = re.compile('(buletin).{0,6}(informativ).{0,20}(scenari)')
    title_nice = re.sub('\W{2,10}',' ',test_title.lower())
    sdt_re = convertToSearchableDate(search_date)
    if sdt_re.search(test_title.lower()) is not None and tit_re.search(title_nice) is not None:
        return True
    else:
        return False


#%%
def getFilenameFromTitle(title):
    return re.sub('\W','',title.lower()) + '.txt'

def was_not_parsed(title,home_dir):
    file_name = getFilenameFromTitle(title)
    path = os.path.join(home_dir,file_name)
    return not os.path.exists(path)


#%%

def anounce(t,a):
    r = requests.post(slack_hook,json={ 'text' : f'Am gasit {t} la {home_url}{a}'})

    
    
#%%
def search_for_number_pattern(scen,text):
    pat = re.compile('([0-9.]+).{0,150}'+scen)

    mtch = pat.search(text)
    if mtch is not None:
        try:
            number_txt = mtch.group(1).replace('.','')
            return int(number_txt)
        except :
            return -2
    else:
        return -1
    
def search_for_number_pattern_extended(scen1,scen2,text):
    pat = re.compile('([0-9.]+).{0,50}'+scen1+'.{0,30}'+scen2)

    mtch = pat.search(text)
    if mtch is not None:
        try:
            number_txt = mtch.group(1).replace('.','')
            return int(number_txt)
        except :
            return -2
    else:
        return -1
#%%

def post_json(t,a,s1,s2,s3, s3_covid, s3_lockdown, dt):
    body = {
            "date": dt,
            "sourceUrl": a,
            "sourceName": ("Ministerul Educației și Cercetării - " + t),
            "green": s3,
            "yellow": s2,
            "red": s1,
            "redCovid": s3_covid,
            "redLockdown": s3_lockdown
        }
    print('******'*6)
    print(body)
    requests.post(slack_hook,json={ 'text' : json.dumps(body)})
   
#%%
test_url = 'https://www.edu.ro/buletin-informativ-dinamica-scenariilor-de-func%C8%9Bionare-unit%C4%83%C8%9Bilor-de-%C3%AEnv%C4%83%C8%9B%C4%83m%C3%A2nt-preuniversitar-19'
def visit(url,t,a):
    req = requests.get(url)
    soup = BeautifulSoup(req.text, "html.parser")
    all_p = soup.find_all('p')
    s1 = None
    s2 = None
    s3 = None
    s3_covid = None
    s3_lockdown = None
    for para in all_p:
        red_found = search_for_number_pattern('scenariul 3',para.text.lower())
        if red_found > 0:
            if s1 is None:
                s1 = red_found
        yellow_found = search_for_number_pattern('scenariul 2',para.text.lower())
        if yellow_found > 0:
            if s2 is None:
                s2 = yellow_found
        green_found = search_for_number_pattern('scenariul 1',para.text.lower())
        if green_found > 0:
            if s3 is None:
                s3 = green_found
                
        red_covid_found = search_for_number_pattern_extended('cazurilor','covid',para.text.lower())
        if red_covid_found > 0:
            if s3_covid is None:
                s3_covid = red_covid_found
        # replace with a context search        
        red_lockdown_found = search_for_number_pattern_extended('apar din cauza ratei','de inciden',para.text.lower())
        if red_lockdown_found > 0:
            if s3_lockdown is None:
                s3_lockdown = red_lockdown_found
    
    
    if s1 is not None or s2 is not None or s3 is not None:
        post_json(t, f'{home_url}{a}', s1, s2, s3, s3_covid, s3_lockdown, today_date)

#%%
host="5.4.2.2"
def scrape(url,home_dir,today_date):
    global host
    headers = {
        "Cache-Control": "max-age=0",
        "Pragma": "no-cache",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.80 Safari/537.36 Edg/86.0.622.43",
        "Referer": "https://www.edu.ro/",
        "Connection": "keep-alive",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": host
        }
    req = requests.get(url,headers=headers)
    print(req.headers)
    if not req.headers['X-Cache'] == 'MISS':
        print('******'*7)
        print('received cached version')
        host= f'{str(random.randint(1,254))}.{str(random.randint(0,255))}.{str(random.randint(0,255))}.{str(random.randint(0,255))}'
    soup = BeautifulSoup(req.text, "html.parser")

    titles = soup.find_all('h2', {'class': ['node-title']})
    
    anchors = list(map(lambda t: (' '.join(t.a.contents), t.a['href']) if t.a is not None else ('',''), titles))
    candidate_a = list(filter(lambda a: isEligible(a[0],today_date),anchors))
    not_visited_a = list(filter(lambda a: was_not_parsed(a[0],home_dir),candidate_a))
    
    for t,a in not_visited_a:
        anounce(t,a)
        file_name = getFilenameFromTitle(t)
        path = os.path.join(home_dir,file_name)
        with open(path,'w',encoding='utf-8') as f:
            f.write(t + '\n')
            f.write(f'{home_url}{a}')
        print(f'{home_url}{a}')
        visit(f'{home_url}{a}',t,a)
scrape(url,home_dir,today_date)
    
#%%

check_every = 10* 60 #seconds
while True:
    try:
        scrape(url,home_dir,today_date)
        print('nothing found')
    except Exception as e:
       print(e)
    time.sleep(check_every)
#%%
