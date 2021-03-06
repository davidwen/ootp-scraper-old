import argparse
import sqlite3
from contextlib import closing
from flask import Flask, request, g, render_template, redirect, url_for, Response
from functools import wraps

app = Flask(__name__)
USERNAME = None
PASSWORD = None

DATABASE = 'wbh.db'
ROOT = 'http://worldbaseballhierarchy.com/lgreports/news/html/'

RATINGS = {
    5: 'Very High',
    4: 'High',
    3: 'Normal',
    2: 'Low',
    1: 'Very Low'
}

COMPARATORS = {
    'gt': '>',
    'lt': '<',
    'eq': '='
}

SORTCOLS = {
    '2b': 'double',
    '3b': 'triple',
    'k%': 'krate',
    'bb%': 'bbrate',
    'k/9': 'k9',
    'bb/9': 'bb9',
    'k/bb': 'kbb'
}

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == USERNAME and password == PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

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

@app.route('/player/<int:player_id>/')
@requires_auth
def player(player_id):
    cur = g.db.cursor()
    cur.execute('''
        select p.*, starred.player_id is not null as starred
        from players p
        left join starred
            on starred.player_id = p.id
        where p.id = ?
        ''', [player_id])
    player = cur.fetchone()
    title_href = ROOT + 'players/player_' + str(player_id) + '.html'
    date_id, date = get_date()
    age = get_age(player['birthday'], date)
    starred = 'starred' if player['starred'] else ''
    return render_template('player.html',
        player=player,
        title_href=title_href,
        age=age,
        intelligence=RATINGS[player['intelligence']],
        work_ethic=RATINGS[player['work_ethic']],
        starred=starred)

@app.route('/player/<int:player_id>/star', methods=['POST'])
@requires_auth
def star_player(player_id):
    starred = request.form['starred'] == 'true'
    cur = g.db.cursor()
    if starred:
        cur.execute('''
            insert into starred
            (player_id) values (?)
            ''', [player_id])
    else:
        cur.execute('''
            delete from starred
            where player_id = ?
            ''', [player_id])
    g.db.commit()
    return str(player_id)

@app.route('/player/<int:player_id>/batting')
@requires_auth
def batting_ratings(player_id):
    return player_ratings(player_id, 'select r.*, date from batting_ratings r', '_batting_ratings.html')

@app.route('/player/<int:player_id>/pitching')
@requires_auth
def pitching_ratings(player_id):
    return player_ratings(player_id, 'select r.*, date from pitching_ratings r', '_pitching_ratings.html')

@app.route('/player/<int:player_id>/run')
@requires_auth
def run_ratings(player_id):
    return player_ratings(player_id, 'select r.*, date from run_ratings r', '_run_ratings.html')

@app.route('/player/<int:player_id>/fielding')
@requires_auth
def fielding_ratings(player_id):
    return player_ratings(player_id, 'select r.*, date from fielding_ratings r', '_fielding_ratings.html')

@app.route('/player/<int:player_id>/position')
@requires_auth
def position_ratings(player_id):
    return player_ratings(player_id, 'select r.*, date from position_ratings r', '_position_ratings.html')

@app.route('/player/<int:player_id>/pitch')
@requires_auth
def pitch_ratings(player_id):
    cur = g.db.cursor()
    cur.execute('''
        select r.*, date from pitch_ratings r
        join dates on date_id = dates.id
        where player_id = ?
        order by date desc
        ''', [player_id])
    rows = cur.fetchall()
    pitch_names = [i[0] for i in cur.description]
    exists = set()
    for row in rows:
        for i in range(2, len(row) - 1):
            if row[i] is not None:
                exists.add(pitch_names[i])
    pitch_names = [name for name in pitch_names if name in exists]
    return render_template('_pitch_ratings.html',
        rows=rows,
        exists=exists,
        pitch_names=pitch_names)

def player_ratings(player_id, sql, template):
    cur = g.db.cursor()
    cur.execute(sql + '''
        join dates on date_id = dates.id
        where player_id = ?
        order by date desc
        ''', [player_id])
    rows = cur.fetchall()
    return render_template(template,
        rows=rows)

@app.route('/team/')
@requires_auth
def teams():
    cur = g.db.cursor()
    cur.execute('''
        select *
        from teams
        where id = parent_id
        order by name
        ''')
    teams = cur.fetchall()
    return render_template('teams.html',
        teams=teams)

