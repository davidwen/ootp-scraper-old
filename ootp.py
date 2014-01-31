import sqlite3
import time
import json
from contextlib import closing
from flask import Flask, request, g, jsonify, render_template

app = Flask(__name__)

DATABASE = 'wbh.db'

def connect_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

def error(reason, code=400):
    return jsonify({'error': reason}), code

@app.route('/player/<player_id>/')
def player(player_id):
    cur = g.db.cursor()

    cur.execute('''
        select * from players where id = ?
        ''', [player_id])
    player = cur.fetchone()
    return render_template('player.html',
        player=player)

@app.route('/player/<player_id>/batting')
def batting_ratings(player_id):
    cur = g.db.cursor()
    cur.execute('''
        select br.*, date
        from batting_ratings br
        join dates on date_id = dates.id
        where player_id = ?
        order by date desc
        ''', [player_id])
    rows = cur.fetchall()
    return render_template('_batting_ratings.html',
        rows=rows)

@app.route('/player/<player_id>/pitching')
def pitching_ratings(player_id):
    cur = g.db.cursor()
    cur.execute('''
        select pr.*, date
        from pitching_ratings pr
        join dates on date_id = dates.id
        where player_id = ?
        order by date desc
        ''', [player_id])
    rows = cur.fetchall()
    return render_template('_pitching_ratings.html',
        rows=rows)

@app.route('/team/<team_id>/')
def team(team_id):
    cur = g.db.cursor()

    cur.execute('''
        select * from teams where id = ?
        ''', [team_id])
    team = cur.fetchone()

    date_id, date = get_date()

    return render_template('team.html',
        team=team,
        date=date)

@app.route('/team/<team_id>/batting')
def team_batting(team_id):
    cur = g.db.cursor()
    date_id, date = get_date()

    cur.execute('''
        select p.name, p.position, br.*, t.level
        from batting_ratings br
        join players p on br.player_id = p.id
        join player_teams pt on br.player_id = pt.player_id
        join teams t on t.id = pt.team_id
        where br.date_id = ?
        and (t.id = ? or t.parent_id = ?)
        order by level desc
        ''', [date_id, team_id, team_id])
    rows = cur.fetchall()
    ratings = {}
    ids = []
    for row in rows:
        player_id = row['player_id']
        ratings[player_id] = row
        ids.append(player_id)

    sql = '''
        select br.*, count(*) as position
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id >= br.date_id
        where br.player_id in ({seq})
        group by br.player_id, br.date_id
        having position = 2
        '''.format(seq=','.join(['?']*len(ratings)))
    cur.execute(sql, ratings.keys())
    prev_rows = cur.fetchall()
    prev_ratings = {}
    diff_classes = {}
    for row in prev_rows:
        player_id = row['player_id']
        prev_ratings[player_id] = row
        diff_classes[player_id] = {}
        for key in row.keys():
            if row[key] < ratings[player_id][key]:
                diff_classes[player_id][key] = 'increase'
            elif row[key] > ratings[player_id][key]:
                diff_classes[player_id][key] = 'decrease'

    return render_template('_team_batting.html',
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes)

@app.route('/team/<team_id>/pitching')
def team_pitchers(team_id):
    cur = g.db.cursor()
    date_id, date = get_date()

    cur.execute('''
        select p.name, p.position, pr.*, t.level
        from pitching_ratings pr
        join players p on pr.player_id = p.id
        join player_teams pt on pr.player_id = pt.player_id
        join teams t on t.id = pt.team_id
        where pr.date_id = ?
        and (t.id = ? or t.parent_id = ?)
        order by level desc
        ''', [date_id, team_id, team_id])
    rows = cur.fetchall()
    ratings = {}
    ids = []
    for row in rows:
        player_id = row['player_id']
        ratings[player_id] = row
        ids.append(player_id)

    sql = '''
        select pr.*, count(*) as position
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id >= pr.date_id
        where pr.player_id in ({seq})
        group by pr.player_id, pr.date_id
        having position = 2
        '''.format(seq=','.join(['?']*len(ratings)))
    cur.execute(sql, ratings.keys())
    prev_rows = cur.fetchall()
    prev_ratings = {}
    diff_classes = {}
    for row in prev_rows:
        player_id = row['player_id']
        prev_ratings[player_id] = row
        diff_classes[player_id] = {}
        for key in row.keys():
            if row[key] < ratings[player_id][key]:
                diff_classes[player_id][key] = 'increase'
            elif row[key] > ratings[player_id][key]:
                diff_classes[player_id][key] = 'decrease'

    return render_template('_team_pitching.html',
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes)

