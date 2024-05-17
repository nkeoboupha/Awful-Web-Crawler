import requests
import os
import sqlite3
from bs4 import BeautifulSoup
import logging
import re
import zipfile
import urllib.robotparser
import hashlib
from PIL import Image
from io import BytesIO
import json
import time
import logging

logging.basicConfig(level = logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def normalize_src(src, url):
    result = re.match(r"^http(s)?://(.)*", src)
    if result:
        return result.group(0)
    result = re.match(r'^//(.)*', src)
    if result:
        protocol = re.match(r'^http(s)?:', url)
        if protocol:
            return protocol.group(0) + result.group(0)
    #May result in additional forward slashes
    #These are ignored by requests, probably
    result = re.match(r'^/[^/](.)*', src)
    if result:
        return url + result.group(0)
    return None

def get_urls(html):
    return re.findall(r'href="(https?://\S*)"', html)

def get_html(url):
    return requests.get(url).text

def get_imgs(html):
    soup = BeautifulSoup(html, "lxml")
    return soup.find_all('img')

def parse_imgs(imgs, url):
    batch = []
    for img in imgs:
        src = normalize_src(img.get('src'), url)
        alt = img.get('alt')
        if src and alt:
            batch.append([src, alt])
    return batch

def setup_db(seed_url):
    con = sqlite3.connect('proj.db')
    cur = con.cursor()
    cur.execute("CREATE TABLE urls(url TEXT PRIMARY KEY, visited INTEGER) WITHOUT ROWID")
    cur.execute("CREATE TABLE hashes(hash BLOB PRIMARY KEY, hrefs TEXT, alts TEXT) WITHOUT ROWID")
    cur.execute(f"INSERT INTO urls VALUES ('{seed_url}', 0)")
    con.commit()
    con.close()

def setup_file_struct():
    os.mkdir('photo')

def get_domain(url):
    return re.match(r"https?://([^/]*)", url).group(1)

def get_protocol(url):
    return re.match(r'https?://', url).group(0)

def get_robots_url(url):
    return get_protocol(url) + get_domain(url) + '/robots.txt'

def can_scrape(user_agent, url):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(get_robots_url(url))
    rp.read()
    cd = rp.crawl_delay(user_agent)
    rr = rp.request_rate(user_agent)
    if cd:
        logging.info(f'Waiting for {cd}-second crawl delay')
        time.sleep(cd)
    if rr:
        logging.info(f'Waiting for {rr[0]/rr[1]}-second request rate')
        time.sleep(rr[0] / rr[1])
    return rp.can_fetch(user_agent, url)

def get_hash(bin_photo):
    if not bin_photo:
        return None
    os.chdir('photo')
    try:
        photo = Image.open(BytesIO(bin_photo))
        photo.save('img.png')
        with open('img.png', 'rb') as img:
            os.chdir('..')
            return hashlib.file_digest(img, 'sha256')
    except:
        os.chdir('..')
        return None

if __name__ == "__main__":
    seed_url = 'https://en.wikipedia.org'
    user_agent = "MyHorribleBot" 
    sesh = requests.session()
    sesh.headers.update({'User-Agent' : user_agent})
    if "proj.db" not in os.listdir() and "proj.zip" not in os.listdir() and 'photo' not in os.listdir():
        setup_db(seed_url)
        setup_file_struct()
    con = sqlite3.connect('proj.db')
    cur = con.cursor()
    while True:
        url = cur.execute(f"SELECT url FROM urls WHERE visited = 0").fetchone()[0] 
        cur.execute(f"UPDATE urls SET visited = 1 WHERE url = '{url}'")
        if can_scrape(user_agent, url):
            resp = sesh.get(url)
            while resp.status_code == 429:
                logging.info('Code 429 encountered')
                time.sleep(int(resp.headers['Retry-After']))
                if can_scrape(user_agent, url):
                    resp = sesh.get(url)
                else:
                    raise Exception('Permission Revoked')
            html = resp.text
            for link in get_urls(html):
                if can_scrape(user_agent, link):
                    cur.execute(f"INSERT INTO urls VALUES ('{link}', 0) ON CONFLICT DO NOTHING")
            imgs = parse_imgs(get_imgs(html), url)
            for img in imgs:
                if can_scrape(user_agent, img[0]):
                    resp = sesh.get(img[0])
                    while resp.status_code == 429:
                        time.sleep(int(resp.headers['Retry-After']))
                        logging.info('Code 429 encountered')
                        if can_scrape(user_agent, img[0]):
                            resp = sesh.get(img[0])
                        else:
                            raise Exception('Permission Revoked')
                    sha = get_hash(resp.content)
                    if sha:
                        values = cur.execute("SELECT * FROM hashes WHERE hash = (?)", (sha.digest(),)).fetchone()
                        if not values:
                            cur.execute("INSERT INTO hashes VALUES (?, ?, ?)", (sha.digest(), img[0], img[1]))
                        else:
                            cur.execute("DELETE FROM hashes WHERE hash = (?)", (sha.digest(),))
                            cur.execute("INSERT INTO hashes VALUES (?, ?, ?)", (sha.digest(), values[1] + '\n' + img[0], values[2] + '\n' + img[1]))
        con.commit()