@app.route('/team/<int:team_id>/')
@requires_auth
def team(team_id):
    date_id, date = get_date()
    return redirect(url_for('team_date', team_id=team_id, date_id=date_id))

@app.route('/team/<int:team_id>/date/<int:date_id>')
@requires_auth
def team_date(team_id, date_id):
    cur = g.db.cursor()
    cur.execute('select * from teams where id = ?', [team_id])
    team = cur.fetchone()
    date_id, date = get_date(date_id=date_id)
    return render_template('team.html',
        team=team,
        date=date,
        date_id=date_id)

@app.route('/team/<int:team_id>/date/<int:date_id>/batting')
@requires_auth
def team_batting(team_id, date_id):
    sql = '''
        select p.name as name, p.position as position, p.birthday as birthday,
          br.*, t.level as level
        from batting_ratings br
        join players p on br.player_id = p.id
        join (
            select pt.player_id, pt.team_id
            from player_teams pt
            left join player_teams pt_later
              on pt_later.player_id = pt.player_id
              and pt_later.date_id > pt.date_id
              and pt_later.date_id <= ?
            where pt_later.player_id is null
        ) pt on br.player_id = pt.player_id
        join teams t on t.id = pt.team_id
        where br.date_id = ?
        and (t.id = ? or t.parent_id = ?)
        group by br.player_id
        order by level desc
        '''
    prev_sql = '''
        select br.*, count(*) as position
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id >= br.date_id
          and br_later.date_id <= ?
        where br.player_id in ({seq})
        group by br.player_id, br.date_id
        having position = 2
        '''
    return team_bp(team_id, date_id, sql, prev_sql, '_team_batting.html')

@app.route('/team/<int:team_id>/date/<int:date_id>/pitching')
@requires_auth
def team_pitchers(team_id, date_id):
    sql = '''
        select p.name as name, p.position as position, p.birthday as birthday,
          pr.*, t.level as level
        from pitching_ratings pr
        join players p on pr.player_id = p.id
        join (
            select pt.player_id, pt.team_id
            from player_teams pt
            left join player_teams pt_later
              on pt_later.player_id = pt.player_id
              and pt_later.date_id > pt.date_id
              and pt_later.date_id <= ?
            where pt_later.player_id is null
        ) pt on pr.player_id = pt.player_id
        join teams t on t.id = pt.team_id
        where pr.date_id = ?
        and (t.id = ? or t.parent_id = ?)
        group by pr.player_id
        order by level desc
        '''
    prev_sql = '''
        select pr.*, count(*) as position
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id >= pr.date_id
          and pr_later.date_id <= ?
        where pr.player_id in ({seq})
        group by pr.player_id, pr.date_id
        having position = 2
        '''
    return team_bp(team_id, date_id, sql, prev_sql, '_team_pitching.html')

def team_bp(team_id, date_id, sql, prev_sql, template):
    cur = g.db.cursor()
    date_id, date = get_date(date_id=date_id)

    cur.execute(sql, [date_id, date_id, team_id, team_id])
    rows = cur.fetchall()
    ratings = {}
    ids = []
    for row in rows:
        player_id = row['player_id']
        ratings[player_id] = row
        ids.append(player_id)

    prev_sql = prev_sql.format(seq=','.join(['?']*len(ratings)))
    cur.execute(prev_sql, [date_id] + ratings.keys())
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
    ages = get_ages(ratings, date)

    return render_template(template,
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes,
        ages=ages)

@app.route('/improvers/')
@requires_auth
def improvers():
    date_id, date = get_date()
    return redirect(url_for('improvers_date', date_id=date_id))

@app.route('/improvers/<int:date_id>')
@requires_auth
def improvers_date(date_id):
    date_id, date = get_date(date_id=date_id)
    return render_template('improvers.html',
        date=date,
        date_id=date_id)

@app.route('/improvers/<int:date_id>/batting')
@requires_auth
def improved_batting(date_id):
    max_age = int(request.args.get('maxage', '99'))
    starred = request.args.get('starred') == 'true'
    starred_sql = 'and s.player_id is not null ' if starred else ''
    sql = '''
        select
          p.name, p.position, p.birthday, p.work_ethic, p.intelligence,
          s.player_id is not null as starred,
          t.level, parent_team.name as ml_team, br.*,
          br.pot_contact + br.pot_gap + br.pot_power + br.pot_eye + br.pot_avoid_k as potential
        from batting_ratings br
        join players p on br.player_id = p.id
        left join starred s on p.id = s.player_id
        join player_teams pt on br.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where br.date_id = ?
        %s
        group by br.player_id
        order by potential desc
        ''' % starred_sql
    prev_sql = '''
        select br.*, br.pot_contact + br.pot_gap + br.pot_power + br.pot_eye + br.pot_avoid_k as potential, count(*) as position
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id >= br.date_id
        where br.player_id in ({seq})
        and br.date_id <= ?
        group by br.player_id, br.date_id
        having position = 2
        '''
    return improved_bp(date_id, max_age, sql, prev_sql, '_improvers_batting.html')

