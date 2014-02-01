import os
import re
import sqlite3

from bs4 import BeautifulSoup
from contextlib import closing

DATABASE = 'wbh.db'
ROOT = '/Users/davidwen/Library/Application Support/Out of the Park Developments/OOTP Baseball 14/saved_games/WBH.lg/news/almanac_2034'

class Scraper:
    def __init__(self):
        self.positions = {}
        with closing(sqlite3.connect(DATABASE)) as db:
            self.populate_positions(db)

    def populate_positions(self, db):
        cur = db.cursor()
        cur.execute('select id, position from players')
        for row in cur.fetchall():
            self.positions[row[0]] = row[1]

    def scrape(self):
        with closing(sqlite3.connect(DATABASE)) as db:
            for dirname, dirnames, filenames in os.walk(ROOT + '/players'):
                for filename in filenames:
                    if filename[0] == '.':
                        continue
                    player_id = int(filename[len('player_'):filename.find('.')])
                    self.read_player_file(db, player_id, os.path.join(dirname, filename))
            db.commit()
            
    def read_player_file(self, db, player_id, filename):
        with open(filename, 'rb') as f:
            soup = BeautifulSoup(f.read())
            data_line = soup.find(text=re.compile('BATS:'))
            position = data_line.split(' ')[0]
            if position == 'P':
                other_ratings_table = soup.find_all('table', class_='data')[3]
                other_ratings_rows = other_ratings_table.find_all('tr')
                role = other_ratings_rows[3].find_all('td')[1].text
                if role == 'Starter':
                    position = 'SP'
                else:
                    position = 'MR'
            if self.positions[player_id] != position:
                print str(player_id) + ': ' + self.positions[player_id] + ' -> ' + position
                cur = db.cursor()
                cur.execute('''
                    update players
                    set position = ?
                    where id = ?
                    ''', [position, player_id])

if __name__ == '__main__':
    scraper = Scraper()
    scraper.scrape()