import os
import re
import sqlite3

from bs4 import BeautifulSoup
from contextlib import closing

DATABASE = 'wbh.db'
ROOT = '/Users/davidwen/Library/Application Support/Out of the Park Developments/OOTP Baseball 14/saved_games/WBH.lg/news/almanac_2034'

class UpcomingFreeAgentPopulator:
    def __init__(self):
        self.players = []

    def extract_player_id(self, href):
        return int(href[href.find('player_') + 7 : href.find('html') - 1])

    def read_leagues(self):
        leagues = [100, 102, 104, 112, 116, 120, 124]
        for league in leagues:
            for i in range(2):
                filename = ROOT + '/leagues/league_' + str(league) + '_upcoming_free_agents_report_' + str(i) + '.html'
                with open(filename, 'rb') as f:
                    soup = BeautifulSoup(f.read())
                    self.read_league(soup)

    def read_league(self, soup):
        table = soup.find('table', class_='sortable')
        links = table.find_all('a')
        for link in links:
            href = link['href']
            if 'players' in href:
                self.players.append(self.extract_player_id(href))

    def insert(self):
        with closing(sqlite3.connect(DATABASE)) as db:
            cur = db.cursor()
            cur.execute('delete from upcoming_fa')
            for player in self.players:
                cur.execute('''
                    insert into upcoming_fa
                    (player_id)
                    values
                    (?)
                    ''', [player])
            db.commit()

if __name__ == '__main__':
    populator = UpcomingFreeAgentPopulator()
    populator.read_leagues()
    populator.insert()