import os
import re
import sqlite3

from bs4 import BeautifulSoup
from contextlib import closing

DATABASE = 'wbh.db'
ROOT = '/Users/davidwen/Library/Application Support/Out of the Park Developments/OOTP Baseball 14/saved_games/WBH.lg/news/almanac_2034'

class TeamPopulator:
    def __init__(self):
        self.ml_teams = []

    def extract_team_id(self, href):
        return int(href[href.find('team_') + 5 : href.find('html') - 1])

    def read_leagues(self):
        leagues = [100, 102, 104, 112, 116, 120, 124]
        for league in leagues:
            filename = ROOT + '/leagues/league_' + str(league) + '_home.html'
            with open(filename, 'rb') as f:
                soup = BeautifulSoup(f.read())
                self.read_league(soup)

    def read_league(self, soup):
        table = soup.find_all('table', width='291px')[3]
        links = table.find_all('a')
        table = soup.find_all('table', width='291px')[5]
        links.extend(table.find_all('a'))
        for link in links:
            href = link['href']
            self.ml_teams.append(self.extract_team_id(href))

    def read_teams(self):
        with closing(sqlite3.connect(DATABASE)) as db:
            for ml_team in self.ml_teams:
                filename = ROOT + '/teams/team_' + str(ml_team) + '.html'
                with open(filename, 'rb') as f:
                    soup = BeautifulSoup(f.read())
                    cur = db.cursor()
                    self.read_team(ml_team, cur, soup)
            db.commit()

    def read_team(self, ml_team, cur, soup):
        name = soup.find('div', class_='reptitle').text
        cur.execute('''
            insert into teams
            (id, name, level)
            values
            (?, ?, ?)
            ''', [ml_team, name, 'ML'])
        minor_teams = []
        table = soup.find_all('table', width='291px')[7]
        for row in table.find_all('tr'):
            a = row.find('a')
            if a is not None:
                href = a['href']
                full_name = a.find('img')['title']
                name = full_name[:full_name.find('(')-1]
                level = full_name[full_name.find('(')+1: full_name.find(')')]
                minor_teams.extend([self.extract_team_id(href), name, level, ml_team])
        cur.execute('''
            insert into teams
            (id, name, level, parent_id)
            values
            (?, ?, ?, ?),
            (?, ?, ?, ?),
            (?, ?, ?, ?)
            ''', minor_teams)

if __name__ == '__main__':
    team_populator = TeamPopulator()
    team_populator.read_leagues()
    team_populator.read_teams()