@app.route('/improvers/<int:date_id>/pitching')
@requires_auth
def improved_pitching(date_id):
    max_age = int(request.args.get('maxage', '99'))
    starred = request.args.get('starred') == 'true'
    starred_sql = 'and s.player_id is not null ' if starred else ''
    sql = '''
        select
          p.name, p.position, p.birthday, p.work_ethic, p.intelligence,
          s.player_id is not null as starred,
          t.level, parent_team.name as ml_team, pr.*,
          pr.pot_stuff + pr.pot_movement + pr.pot_control as potential
        from pitching_ratings pr
        join players p on pr.player_id = p.id
        left join starred s on p.id = s.player_id
        join player_teams pt on pr.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where pr.date_id = ?
        %s
        group by pr.player_id
        order by potential desc
        ''' % starred_sql
    prev_sql = '''
        select pr.*, pr.pot_stuff + pr.pot_movement + pr.pot_control as potential, count(*) as position
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id >= pr.date_id
        where pr.player_id in ({seq})
        and pr.date_id <= ?
        group by pr.player_id, pr.date_id
        having position = 2
        '''
    return improved_bp(date_id, max_age, sql, prev_sql, '_improvers_pitching.html')

def improved_bp(date_id, max_age, sql, prev_sql, template):
    date_id, date = get_date(date_id=date_id)
    cur = g.db.cursor()
    cur.execute(sql, [date_id])
    rows = cur.fetchall()
    ratings = {}
    ids = []
    for row in rows:
        player_id = row['player_id']
        ratings[player_id] = row
        ids.append(player_id)

    prev_sql = prev_sql.format(seq=','.join(['?']*len(ratings)))
    cur.execute(prev_sql, ratings.keys() + [date_id])
    prev_rows = cur.fetchall()
    prev_ratings = {}
    diff_classes = {}
    for row in prev_rows:
        player_id = row['player_id']
        if player_id in ratings:
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
    ages = get_ages(ratings, date)
    ids = [id for id in ids if id in prev_ratings and ages[id] < max_age]
    return render_template(template,
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes,
        ages=ages)

@app.route('/improvers/top/')
@requires_auth
def top_improvers():
    return render_template('top_improvers.html',
        team_id=request.args.get('team', 0),
        min_imp=request.args.get('minimp', 2))

@app.route('/improvers/top/batting')
@requires_auth
def top_improvers_batting():
    max_age = int(request.args.get('maxage', '99'))
    min_imp = int(request.args.get('minimp', '1'))
    team = int(request.args.get('team', '0'))
    starred = request.args.get('starred') == 'true'
    starred_sql = 'and s.player_id is not null ' if starred else ''
    sql = '''
        select
          p.name, p.position, p.birthday, p.work_ethic, p.intelligence,
          t.level, br.*, s.player_id is not null as starred,
          parent_team.name as ml_team, parent_team.id as ml_team_id,
          br.pot_contact + br.pot_gap + br.pot_power + br.pot_eye + br.pot_avoid_k as potential
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id > br.date_id
        join players p on br.player_id = p.id
        left join starred s on p.id = s.player_id
        join player_teams pt on br.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where br_later.player_id is null
        %s
        group by br.player_id
        ''' % starred_sql
    prev_sql = '''
        select
          p.name, p.position, p.birthday, t.level, br.*,
          parent_team.name as ml_team, parent_team.id as ml_team_id,
          br.pot_contact + br.pot_gap + br.pot_power + br.pot_eye + br.pot_avoid_k as potential
        from batting_ratings br
        left join batting_ratings br_earlier
          on br_earlier.player_id = br.player_id
          and br_earlier.date_id < br.date_id
        join players p on br.player_id = p.id
        left join starred s on p.id = s.player_id
        join player_teams pt on br.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where br_earlier.player_id is null
        %s
        group by br.player_id
        ''' % starred_sql
    return top_improvers_bp(max_age, min_imp, team, sql, prev_sql, '_improvers_batting.html')

