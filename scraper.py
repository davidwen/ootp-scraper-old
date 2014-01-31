import os
import re
import sqlite3

from bs4 import BeautifulSoup
from contextlib import closing

DATABASE = 'wbh.db'
ROOT = '/Users/davidwen/Library/Application Support/Out of the Park Developments/OOTP Baseball 14/saved_games/WBH.lg/news/almanac_2034'
LEAGUES = [100, 102, 104, 112, 116, 120, 124]

RATINGS = {
    'Very High': 5,
    'High': 4,
    'Normal': 3,
    'Low': 2,
    'Very Low': 1
}

class Scraper:
    def __init__(self):
        self.date_id = None
        self.batting_ratings = {}
        self.pitching_ratings = {}
        self.run_ratings = {}
        self.fielding_ratings = {}
        self.position_ratings = {}
        with closing(sqlite3.connect(DATABASE)) as db:
            self.populate_batting_ratings(db)
            self.populate_pitching_ratings(db)
            self.populate_run_ratings(db)
            self.populate_fielding_ratings(db)
            self.populate_position_ratings(db)

    def populate_batting_ratings(self, db):
        cur = db.cursor()
        cur.execute('''
            select
              br.player_id,
              br.contact, br.contact_l, br.contact_r, br.pot_contact,
              br.gap, br.gap_l, br.gap_r, br.pot_gap,
              br.power, br.power_l, br.power_r, br.pot_power,
              br.eye, br.eye_l, br.eye_r, br.pot_eye,
              br.avoid_k, br.avoid_k_l, br.avoid_k_r, br.pot_avoid_k
            from batting_ratings br
            left join batting_ratings br_later
              on br_later.player_id = br.player_id
              and br_later.date_id > br.date_id
            where br_later.date_id is null
            ''')
        for row in cur.fetchall():
            self.batting_ratings[row[0]] = [row[i] for i in range(1, len(row))]

    def populate_pitching_ratings(self, db):    
        cur = db.cursor()
        cur.execute('''
            select
              pr.player_id,
              pr.stuff, pr.stuff_l, pr.stuff_r, pr.pot_stuff,
              pr.movement, pr.movement_l, pr.movement_r, pr.pot_movement,
              pr.control, pr.control_l, pr.control_r, pr.pot_control,
              pr.velocity, pr.stamina
            from pitching_ratings pr
            left join pitching_ratings pr_later
              on pr_later.player_id = pr.player_id
              and pr_later.date_id > pr.date_id
            where pr_later.date_id is null
            ''')
        for row in cur.fetchall():
            self.pitching_ratings[row[0]] = [row[i] for i in range(1, len(row))]

    def populate_run_ratings(self, db):
        cur = db.cursor()
        cur.execute('''
            select
              rr.player_id, rr.speed, rr.steal, rr.baserunning, rr.sac_bunt, rr.bunt_for_hit
            from run_ratings rr
            left join run_ratings rr_later
              on rr_later.player_id = rr.player_id
              and rr_later.date_id > rr.date_id
            where rr_later.date_id is null
            ''')
        for row in cur.fetchall():
            self.run_ratings[row[0]] = [row[i] for i in range(1, len(row))]

    def populate_fielding_ratings(self, db):
        cur = db.cursor()
        cur.execute('''
            select
              fr.player_id,
              fr.catcher_arm, fr.catcher_ability,
              fr.infield_range, fr.infield_errors, fr.infield_arm, fr.infield_turn_dp,
              fr.outfield_range, fr.outfield_errors, fr.outfield_arm
            from fielding_ratings fr
            left join fielding_ratings fr_later
              on fr_later.player_id = fr.player_id
              and fr_later.date_id > fr.date_id
            where fr_later.date_id is null
            ''')
        for row in cur.fetchall():
            self.fielding_ratings[row[0]] = [row[i] for i in range(1, len(row))]

    def populate_position_ratings(self, db):
        cur = db.cursor()
        cur.execute('''
            select
              pr.player_id,
              pr.p, pr.ss,
              pr.c, pr.lf,
              pr.first_b, pr.cf,
              pr.second_b, pr.rf,
              pr.third_b
            from position_ratings pr
            left join position_ratings pr_later
              on pr_later.player_id = pr.player_id
              and pr_later.date_id > pr.date_id
            where pr_later.date_id is null
            ''')
        for row in cur.fetchall():
            self.position_ratings[row[0]] = [row[i] for i in range(1, len(row))]

    def scrape(self):
        with closing(sqlite3.connect(DATABASE)) as db:
            for dirname, dirnames, filenames in os.walk(ROOT + '/players'):
                for filename in filenames:
                    if filename[0] == '.':
                        continue
                    player_id = int(filename[len('player_'):filename.find('.')])
                    self.read_player_file(db, player_id, os.path.join(dirname, filename))
            for league in LEAGUES:
                filename = ROOT + '/leagues/league_' + str(league) + '_waiver_wire_block.html'
                self.read_waiver_wire(db, filename)


    def format_date(self, date):
        date_parts = date.split('/')
        return date_parts[2] + '-' + date_parts[0] + '-' + date_parts[1]

    def convert(self, rating):
        if rating == '-':
            return None
        return int(rating)

    def read_initial_player_file(self, db, player_id, filename):
        with open(filename, 'rb') as f:
            soup = BeautifulSoup(f.read())

            name = soup.find('div', class_='reptitle').text
            name = name[name.find(' ') + 1:name.find('#') - 1].strip()

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

            data_line = soup.find(text=re.compile('BATS:'))
            position = data_line.split(' ')[0]
            bats = data_line[data_line.find('BATS:') + 6: data_line.find('BATS:') + 7]
            throws = data_line[data_line.find('THROWS:') + 8: data_line.find('THROWS:') + 9]

            cur = db.cursor()
            cur.execute('''
                insert or ignore into players
                (id, name, birthday, leadership, loyalty, desire_for_win, greed, intelligence, work_ethic, bats, throws, position)
                values
                (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (player_id, name, birthday, leadership, loyalty, desire_for_win, greed, intelligence, work_ethic, bats, throws, position))
            db.commit()

    def read_player_file(self, db, player_id, filename):
        print player_id
        with open(filename, 'rb') as f:
            soup = BeautifulSoup(f.read())
            cur = db.cursor()
            if self.date_id is None:
                self.set_date(cur, soup)

            self.set_team(cur, player_id, soup)
            self.set_batting_ratings(cur, player_id, soup)
            self.set_pitching_ratings(cur, player_id, soup)
            self.set_run_ratings(cur, player_id, soup)
            self.set_fielding_ratings(cur, player_id, soup)
            self.set_position_ratings(cur, player_id, soup)
            db.commit()

    def set_team(self, cur, player_id, soup):
        team = 0
        team_link = soup.find('a', class_='boxlink').get('href')
        if team_link.find('team_.html') < 0:
            team = int(team_link[team_link.find('team_') + 5:team_link.find('html') - 1])
        cur.execute('''
            select pt.team_id
            from player_teams pt
            left join player_teams pt_later
              on pt_later.player_id = pt.player_id
              and pt_later.date_id > pt.date_id
            where pt_later.date_id is null
            and pt.player_id = ?
            ''', [player_id])
        row = cur.fetchone()
        old_team = None
        if row is not None:
            old_team = row[0]
        if old_team != team:
            params = [player_id, self.date_id, team]
            cur.execute('''
                insert into player_teams
                (player_id, date_id, team_id)
                values
                (?, ?, ?)
                ''', params)

    def set_batting_ratings(self, cur, player_id, soup):
        if soup.find(text=re.compile('BATTING RATINGS')) is None:
            return
        ratings_table = soup.find_all('table', class_='data')[1]
        ratings_rows = ratings_table.find_all('tr')
        contacts = ratings_rows[2].find_all('td')
        gaps = ratings_rows[3].find_all('td')
        powers = ratings_rows[4].find_all('td')
        eyes = ratings_rows[5].find_all('td')
        ks = ratings_rows[6].find_all('td')
        ratings = []
        for attr in [contacts, gaps, powers, eyes, ks]:
            ratings.extend([int(attr[i].text) for i in range(3, 7)])

        old_ratings = []
        if self.batting_ratings.has_key(player_id):
            old_ratings = self.batting_ratings[player_id]
        if old_ratings != ratings:
            params = [player_id, self.date_id]
            params.extend(ratings)
            cur.execute('''
                insert into batting_ratings
                (player_id, date_id,
                 contact, contact_l, contact_r, pot_contact,
                 gap, gap_l, gap_r, pot_gap,
                 power, power_l, power_r, pot_power,
                 eye, eye_l, eye_r, pot_eye,
                 avoid_k, avoid_k_l, avoid_k_r, pot_avoid_k)
                values
                (?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?)
                ''', params)

    def set_pitching_ratings(self, cur, player_id, soup):
        if soup.find(text=re.compile('PITCHING RATINGS')) is None:
            return
        ratings_table = soup.find_all('table', class_='data')[1]
        ratings_rows = ratings_table.find_all('tr')
        stuffs = ratings_rows[2].find_all('td')
        movements = ratings_rows[3].find_all('td')
        controls = ratings_rows[4].find_all('td')

        other_ratings_table = soup.find_all('table', class_='data')[3]
        other_ratings_rows = other_ratings_table.find_all('tr')
        velocity = other_ratings_rows[1].find_all('td')[1].text
        velocity = int(velocity[velocity.find('-') + 1: velocity.find(' ')])
        stamina = int(other_ratings_rows[2].find_all('td')[1].text)
        groundball = int(other_ratings_rows[4].find_all('td')[1].text[:2])
        hold = int(other_ratings_rows[5].find_all('td')[1].text)

        ratings = []
        for attr in [stuffs, movements, controls]:
            ratings.extend([int(attr[i].text) for i in range(3, 7)])
        ratings.extend([velocity, stamina])

        old_ratings = []
        if self.pitching_ratings.has_key(player_id):
            old_ratings = self.pitching_ratings[player_id]
        if old_ratings != ratings:
            params = [player_id, self.date_id]
            params.extend(ratings)
            params.extend([groundball, hold])
            cur.execute('''
                insert into pitching_ratings
                (player_id, date_id,
                 stuff, stuff_l, stuff_r, pot_stuff,   
                 movement, movement_l, movement_r, pot_movement,
                 control, control_l, control_r, pot_control,
                 velocity, stamina, groundball, hold)
                values
                (?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?, ?)
                ''', params)

    def set_run_ratings(self, cur, player_id, soup):
        ratings_table = soup.find_all('table', class_='data')[4]
        ratings_rows = ratings_table.find_all('tr')
        speed = int(ratings_rows[1].find_all('td')[1].text)
        steal = int(ratings_rows[2].find_all('td')[1].text)
        baserunning = int(ratings_rows[3].find_all('td')[1].text)
        sac_bunt = int(ratings_rows[4].find_all('td')[1].text)
        bunt_for_hit = int(ratings_rows[5].find_all('td')[1].text)

        ratings = [speed, steal, baserunning, sac_bunt, bunt_for_hit]
        
        old_ratings = []
        if self.run_ratings.has_key(player_id):
            old_ratings = self.run_ratings[player_id]
        if old_ratings != ratings:
            params = [player_id, self.date_id]
            params.extend(ratings)
            cur.execute('''
                insert into run_ratings
                (player_id, date_id,
                 speed, steal, baserunning, sac_bunt, bunt_for_hit)
                values
                (?, ?,
                 ?, ?, ?, ?, ?)
                ''', params)

    def set_fielding_ratings(self, cur, player_id, soup):
        if soup.find(text=re.compile('FIELDING RATINGS')) is None:
            return
        ratings_table = soup.find_all('table', class_='data')[2]
        ratings_rows = ratings_table.find_all('tr')
        ranges = ratings_rows[2].find_all('td')
        errors = ratings_rows[3].find_all('td')
        arms = ratings_rows[4].find_all('td')
        turn_dps = ratings_rows[5].find_all('td')
        abilities = ratings_rows[6].find_all('td')

        catcher_arm = arms[1].text
        catcher_ability = abilities[1].text
        infield_range = ranges[2].text
        infield_errors = errors[2].text
        infield_arm = arms[2].text
        infield_turn_dp = turn_dps[2].text
        outfield_range = ranges[3].text
        outfield_errors = errors[3].text
        outfield_arm = arms[3].text

        ratings = [catcher_arm, catcher_ability, infield_range, infield_errors, infield_arm, infield_turn_dp, outfield_range, outfield_errors, outfield_arm]
        ratings = [self.convert(rating) for rating in ratings]
        
        old_ratings = []
        if self.fielding_ratings.has_key(player_id):
            old_ratings = self.fielding_ratings[player_id]
        if old_ratings != ratings:
            params = [player_id, self.date_id]
            params.extend(ratings)
            cur.execute('''
                insert into fielding_ratings
                (player_id, date_id,
                 catcher_arm, catcher_ability,
                 infield_range, infield_errors, infield_arm, infield_turn_dp,
                 outfield_range, outfield_errors, outfield_arm)
                values
                (?, ?,
                 ?, ?,
                 ?, ?, ?, ?,
                 ?, ?, ?)
                ''', params)

    def set_position_ratings(self, cur, player_id, soup):
        if soup.find(text=re.compile('POSITION RATINGS')) is None:
            return
        ratings_table = soup.find_all('table', class_='data')[3]
        ratings_cells = ratings_table.find_all('td')
        ratings = [ratings_cells[i].text for i in range(1, 18, 2)]
        ratings = [self.convert(rating) for rating in ratings]
        
        old_ratings = []
        if self.position_ratings.has_key(player_id):
            old_ratings = self.position_ratings[player_id]
        if old_ratings != ratings:
            params = [player_id, self.date_id]
            params.extend(ratings)
            cur.execute('''
                insert into position_ratings
                (player_id, date_id,
                 p, ss,
                 c, lf,
                 first_b, cf,
                 second_b, rf,
                 third_b)
                values
                (?, ?,
                 ?, ?,
                 ?, ?,
                 ?, ?,
                 ?, ?,
                 ?)
                ''', params)        

    def set_date(self, cur, soup):
        date = soup.find('div', style='text-align:center; color:#000000; padding-top:4px;').text
        date = self.format_date(date)
        cur.execute('''
            select id
            from dates
            where date = ?
            ''', [date])
        row = cur.fetchone()
        if row is None:
            cur.execute('''
                insert into dates
                (date)
                values
                (?)
                ''', [date])
            self.date_id = cur.lastrowid
        else:
            self.date_id = row[0]

    def read_waiver_wire(self, db, filename):
        with open(filename, 'rb') as f:
            soup = BeautifulSoup(f.read())
            cur = db.cursor()

            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                if href.find('/players/') > 0:
                    player_id = int(href[href.find('player_') + 7 : href.find('html') - 1])
                    cur.execute('''
                        insert into waiver_wire
                        (player_id, date_id)
                        values
                        (?, ?)
                        ''', [player_id, self.date_id])
            db.commit()

if __name__ == '__main__':
    scraper = Scraper()
    scraper.scrape()