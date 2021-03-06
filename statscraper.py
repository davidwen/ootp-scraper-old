import argparse
import os
import re
import sqlite3
import urllib2

from bs4 import BeautifulSoup
from contextlib import closing
from decimal import Decimal

DATABASE = 'wbh.db'
URL_ROOT = 'http://worldbaseballhierarchy.com/lgreports/news/html/'
FILE_ROOT = '/Users/davidwen/Library/Application Support/Out of the Park Developments/OOTP Baseball 14/saved_games/WBH.lg/news/almanac_2035'

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
                response = urllib2.urlopen(URL_ROOT + '/players/player_%d.html' % player_id)
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

    header_table = soup.find(text=re.compile('Career Pitching Stats'))
    table = header_table.find_parents('table')[0].find_next_sibling()
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
        (player_id, name, g, gs, w, l, sv, ip, ha, r, er, hr, bb, k, cg, sho, vorp, war, era, whip, k9, bb9, kbb)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, name, result['G'], result['GS'], result['W'], result['L'], result['SV'], result['IP'],
              result['HA'], result['R'], result['ER'], result['HR'], result['BB'], result['K'], result['CG'],
              result['SHO'], result['VORP'], result['WAR'], result['ERA'], result['WHIP']), result['K9'], result['BB9'], result['KBB'])
    db.commit()

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
    if (adjusted_ip * 10) % 10 == 1:
        adjusted_ip += 0.2333
    elif (adjusted_ip * 10) % 10 == 2:
        adjusted_ip += 0.4666
    ER = result['ER']
    HA = result['HA']
    BB = result['BB']
    K = result['K']
    outs = round(adjusted_ip * 3)
    result['ERA'] = round(ER * 9.0 / adjusted_ip, 2)
    result['WHIP'] = round((HA + BB) / adjusted_ip, 2)
    result['K9'] = round(K * 9.0 / adjusted_ip, 2)
    result['BB9'] = round(BB * 9.0 / adjusted_ip, 2)
    result['KBB'] = 0
    if BB > 0:
        result['KBB'] = round(float(K) / BB, 2)

def batting_stats(db, soup, player_id):
    name = soup.find('div', class_='reptitle').text
    name = name[name.find(' ') + 1:name.find('#') - 1].strip()
    
    fielding_header = soup.find(text=re.compile('CAREER FIELDING STATS'))
    fielding_table = fielding_header.find_parents('table')[0].find_next_sibling()
    rows = fielding_table.find_all('tr', class_='hsi')
    best = (None, 0)
    for row in rows:
        values = [th.string for th in row.find_all('th')]
        games = int(values[2])
        position = values[1]
        if games > best[1]:
            best = (position, games)
    position = best[0]
    if position is None:
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
        (player_id, name, position,
         g, ab, h, double, triple, hr,
         rbi, r, bb, hp, sf, k, sb, cs,
         vorp, war, avg, obp, slg, ops, babip, krate, bbrate)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, name, position, result['G'], result['AB'], result['H'], result['_2B'], result['_3B'], result['HR'],
              result['RBI'], result['R'], result['BB'], result['HP'], result['SF'], result['K'], result['SB'], result['CS'],
              result['VORP'], result['WAR'], result['AVG'], result['OBP'], result['SLG'], result['OPS'], result['BABIP'], result['K%'], result['BB%']))
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
    PA = AB + BB + HP + SF
    result['AVG'] = round(float(H) / AB, 3)
    result['OBP'] = round(float(H + BB + HP) / (AB + BB + HP + SF), 3)
    result['SLG'] = round((H + _2B + (2 * _3B) + (3 * HR)) / float(AB), 3)
    result['OPS'] = round(result['OBP'] + result['SLG'], 3)
    if AB - K - HR + SF > 0:
        result['BABIP'] = round(float(H - HR) / (AB - K - HR + SF), 3)
    else:
        result['BABIP'] = 0
    result['K%'] = round(float(K) / PA, 2)
    result['BB%'] = round(float(BB) / PA, 2)