@app.route('/improvers/top/pitching')
@requires_auth
def top_improvers_pitching():
    max_age = int(request.args.get('maxage', '99'))
    min_imp = int(request.args.get('minimp', '1'))
    team = int(request.args.get('team', '0'))
    starred = request.args.get('starred') == 'true'
    starred_sql = 'and s.player_id is not null ' if starred else ''
    sql = '''
        select
          p.name, p.position, p.birthday, p.work_ethic, p.intelligence,
          t.level, pr.*, s.player_id is not null as starred,
          parent_team.name as ml_team, parent_team.id as ml_team_id,
          pr.pot_stuff + pr.pot_movement + pr.pot_control as potential
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id > pr.date_Id
        join players p on pr.player_id = p.id
        left join starred s on p.id = s.player_id
        join player_teams pt on pr.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where pr_later.date_id is null
        %s
        group by pr.player_id
        ''' % starred_sql
    prev_sql = '''
        select
          p.name, p.position, p.birthday, t.level, pr.*,
          parent_team.name as ml_team, parent_team.id as ml_team_id,
          pr.pot_stuff + pr.pot_movement + pr.pot_control as potential
        from pitching_ratings pr
        left join pitching_ratings pr_earlier
          on pr_earlier.player_id = pr.player_id
          and pr_earlier.date_id < pr.date_Id
        join players p on pr.player_id = p.id
        left join starred s on p.id = s.player_id
        join player_teams pt on pr.player_id = pt.player_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where pr_earlier.date_id is null
        %s
        group by pr.player_id
        ''' % starred_sql
    return top_improvers_bp(max_age, min_imp, team, sql, prev_sql, '_improvers_pitching.html')

def top_improvers_bp(max_age, min_imp, team, sql, prev_sql, template):
    date_id, date = get_date()
    cur = g.db.cursor()
    ratings = {}
    for row in cur.execute(sql):
        ratings[row['player_id']] = row
    prev_ratings = {}
    diff_classes = {}
    ids = []
    for prev_player in cur.execute(prev_sql):
        player_id = prev_player['player_id']
        player = ratings[player_id]
        if player['potential'] > prev_player['potential']:
            prev_ratings[player_id] = prev_player
            diff_classes[player_id] = {}
            for key in prev_player.keys():
                if prev_player[key] < ratings[player_id][key]:
                    diff_classes[player_id][key] = 'increase'
                elif prev_player[key] > ratings[player_id][key]:
                    diff_classes[player_id][key] = 'decrease'
            ids.append((player['potential'] - prev_player['potential'], player['player_id']))
    ages = get_ages(ratings, date)
    ids = [id[1] for id in sorted(ids, key=lambda id: id[0], reverse=True) if ages[id[1]] < max_age]
    ids = [id for id in ids if (ratings[id]['potential'] - prev_ratings[id]['potential']) >= min_imp]
    if team != 0:
        ids = [id for id in ids if ratings[id]['ml_team_id'] == team]

    return render_template(template,
        ids=ids,
        ratings=ratings,
        prev_ratings=prev_ratings,
        diff_classes=diff_classes,
        ages=ages)

@app.route('/dropped/')
@requires_auth
def dropped():
    date_id, date = get_date()
    return redirect(url_for('dropped_date', date_id=date_id))

@app.route('/dropped/<int:date_id>')
@requires_auth
def dropped_date(date_id):
    date_id, date = get_date(date_id=date_id)
    return render_template('dropped.html',
        date=date,
        date_id=date_id)

@app.route('/dropped/<int:date_id>/batting')
@requires_auth
def dropped_batting(date_id):
    date_id, date = get_date(date_id=date_id)

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, p.birthday, br.*,
          br.contact + br.gap + br.power + br.eye + br.avoid_k as overall
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id > br.date_id
          and br_later.date_id <= ?
        join players p on br.player_id = p.id
        join player_teams pt on br.player_id = pt.player_id
        where pt.date_id = ?
        and pt.team_id = 0
        and br_later.player_id is null
        order by overall desc
        ''', [date_id, date_id])
    rows = cur.fetchall()
    ages = get_ages_from_rows(rows, date)
    return render_template('_dropped_batting.html',
        rows=rows,
        ages=ages)

@app.route('/dropped/<int:date_id>/pitching')
@requires_auth
def dropped_pitching(date_id):
    date_id, date = get_date(date_id=date_id)

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, p.birthday, pr.*,
          pr.stuff + pr.movement + pr.control as overall
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id > pr.date_id
          and pr_later.date_id <= ?
        join players p on pr.player_id = p.id
        join player_teams pt on pr.player_id = pt.player_id
        where pt.date_id = ?
        and pt.team_id = 0
        and pr_later.player_id is null
        order by overall desc
        ''', [date_id, date_id])
    rows = cur.fetchall()
    ages = get_ages_from_rows(rows, date)
    return render_template('_dropped_pitching.html',
        rows=rows,
        ages=ages)

