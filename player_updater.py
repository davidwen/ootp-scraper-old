import os
import re
import sqlite3

from bs4 import BeautifulSoup
from contextlib import closing

DATABASE = 'wbh.db'
ROOT = '/Users/davidwen/Library/Application Support/Out of the Park Developments/OOTP Baseball 14/saved_games/WBH.lg/news/almanac_2035'
RATINGS = {
    'Very High': 5,
    'High': 4,
    'Normal': 3,
    'Low': 2,
    'Very Low': 1
}
DATE_ID = 17

class Scraper:
    def __init__(self):
        self.names = {}
        with closing(sqlite3.connect(DATABASE)) as db:
            self.populate_names(db)

    def populate_names(self, db):
        cur = db.cursor()
        cur.execute('select id, name from players')
        for row in cur.fetchall():
            self.names[row[0]] = row[1]

    def scrape(self):
        with closing(sqlite3.connect(DATABASE)) as db:
            player_ids = []
            cursor = db.cursor()
            cursor.execute('''
                select player_id from batting_ratings where date_id = %d
                ''' % (DATE_ID))
            for row in cursor.fetchall():
                player_ids.append(row[0])
            cursor.execute('''
                select player_id from pitching_ratings where date_id = %d
                ''', (DATE_ID))
            for row in cursor.fetchall():
                player_ids.append(row[0])
            for player_id in player_ids:
                filename = ROOT + '/players/player_%d.html' % player_id
                self.read_player_file(db, player_id, filename)
            db.commit()
            
    def read_player_file(self, db, player_id, filename):
        with open(filename, 'rb') as f:
            soup = BeautifulSoup(f.read())
            name = soup.find('div', class_='reptitle').text
            name = name[name.find(' ') + 1:name.find('#') - 1].strip()

            if self.names[player_id] != name:
                print str(player_id) + ' ' + name
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

                birthday = soup.find('td', class_='wrap').text
                birthday = self.format_date(birthday)

                personality = soup.find('td', width='172px')
                personality_td = personality.find_all('td')
                leadership = RATINGS[personality_td[1].text]
                loyalty = RATINGS[personality_td[3].text]
                desire_for_win = RATINGS[personality_td[5].text]
                greed = RATINGS[personality_td[7].text]
                intelligence = RATINGS[personality_td[9].text]
                work_ethic = RATINGS[personality_td[11].text]

                bats = data_line[data_line.find('BATS:') + 6: data_line.find('BATS:') + 7]
                throws = data_line[data_line.find('THROWS:') + 8: data_line.find('THROWS:') + 9]

                cur = db.cursor()
                cur.execute('''
                    insert or replace into players
                    (id, name, birthday, leadership, loyalty, desire_for_win, greed, intelligence, work_ethic, bats, throws, position)
                    values
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (player_id, name, birthday, leadership, loyalty, desire_for_win, greed, intelligence, work_ethic, bats, throws, position))
                cur.execute('''
                    delete from batting_ratings where player_id = %d and date_id < %d
                    ''' % (player_id, DATE_ID))
                cur.execute('''
                    delete from pitching_ratings where player_id = %d and date_id < %d
                    ''' % (player_id, DATE_ID))
                cur.execute('''
                    delete from fielding_ratings where player_id = %d and date_id < %d
                    ''' % (player_id, DATE_ID))
                cur.execute('''
                    delete from run_ratings where player_id = %d and date_id < %d
                    ''' % (player_id, DATE_ID))
                cur.execute('''
                    delete from position_ratings where player_id = %d and date_id < %d
                    ''' % (player_id, DATE_ID))
                cur.execute('''
                    delete from player_teams where player_id = %d and date_id < %d
                    ''' % (player_id, DATE_ID))
                cur.execute('''
                    insert or ignore into player_teams (player_id, team_id, date_id) values (%d, 0, %d)
                    ''' % (player_id, DATE_ID))
                db.commit()

    def format_date(self, date):
        date_parts = date.split('/')
        return date_parts[2] + '-' + date_parts[0] + '-' + date_parts[1]

if __name__ == '__main__':
    scraper = Scraper()
    scraper.scrape()