def season_scrape(year):
    with closing(sqlite3.connect(DATABASE)) as db:
        if year == '2035':
            for dirname, dirnames, filenames in os.walk(FILE_ROOT + '/players'):
                for filename in filenames:
                    if filename[0] == '.':
                        continue
                    player_id = int(filename[len('player_'):filename.find('.')])
                    with open(os.path.join(dirname, filename), 'rb') as f:
                        soup = BeautifulSoup(f.read())
                        if soup.find(text=re.compile('BATTING RATINGS')) is not None:
                            season_batting_stats(db, soup, player_id, int(year))
                        elif soup.find(text=re.compile('PITCHING RATINGS')) is not None:
                            season_pitching_stats(db, soup, player_id, int(year))
        else:
            for player_id in range(18170):
                try:
                    response = urllib2.urlopen(URL_ROOT + '/players/player_%d.html' % player_id)
                    html = response.read()
                    soup = BeautifulSoup(html)
                    if soup.find(text=re.compile('BATTING RATINGS')) is not None:
                        for y in range(2006, 2035):
                            season_batting_stats(db, soup, player_id, y)
                    elif soup.find(text=re.compile('PITCHING RATINGS')) is not None:
                        for y in range(2006, 2035):
                            season_pitching_stats(db, soup, player_id, y)
                except urllib2.HTTPError:
                    pass

def season_pitching_stats(db, soup, player_id, year):
    name = soup.find('div', class_='reptitle').text
    name = name[name.find(' ') + 1:name.find('#') - 1].strip()
    header_table = soup.find(text=re.compile('Career Pitching Stats'))
    table = header_table.find_parents('table')[0].find_next_sibling()
    rows = table.find_all('tr', class_=None)
    rows = [row for row in rows if str(year) in row.contents[1].string]
    if len(rows) == 0:
        return
    result = {}
    values = [td.string for td in rows[-1].find_all('td')]
    add_pitching_stats(result, values)
    if result['IP'] == 0:
        return
    print player_id
    compile_pitching_stats(result)
    cur = db.cursor()
    cur.execute('''
        insert or replace into season_pitching_stats
        (year, player_id, name, g, gs, w, l, sv, ip, ha, r, er, hr, bb, k, cg, sho, vorp, war, era, whip, k9, bb9, kbb)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (year, player_id, name, result['G'], result['GS'], result['W'], result['L'], result['SV'], result['IP'],
              result['HA'], result['R'], result['ER'], result['HR'], result['BB'], result['K'], result['CG'],
              result['SHO'], result['VORP'], result['WAR'], result['ERA'], result['WHIP'], result['K9'], result['BB9'], result['KBB']))
    db.commit()

def season_batting_stats(db, soup, player_id, year):
    name = soup.find('div', class_='reptitle').text
    name = name[name.find(' ') + 1:name.find('#') - 1].strip()
    
    fielding_header = soup.find(text=re.compile('CAREER FIELDING STATS'))
    fielding_table = fielding_header.find_parents('table')[0].find_next_sibling()
    rows = fielding_table.find_all('tr', class_=None)
    rows = [row for row in rows if str(year) in row.contents[1].string]
    best = (None, 0)
    for row in rows:
        values = [td.string for td in row.find_all('td')]
        games = int(values[2])
        position = values[1]
        if games > best[1]:
            best = (position, games)
    position = best[0]
    if position is None:
        data_line = soup.find(text=re.compile('BATS:'))
        position = data_line.split(' ')[0]

    header_table = soup.find(text=re.compile('Career Batting Stats'))
    table = header_table.find_parents('table')[0].find_next_sibling()
    rows = table.find_all('tr', class_=None)
    rows = [row for row in rows if str(year) in row.contents[1].string]
    if len(rows) == 0:
        return
    result = {}
    values = [td.string for td in rows[-1].find_all('td')]
    add_batting_stats(result, values)
    if result['AB'] == 0:
        return
    print player_id
    compile_batting_stats(result)
    cur = db.cursor()
    cur.execute('''
        insert or replace into season_batting_stats
        (year, player_id, name, position,
         g, ab, h, double, triple, hr,
         rbi, r, bb, hp, sf, k, sb, cs,
         vorp, war, avg, obp, slg, ops, babip, krate, bbrate)
        values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (year, player_id, name, position, result['G'], result['AB'], result['H'], result['_2B'], result['_3B'], result['HR'],
              result['RBI'], result['R'], result['BB'], result['HP'], result['SF'], result['K'], result['SB'], result['CS'],
              result['VORP'], result['WAR'], result['AVG'], result['OBP'], result['SLG'], result['OPS'], result['BABIP'], result['K%'], result['BB%']))
    db.commit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('year', default=None)
    args = parser.parse_args()
    if args.year:
        season_scrape(args.year)
    else:
        scrape()