@app.route('/waivers/')
@requires_auth
def waivers():
    date_id, date = get_date()
    return redirect(url_for('waivers_date', date_id=date_id))

@app.route('/waivers/<int:date_id>')
@requires_auth
def waivers_date(date_id):
    date_id, date = get_date(date_id=date_id)
    return render_template('waivers.html',
        date=date,
        date_id=date_id)

@app.route('/waivers/<int:date_id>/batting')
@requires_auth
def waivers_batting(date_id):
    date_id, date = get_date(date_id=date_id)

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, p.birthday, br.*,
          br.contact + br.gap + br.power + br.eye + br.avoid_k as overall
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id > br.date_id
          and br_later.date_id <= ?
        join players p on br.player_id = p.id
        join waiver_wire ww on ww.player_id = br.player_id
        where ww.date_id = ?
        and br_later.player_id is null
        order by overall desc
        ''', [date_id, date_id])
    rows = cur.fetchall()
    ages = get_ages_from_rows(rows, date)
    return render_template('_dropped_batting.html',
        rows=rows,
        ages=ages)

@app.route('/waivers/<int:date_id>/pitching')
@requires_auth
def waivers_pitching(date_id):
    date_id, date = get_date(date_id=date_id)

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, p.birthday, pr.*,
          pr.stuff + pr.movement + pr.control as overall
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id > pr.date_id
          and pr_later.date_id <= ?
        join players p on pr.player_id = p.id
        join waiver_wire ww on ww.player_id = pr.player_id
        where ww.date_id = ?
        and pr_later.player_id is null
        order by overall desc
        ''', [date_id, date_id])
    rows = cur.fetchall()
    ages = get_ages_from_rows(rows, date)
    return render_template('_dropped_pitching.html',
        rows=rows,
        ages=ages)

@app.route('/upcomingfa/')
@requires_auth
def upcoming_fa():
    return render_template('upcomingfa.html')

