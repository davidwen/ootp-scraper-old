CREATE TABLE IF NOT EXISTS players(
    id INTEGER PRIMARY KEY,
    name TEXT,
    birthday TEXT,
    leadership INTEGER,
    loyalty INTEGER,
    desire_for_win INTEGER,
    greed INTEGER,
    intelligence INTEGER,
    work_ethic INTEGER,
    bats TEXT,
    throws TEXT,
    position TEXT);

CREATE TABLE IF NOT EXISTS dates(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE);

CREATE TABLE IF NOT EXISTS batting_ratings(
    player_id INTEGER,
    date_id INTEGER,
    contact INTEGER,
    gap INTEGER,
    power INTEGER,
    eye INTEGER,
    avoid_k INTEGER,
    contact_r INTEGER,
    gap_r INTEGER,
    power_r INTEGER,
    eye_r INTEGER,
    avoid_k_r INTEGER,
    contact_l INTEGER,
    gap_l INTEGER,
    power_l INTEGER,
    eye_l INTEGER,
    avoid_k_l INTEGER,
    pot_contact INTEGER,
    pot_gap INTEGER,
    pot_power INTEGER,
    pot_eye INTEGER,
    pot_avoid_k INTEGER,
    PRIMARY KEY (player_id, date_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (date_id) REFERENCES dates(id));

CREATE TABLE IF NOT EXISTS pitching_ratings(
    player_id INTEGER,
    date_id INTEGER,
    stuff INTEGER,
    movement INTEGER,
    control INTEGER,
    stuff_l INTEGER,
    movement_l INTEGER,
    control_l INTEGER,
    stuff_r INTEGER,
    movement_r INTEGER,
    control_r INTEGER,
    pot_stuff INTEGER,
    pot_movement INTEGER,
    pot_control INTEGER,
    stamina INTEGER,
    velocity INTEGER,
    hold INTEGER,
    groundball INTEGER,
    PRIMARY KEY (player_id, date_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (date_id) REFERENCES dates(id));

CREATE TABLE IF NOT EXISTS fielding_ratings(
    player_id INTEGER,
    date_id INTEGER,
    catcher_arm INTEGER,
    catcher_ability INTEGER,
    infield_range INTEGER,
    infield_errors INTEGER,
    infield_arm INTEGER,
    infield_turn_dp INTEGER,
    outfield_range INTEGER,
    outfield_errors INTEGER,
    outfield_arm INTEGER,
    PRIMARY KEY (player_id, date_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (date_id) REFERENCES dates(id));

CREATE TABLE IF NOT EXISTS position_ratings(
    player_id INTEGER,
    date_id INTEGER,
    p INTEGER,
    c INTEGER,
    first_b INTEGER,
    second_b INTEGER,
    third_b INTEGER,
    ss INTEGER,
    lf INTEGER,
    cf INTEGER,
    rf INTEGER,
    PRIMARY KEY (player_id, date_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (date_id) REFERENCES dates(id));

CREATE TABLE IF NOT EXISTS run_ratings(
    player_id INTEGER,
    date_id INTEGER,
    speed INTEGER,
    steal INTEGER,
    baserunning INTEGER,
    sac_bunt INTEGER,
    bunt_for_hit INTEGER,
    PRIMARY KEY (player_id, date_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (date_id) REFERENCES dates(id));

CREATE TABLE IF NOT EXISTS player_teams(
    player_id INTEGER,
    date_id INTEGER,
    team_id INTEGER,
    PRIMARY KEY (player_id, date_id),
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (date_id) REFERENCES dates(id),
    FOREIGN KEY (team_id) REFERENCES teams(id));

CREATE TABLE IF NOT EXISTS teams(
    id INTEGER PRIMARY KEY,
    name TEXT,
    level TEXT,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES teams(id));

CREATE TABLE IF NOT EXISTS waiver_wire(
    player_id INTEGER,
    date_id INTEGER,
    PRIMARY KEY (player_id, date_id));

CREATE TABLE IF NOT EXISTS upcoming_fa(
    player_id INTEGER,
    PRIMARY KEY (player_id));

CREATE TABLE IF NOT EXISTS batting_stats(
    player_id INTEGER,
    name TEXT,
    position TEXT,
    g INTEGER,
    ab INTEGER,
    h INTEGER,
    double INTEGER,
    triple INTEGER,
    hr INTEGER,
    rbi INTEGER,
    r INTEGER,
    bb INTEGER,
    hp INTEGER,
    sf INTEGER,
    k INTEGER,
    sb INTEGER,
    cs INTEGER,
    vorp REAL,
    war REAL,
    avg REAL,
    obp REAL,
    slg REAL,
    ops REAL,
    babip REAL,
    krate REAL,
    bbrate REAL,
    PRIMARY KEY (player_id));

CREATE TABLE IF NOT EXISTS pitching_stats(
    player_id INTEGER,
    name TEXT,
    g INTEGER,
    gs INTEGER,
    w INTEGER,
    l INTEGER,
    sv INTEGER,
    ip INTEGER,
    ha INTEGER,
    r INTEGER,
    er INTEGER,
    hr INTEGER,
    bb INTEGER,
    k INTEGER,
    cg INTEGER,
    sho INTEGER,
    vorp REAL,
    war REAL,
    era REAL,
    whip REAL,
    k9 REAL,
    bb9 REAL,
    kbb REAL,
    PRIMARY KEY (player_id));

CREATE TABLE IF NOT EXISTS hall_of_fame (
    player_id INTEGER,
    year INTEGER);

CREATE TABLE IF NOT EXISTS hall_of_fame_eligible (
    player_id INTEGER);

CREATE TABLE IF NOT EXISTS season_batting_stats(
    year INTEGER,
    player_id INTEGER,
    name TEXT,
    position TEXT,
    g INTEGER,
    ab INTEGER,
    h INTEGER,
    double INTEGER,
    triple INTEGER,
    hr INTEGER,
    rbi INTEGER,
    r INTEGER,
    bb INTEGER,
    hp INTEGER,
    sf INTEGER,
    k INTEGER,
    sb INTEGER,
    cs INTEGER,
    vorp REAL,
    war REAL,
    avg REAL,
    obp REAL,
    slg REAL,
    ops REAL,
    babip REAL,
    krate REAL,
    bbrate REAL,
    PRIMARY KEY (player_id, year));

CREATE TABLE IF NOT EXISTS season_pitching_stats(
    year INTEGER,
    player_id INTEGER,
    name TEXT,
    g INTEGER,
    gs INTEGER,
    w INTEGER,
    l INTEGER,
    sv INTEGER,
    ip INTEGER,
    ha INTEGER,
    r INTEGER,
    er INTEGER,
    hr INTEGER,
    bb INTEGER,
    k INTEGER,
    cg INTEGER,
    sho INTEGER,
    vorp REAL,
    war REAL,
    era REAL,
    whip REAL,
    k9 REAL,
    bb9 REAL,
    kbb REAL,
    PRIMARY KEY (player_id, year));