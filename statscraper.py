import os
import re
import sqlite3
import urllib2

from bs4 import BeautifulSoup
from contextlib import closing
from decimal import Decimal

DATABASE = 'wbh.db'
ROOT = 'http://worldbaseballhierarchy.com/lgreports/news/html/'

class PITCHING_FIELDS:
    LEAGUE, \
    AGE, \
    G, \
    GS, \
    W, \
    L, \
    SV, \
    ERA, \
    IP, \
    HA, \
    R, \
    ER, \
    HR, \
    BB, \
    K, \
    CG, \
    SHO, \
    WHIP, \
    BABIP, \
    VORP, \
    WAR, \
    ERAP = range(22)

PITCHING_STATS = {
    'G': PITCHING_FIELDS.G,
    'GS': PITCHING_FIELDS.GS,
    'W': PITCHING_FIELDS.W,
    'L': PITCHING_FIELDS.L,
    'SV': PITCHING_FIELDS.SV,
    'IP': PITCHING_FIELDS.IP,
    'HA': PITCHING_FIELDS.HA,
    'R': PITCHING_FIELDS.R,
    'ER': PITCHING_FIELDS.ER,
    'HR': PITCHING_FIELDS.HR,
    'BB': PITCHING_FIELDS.BB,
    'K': PITCHING_FIELDS.K,
    'CG': PITCHING_FIELDS.CG,
    'SHO': PITCHING_FIELDS.SHO,
    'VORP': PITCHING_FIELDS.VORP,
    'WAR': PITCHING_FIELDS.WAR
}

PITCHING_DECIMALS = set(['IP', 'VORP', 'WAR'])

class BATTING_FIELDS:
    LEAGUE, \
    AGE, \
    G, \
    AB, \
    H, \
    _2B, \
    _3B, \
    HR, \
    RBI, \
    R, \
    BB, \
    HP, \
    SF, \
    K, \
    SB, \
    CS, \
    AVG, \
    OBP, \
    SLG, \
    OPS, \
    OPSP, \
    VORP, \
    WAR = range(23)

BATTING_STATS = {
    'G': BATTING_FIELDS.G,
    'AB': BATTING_FIELDS.AB,
    'H': BATTING_FIELDS.H,
    '_2B': BATTING_FIELDS._2B,
    '_3B': BATTING_FIELDS._3B,
    'HR': BATTING_FIELDS.HR,
    'RBI': BATTING_FIELDS.RBI,
    'R': BATTING_FIELDS.R,
    'BB': BATTING_FIELDS.BB,
    'HP': BATTING_FIELDS.HP,
    'SF': BATTING_FIELDS.SF,
    'K': BATTING_FIELDS.K,
    'SB': BATTING_FIELDS.SB,
    'CS': BATTING_FIELDS.CS,
    'VORP': BATTING_FIELDS.VORP,
    'WAR': BATTING_FIELDS.WAR
}

BATTING_DECIMALS = set(['VORP', 'WAR'])

def scrape():
    with closing(sqlite3.connect(DATABASE)) as db:
        for player_id in range(18170):
            try:
                response = urllib2.urlopen(ROOT + '/players/player_%d.html' % player_id)
                html = response.read()
                soup = BeautifulSoup(html)
                if soup.find(text=re.compile('BATTING RATINGS')) is not None:
                    batting_stats(db, soup, player_id)
                elif soup.find(text=re.compile('PITCHING RATINGS')) is not None:
                    pitching_stats(db, soup, player_id)
                    
            except urllib2.HTTPError:
                pass