@app.route('/upcomingfa/batting')
@requires_auth
def upcoming_fa_batting():
    date_id, date = get_date()

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, p.birthday, br.*,
          br.contact + br.gap + br.power + br.eye + br.avoid_k as overall
        from batting_ratings br
        left join batting_ratings br_later
          on br_later.player_id = br.player_id
          and br_later.date_id > br.date_id
        join players p on br.player_id = p.id
        join upcoming_fa ufa on ufa.player_id = br.player_id
        and br_later.player_id is null
        order by overall desc
        ''')
    rows = cur.fetchall()
    ages = get_ages_from_rows(rows, date)
    return render_template('_dropped_batting.html',
        rows=rows,
        ages=ages)

@app.route('/upcomingfa/pitching')
@requires_auth
def upcoming_fa_pitching():
    date_id, date = get_date()

    cur = g.db.cursor()
    cur.execute('''
        select
          p.name, p.position, p.birthday, pr.*,
          pr.stuff + pr.movement + pr.control as overall
        from pitching_ratings pr
        left join pitching_ratings pr_later
          on pr_later.player_id = pr.player_id
          and pr_later.date_id > pr.date_id
        join players p on pr.player_id = p.id
        join upcoming_fa ufa on ufa.player_id = pr.player_id
        and pr_later.player_id is null
        order by overall desc
        ''')
    rows = cur.fetchall()
    ages = get_ages_from_rows(rows, date)
    return render_template('_dropped_pitching.html',
        rows=rows,
        ages=ages)

@app.route('/search/')
@requires_auth
def search():
    cols = [
        ('Age', ['age'], ''),
        ('Intelligence', ['intelligence'], ''),
        ('Work ethic', ['work_ethic'], ''),
        ('Batting (current)', ['contact', 'gap', 'power', 'eye', 'avoid_k'], 'batting'),
        ('Batting (potential)', ['pot_contact', 'pot_gap', 'pot_power', 'pot_eye', 'pot_avoid_k'], 'batting'),
        ('Speed', ['speed'], 'batting'),
        ('Stealing', ['steal'], 'batting'),
        ('Bunt for hit', ['bunt_for_hit'], 'batting'),
        ('Pitching (current)', ['stuff', 'movement', 'control'], 'pitching'),
        ('Pitching (potential)', ['pot_stuff', 'pot_movement', 'pot_control'], 'pitching'),
        ('Stamina', ['stamina'], 'pitching'),
        ('Velocity', ['velocity'], 'pitching'),
        ('Hold runner', ['hold'], 'pitching'),
        ('Groundball %', ['groundball'], 'pitching'),
        ('Catcher ability', ['catcher_ability'], 'batting'),
        ('Catcher arm', ['catcher_arm'], 'batting'),
        ('Infield range', ['infield_range'], 'batting'),
        ('Infield errors', ['infield_errors'], 'batting'),
        ('Infield arm', ['infield_arm'], 'batting'),
        ('Infield turn dp', ['infield_turn_dp'], 'batting'),
        ('Outfield range', ['outfield_range'], 'batting'),
        ('Outfield errors', ['outfield_errors'], 'batting'),
        ('Outfield arm', ['outfield_arm'], 'batting')]
    return render_template('search.html',
        cols=cols)

@app.route('/search/table')
@requires_auth
def search_table():
    cols = ['name'] + [c.encode('ascii', 'ignore') for c in request.args.getlist('cols[]')]
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 25))
    end = start + limit
    batting = request.args.get('batting', True)
    pitching = request.args.get('pitching', True)
    sortcol = request.args.get('sortcol', None)
    sortdir = request.args.get('sortdir', None)
    where = ''
    if pitching == 'true' and batting == 'false':
        where = 'and position in ("SP", "MR") '
    elif batting == 'true' and pitching == 'false':
        where = 'and position not in ("SP", "MR") '
    for f in request.args.getlist('filters[]'):
        f_parts = f.split(':')
        where += 'and %s %s %s ' % (f_parts[0], COMPARATORS[f_parts[1]], f_parts[2])
    order_by = ''
    if sortcol != '' and sortcol is not None:
        order_by = str.format('order by {0} ', sortcol)
        if sortdir == 'desc':
            order_by += 'desc '
        if sortcol != 'name':
            order_by += ', name '
    date_id, date = get_date()
    age_sql = '(julianday("%s") - julianday(birthday)) / 365 as age ' % date
    cur = g.db.cursor()
    sql = '''
        select p.*, br.*, rr.*, pr.*, fr.*, posr.*, ''' + age_sql + '''
        from players p
        left join batting_ratings br on p.id = br.player_id
        left join batting_ratings br_later
            on br_later.player_id = br.player_id
            and br_later.date_id > br.date_id
        left join pitching_ratings pr on p.id = pr.player_id
        left join pitching_ratings pr_later
            on pr_later.player_id = pr.player_id
            and pr_later.date_id > pr.date_id
        left join run_ratings rr on rr.player_id = br.player_id
        left join run_ratings rr_later
            on rr_later.player_id = rr.player_id
            and rr_later.date_id > rr.date_id
        left join fielding_ratings fr on fr.player_id = br.player_id
        left join fielding_ratings fr_later
            on fr_later.player_id = fr.player_id
            and fr_later.date_id > fr.date_id
        left join position_ratings posr on posr.player_id = br.player_id
        left join position_ratings posr_later
            on posr_later.player_id = posr.player_id
            and posr_later.date_id > posr.date_id
        where br_later.player_id is null
        and rr_later.player_id is null
        and pr_later.player_id is null
        and fr_later.player_id is null
        and posr_later.player_id is null ''' + where + order_by
    cur.execute(sql + str.format('limit {0}, {1}', start, limit))
    rows = cur.fetchall()
    cur.execute('select count(*) from (' + sql + ') s')
    total = cur.fetchone()[0]
    ages = get_ages_from_rows(rows, date)
    col_classes = {'name': 'player-name'}
    return render_template('_search.html',
        rows=rows,
        cols=cols,
        ages=ages,
        col_classes=col_classes,
        total=total,
        start=start + 1,
        end=min(end, total),
        sortcol=sortcol,
        sortdir=sortdir)

@app.route('/playersearch/')
@requires_auth
def player_search():
    return render_template('player_search.html')

@app.route('/playersearchresults')
@requires_auth
def player_search_results():
    cur = g.db.cursor()
    cur.execute('''
        select p.*, t.level, parent_team.name as ml_team
        from players p
        join player_teams pt on p.id = pt.player_id
        left join player_teams pt_later
            on p.id = pt_later.player_id
            and pt_later.date_id > pt.date_id
        left join teams t on t.id = pt.team_id
        left join teams parent_team on t.parent_id = parent_team.id
        where p.name like ?
        and pt_later.date_id is null
        group by p.id
        ''', ['%' + request.args.get('query') + '%'])
    rows = cur.fetchall()
    return render_template('_player_search_results.html',
        rows=rows)

@app.route('/stats/')
def stats():
    cur = g.db.cursor()
    cur.execute('''
        select year from season_batting_stats
        group by year
        order by year desc''')
    years = [row[0] for row in cur.fetchall()]
    return render_template('stats_index.html',
        years=years,
        header='WBH Stats Index')

@app.route('/stats/batting')
def batting_stats():
    return render_template('stats.html',
        batting=True,
        default_min=500,
        header='All-Time Batting Stats',
        title='WBH All-Time Stats')

@app.route('/stats/pitching')
def pitching_stats():
    return render_template('stats.html',
        batting=False,
        default_min=200,
        header='All-Time Pitching Stats',
        title='WBH All-Time Stats')

@app.route('/stats/batting/table')
def batting_stats_table():
    cols = [
        'name', 'g', 'ab', 'h', 'double', 'triple', 'hr',
        'rbi', 'r', 'bb', 'hp', 'sf', 'k', 'sb', 'cs',
        'vorp', 'war', 'avg', 'obp', 'slg', 'ops', 'babip', 'krate', 'bbrate'
    ]
    decimal3 = set(['avg', 'obp', 'slg', 'ops', 'babip'])
    filter_ = 'where ab + bb + hp + sf >= %d ' % int(request.args.get('min'))
    return stats_table(cols, 'batting_stats', filter_, set(), decimal3)

@app.route('/stats/pitching/table')
def pitching_stats_table():
    cols = [
        'name', 'g', 'gs', 'w', 'l', 'sv',
        'ip', 'ha', 'r', 'er', 'hr', 'bb', 'k',
        'cg', 'sho', 'vorp', 'war', 'era', 'whip',
        'k9', 'bb9', 'kbb'
    ]
    decimal2 = set(['era', 'whip', 'k9', 'bb9', 'kbb'])
    filter_ = 'where ip >= %d ' % int(request.args.get('min'))
    return stats_table(cols, 'pitching_stats', filter_, decimal2, set())

@app.route('/stats/season/batting')
def all_time_season_batting_stats():
    return render_template('stats.html',
        batting=True,
        default_min=100,
        header='All-Time Single Season Batting Stats',
        title='WBH Single Season Stats')

@app.route('/stats/season/pitching')
def all_time_pitching_stats():
    return render_template('stats.html',
        batting=False,
        default_min=40,
        header='All-Time Single Season Pitching Stats',
        title='WBH Single Season Stats')

@app.route('/stats/season/batting/table')
def all_time_season_batting_stats_table():
    cols = [
        'name', 'year', 'g', 'ab', 'h', 'double', 'triple', 'hr',
        'rbi', 'r', 'bb', 'hp', 'sf', 'k', 'sb', 'cs',
        'vorp', 'war', 'avg', 'obp', 'slg', 'ops', 'babip', 'krate', 'bbrate'
    ]
    decimal3 = set(['avg', 'obp', 'slg', 'ops', 'babip'])
    filter_ = 'where ab + bb + hp + sf >= %d ' % (int(request.args.get('min')))
    return stats_table(cols, 'season_batting_stats', filter_, set(), decimal3)

@app.route('/stats/season/pitching/table')
def all_time_season_pitching_stats_table():
    cols = [
        'name', 'year', 'g', 'gs', 'w', 'l', 'sv',
        'ip', 'ha', 'r', 'er', 'hr', 'bb', 'k',
        'cg', 'sho', 'vorp', 'war', 'era', 'whip',
        'k9', 'bb9', 'kbb'
    ]
    decimal2 = set(['era', 'whip', 'k9', 'bb9', 'kbb'])
    filter_ = 'where ip >= %d ' % (int(request.args.get('min')))
    return stats_table(cols, 'season_pitching_stats', filter_, decimal2, set())

@app.route('/stats/<int:year>/batting')
def season_batting_stats(year):
    return render_template('stats.html',
        year=year,
        batting=True,
        default_min=100,
        header='%d Batting Stats' % year,
        title='WBH %d Stats' % year)

@app.route('/stats/<int:year>/pitching')
def season_pitching_stats(year):
    return render_template('stats.html',
        year=year,
        batting=False,
        default_min=40,
        header='%d Pitching Stats' % year,
        title='WBH %d Stats' % year)

@app.route('/stats/<int:year>/batting/table')
def season_batting_stats_table(year):
    cols = [
        'name', 'g', 'ab', 'h', 'double', 'triple', 'hr',
        'rbi', 'r', 'bb', 'hp', 'sf', 'k', 'sb', 'cs',
        'vorp', 'war', 'avg', 'obp', 'slg', 'ops', 'babip', 'krate', 'bbrate'
    ]
    decimal3 = set(['avg', 'obp', 'slg', 'ops', 'babip'])
    filter_ = 'where s.year = %d and ab + bb + hp + sf >= %d ' % (year, int(request.args.get('min')))
    return stats_table(cols, 'season_batting_stats', filter_, set(), decimal3)

@app.route('/stats/<int:year>/pitching/table')
def season_pitching_stats_table(year):
    cols = [
        'name', 'g', 'gs', 'w', 'l', 'sv',
        'ip', 'ha', 'r', 'er', 'hr', 'bb', 'k',
        'cg', 'sho', 'vorp', 'war', 'era', 'whip',
        'k9', 'bb9', 'kbb'
    ]
    decimal2 = set(['era', 'whip', 'k9', 'bb9', 'kbb'])
    filter_ = 'where s.year = %d and ip >= %d ' % (year, int(request.args.get('min')))
    return stats_table(cols, 'season_pitching_stats', filter_, decimal2, set())

def stats_table(cols, table_name, filter_, decimal2, decimal3):
    start = int(request.args.get('start', 0))
    limit = int(request.args.get('limit', 25))
    end = start + limit
    sortcol = request.args.get('sortcol', None)
    sortcol = SORTCOLS.get(sortcol, sortcol)
    sortdir = request.args.get('sortdir', None)
    min_ = int(request.args.get('min'))
    show_filters = []
    if request.args.get('showhof') != 'false':
        show_filters.append('is_hof')
    else:
        filter_ += 'and is_hof = 0 '
    if request.args.get('showeligible') != 'false':
        show_filters.append('is_eligible')
    else:
        filter_ += 'and is_eligible = 0 '
    if request.args.get('showactive') != 'false':
        show_filters.append('is_active')
    if request.args.get('showretired') != 'false':
        show_filters.append('is_retired')
    if len(show_filters):
        filter_ += 'and (' + ' or '.join(show_filters) + ') '
    else:
        filter_ += 'and 0 '

    order_by = ''
    if sortcol != '' and sortcol is not None:
        order_by = str.format('order by {0} ', sortcol)
        if sortdir == 'desc':
            order_by += 'desc '
        if sortcol != 'name':
            order_by += ', name '
    cur = g.db.cursor()
    sql = '''
        select s.*,
               hof.player_id IS NOT NULL as is_hof,
               e.player_id IS NOT NULL as is_eligible,
               p.id IS NOT NULL as is_active,
               p.id IS NULL as is_retired
        from %s s
        left join hall_of_fame hof on hof.player_id = s.player_id
        left join hall_of_fame_eligible e on e.player_id = s.player_id
        left join players p on p.id = s.player_id
        %s %s ''' % (table_name, filter_, order_by)
    cur.execute(sql + str.format('limit {0}, {1}', start, limit))
    rows = cur.fetchall()
    cur.execute('select count(*) from (' + sql + ') s')
    total = cur.fetchone()[0]
    col_classes = {'name': 'player-name'}
    return render_template('_stats_table.html',
        rows=rows,
        cols=cols,
        col_classes=col_classes,
        total=total,
        start=start + 1,
        end=min(end, total),
        min=min_,
        sortcol=sortcol,
        sortdir=sortdir,
        decimal2=decimal2,
        decimal3=decimal3)

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

def get_age(birthday, date):
    birth_year = int(birthday[:birthday.find('-')])
    year = int(date[:date.find('-')])
    return year - birth_year

def get_ages(players, date):
    result = {}
    for player_id in players:
        result[player_id] = get_age(players[player_id]['birthday'], date)
    return result

def get_ages_from_rows(rows, date):
    result = {}
    for row in rows:
        result[row['player_id']] = get_age(row['birthday'], date)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    parser.add_argument('password')
    parser.add_argument('--port', default=5000)
    args = parser.parse_args()
    USERNAME = args.username
    PASSWORD = args.password
    app.run(debug=True, port=int(args.port))