@app.route('/improvers/')
def improvers():
    date_id, date = get_date()
    return render_template('improvers.html',
        date=date,
        date_id=date_id)

@app.route('/improvers/<date_id>/')
def improvers_date(date_id):
    date_id, date = get_date(date_id=date_id)
    return render_template('improvers.html',
        date=date,
        date_id=date_id)

@app.route('/improvers/<date_id>/batting')
def improved_batting(date_id):
    date_id, date = get_date()

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, t.level, parent_team.name as ml_team, br.*,
          br.pot_contact + br.pot_gap + br.pot_power + br.pot_eye + br.pot_avoid_k as potential
        from batting_ratings br
        join players p on br.player_id = p.id
        join player_teams pt on br.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where br.date_id = ?
        order by potential desc
        ''', [date_id])
    rows = cur.fetchall()
    ratings = {}
    ids = []
    for row in rows:
        player_id = row['player_id']
        ratings[player_id] = row
        ids.append(player_id)

    sql = '''
        select br.*, br.pot_contact + br.pot_gap + br.pot_power + br.pot_eye + br.pot_avoid_k as potential, count(*) as position
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id >= br.date_id
        where br.player_id in ({seq})
        and br.date_id <= ?
        group by br.player_id, br.date_id
        having position = 2
        '''.format(seq=','.join(['?']*len(ratings)))
    cur.execute(sql, ratings.keys() + [date_id])
    prev_rows = cur.fetchall()
    prev_ratings = {}
    diff_classes = {}
    for row in prev_rows:
        player_id = row['player_id']
        rating = ratings[player_id]
        if rating['potential'] > row['potential']:
            prev_ratings[player_id] = row
            diff_classes[player_id] = {}
            for key in row.keys():
                if row[key] < ratings[player_id][key]:
                    diff_classes[player_id][key] = 'increase'
                elif row[key] > ratings[player_id][key]:
                    diff_classes[player_id][key] = 'decrease'
        else:
            del ratings[player_id]
    ids = [id for id in ids if id in ratings]
    return render_template('_improvers_batting.html',
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes)

@app.route('/improvers/<date_id>/pitching')
def improved_pitching(date_id):
    date_id, date = get_date()

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, t.level, parent_team.name as ml_team, pr.*,
          pr.pot_stuff + pr.pot_movement + pr.pot_control as potential
        from pitching_ratings pr
        join players p on pr.player_id = p.id
        join player_teams pt on pr.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where pr.date_id = ?
        order by potential desc
        ''', [date_id])
    rows = cur.fetchall()
    ratings = {}
    ids = []
    for row in rows:
        player_id = row['player_id']
        ratings[player_id] = row
        ids.append(player_id)

    sql = '''
        select pr.*, pr.pot_stuff + pr.pot_movement + pr.pot_control as potential, count(*) as position
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id >= pr.date_id
        where pr.player_id in ({seq})
        and pr.date_id <= ?
        group by pr.player_id, pr.date_id
        having position = 2
        '''.format(seq=','.join(['?']*len(ratings)))
    cur.execute(sql, ratings.keys() + [date_id])
    prev_rows = cur.fetchall()
    prev_ratings = {}
    diff_classes = {}
    for row in prev_rows:
        player_id = row['player_id']
        rating = ratings[player_id]
        if rating['potential'] > row['potential']:
            prev_ratings[player_id] = row
            diff_classes[player_id] = {}
            for key in row.keys():
                if row[key] < ratings[player_id][key]:
                    diff_classes[player_id][key] = 'increase'
                elif row[key] > ratings[player_id][key]:
                    diff_classes[player_id][key] = 'decrease'
        else:
            del ratings[player_id]
    ids = [id for id in ids if id in ratings]
    return render_template('_improvers_pitching.html',
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes)

def get_date(date_id=None):
    sql = 'select * from dates '
    params = []
    if date_id is not None:
        sql += 'where id = ? '
        params.append(date_id)
    sql += 'order by id desc '

    cur = g.db.cursor()
    cur.execute(sql, params)
    date_row = cur.fetchone()
    date_id = date_row['id']
    date = date_row['date']
    return (date_id, date)

if __name__ == '__main__':
    app.run(debug=True)