def pitching_stats(db, soup, player_id):
    name = soup.find('div', class_='reptitle').text
    name = name[name.find(' ') + 1:name.find('#') - 1].strip()
    table = soup.find_all('table', class_='sortable')[1]
    rows = table.find_all('tr', class_='hsx')
    if len(rows) == 0:
        return
    result = {}
    for row in rows:
        values = [th.string for th in row.find_all('th')]
        add_pitching_stats(result, values)
    if result['IP'] == 0:
        return
    print player_id
    compile_pitching_stats(result)
    cur = db.cursor()
    cur.execute('''
        insert or replace into pitching_stats
        (player_id, name, g, gs, w, l, sv, ip, ha, r, er, hr, bb, k, cg, sho, vorp, war, era, whip)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, name, result['G'], result['GS'], result['W'], result['L'], result['SV'], result['IP'],
              result['HA'], result['R'], result['ER'], result['HR'], result['BB'], result['K'], result['CG'],
              result['SHO'], result['VORP'], result['WAR'], result['ERA'], result['WHIP']))

def add_pitching_stats(result, values):
    for key in PITCHING_STATS:
        if key not in PITCHING_DECIMALS:
            result[key] = result.get(key, 0) + int(values[PITCHING_STATS[key]])
        elif key == 'IP':
            result[key] = round(result.get(key, 0) + float(values[PITCHING_STATS[key]]), 1)
            if result[key] % 1 > 0.25:
                result[key] = round(result[key] + 0.7, 1)
        else:
            result[key] = round(result.get(key, 0) + float(values[PITCHING_STATS[key]]), 1)

def compile_pitching_stats(result):
    adjusted_ip = result['IP']
    if adjusted_ip % 10 == 0.1:
        adjusted_ip += 0.2333
    elif adjusted_ip % 10 == 0.2:
        adjusted_ip += 0.4666
    ER = result['ER']
    HA = result['HA']
    BB = result['BB']
    K = result['K']
    outs = round(adjusted_ip * 3)
    result['ERA'] = round(ER * 9 / adjusted_ip, 2)
    result['WHIP'] = round((HA + BB) / adjusted_ip, 2)

def batting_stats(db, soup, player_id):
    name = soup.find('div', class_='reptitle').text
    name = name[name.find(' ') + 1:name.find('#') - 1].strip()
    data_line = soup.find(text=re.compile('BATS:'))
    position = data_line.split(' ')[0]

    header_table = soup.find(text=re.compile('Career Batting Stats'))
    table = header_table.find_parents('table')[0].find_next_sibling()
    rows = table.find_all('tr', class_='hsx')
    if len(rows) == 0:
        return
    result = {}
    for row in rows:
        values = [th.string for th in row.find_all('th')]
        add_batting_stats(result, values)
    if result['AB'] == 0:
        return
    print player_id
    compile_batting_stats(result)
    cur = db.cursor()
    cur.execute('''
        insert or replace into batting_stats
        (player_id, name, position, g, ab, h, double, triple, hr, rbi, r, bb, hp, sf, k, sb, cs, vorp, war, avg, obp, slg, ops)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, name, position, result['G'], result['AB'], result['H'], result['_2B'], result['_3B'], result['HR'],
              result['RBI'], result['R'], result['BB'], result['HP'], result['SF'], result['K'], result['SB'],
              result['CS'], result['VORP'], result['WAR'], result['AVG'], result['OBP'], result['SLG'], result['OPS']))
    db.commit()

def add_batting_stats(result, values):
    for key in BATTING_STATS:
        if key not in BATTING_DECIMALS:
            result[key] = result.get(key, 0) + int(values[BATTING_STATS[key]])
        else:
            result[key] = round(result.get(key, 0) + float(values[BATTING_STATS[key]]), 1)

def compile_batting_stats(result):
    AB = result['AB']
    H = result['H']
    _2B = result['_2B']
    _3B = result['_3B']
    HR = result['HR']
    BB = result['BB']
    HP = result['HP']
    SF = result['SF']
    K = result['K']
    result['AVG'] = round(float(H) / AB, 3)
    result['OBP'] = round(float(H + BB + HP) / (AB + BB + HP + SF), 3)
    result['SLG'] = round((H + _2B + (2 * _3B) + (3 * HR)) / float(AB), 3)
    result['OPS'] = round(result['OBP'] + result['SLG'], 3)

if __name__ == '__main__':
    scrape()