import pandas as pd
from yahoo_oauth import OAuth2
import logging
import json
from json import dumps
import datetime
import time
import yaml
import os

league_id = yaml.safe_load(open('config.yaml'))['league_id']
week_start = 14

class Yahoo_Api():
    def __init__(self,
                 consumer_key,
                 consumer_secret,
                 access_token
                ):
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token = access_token
        self._authorization = None
    def _login(self):
        global oauth
        oauth = OAuth2(None, None, from_file='oauth2yahoo.json')
        if not oauth.token_is_valid():
            oauth.refresh_access_token()

with open('oauth2yahoo.json') as json_yahoo_file:
    auths = json.load(json_yahoo_file)
yahoo_consumer_key = auths['consumer_key']
yahoo_consumer_secret = auths['consumer_secret']
yahoo_access_key = auths['access_token']
json_yahoo_file.close()

yahoo_api = Yahoo_Api(yahoo_consumer_key, yahoo_consumer_secret, yahoo_access_key)
yahoo_api._login()


def get_league_settings(league_id):
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/league/{}/settings'.format(league_id)
    response = oauth.session.get(url, params={'format': 'json'})
    r = response.json()

    league_stats = r['fantasy_content']['league'][1]['settings'][0]['stat_modifiers']['stats']

    league_stats_dict = {}
    for stat in league_stats:
        try:
            league_stats_dict[str(stat['stat']['stat_id'])] = stat['stat']['value']
        except:
            pass

    league_stats_dict['10'] = '6' #rush tds 6
    league_stats_dict['11'] = '1' #receptions 1
    league_stats_dict['12'] = '.1' #receiving yards .1
    league_stats_dict['16'] = '2' #two point conversion 2
    league_stats_dict

    league_stats_df = pd.DataFrame(list(league_stats_dict.items()), index=None)

    header = ['stat_id', 'stat_multiplier']
    league_stats_df.columns = header
    return league_stats_df


def get_num_teams(league_id):
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/leagues;league_keys={}'.format(league_id)
    response = oauth.session.get(url, params={'format': 'json'})
    r = response.json()

    return r['fantasy_content']['leagues']['0']['league'][0]['num_teams']

def get_team_ids(league_id):
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/league/{}/teams'.format(league_id)
    response = oauth.session.get(url, params={'format': 'json'})
    r = response.json()

    t2 = [i for i in r['fantasy_content']['league'][1]['teams'].keys() if i != 'count']
    team_ids = [r['fantasy_content']['league'][1]['teams'][i]['team'][0][1]['team_id'] for i in t2]
    return team_ids

def get_team_names(league_id):
    teams = {}
    team_ids = get_team_ids(league_id)

    for i in team_ids:
        url = 'https://fantasysports.yahooapis.com/fantasy/v2/team/{0}.t.{1}'.format(league_id,i)
        response = oauth.session.get(url, params={'format': 'json'})
        r = response.json()

        team = r['fantasy_content']['team'][0]
        team_key = get_team_info(team, 'team_key')
        team_id = get_team_info(team, 'team_id')
        team_name = get_team_info(team, 'name')

        teams[str(team_id)] = {'team_name': team_name, 'team_key': team_key}

    return teams

def get_team_info(team_info = None, info = None):
    for i in team_info:
        if list(i.keys())[0] == info:
            return i[info]
    return None

teams = get_team_names(league_id)
league_multiplier = get_league_settings(league_id)

def get_player_points(player_season_id=None, week=None, league_id=None):
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/player/{0}/stats;week={1};type=week'.format(player_season_id, week)
    response = oauth.session.get(url, params={'format': 'json'})
    r = response.json()


    stats = r['fantasy_content']['player'][1]['player_stats']['stats']

    player_stats = {}

    for i in stats:
        player_stats[i['stat']['stat_id']] = i['stat']['value']

    player_stats_df = pd.DataFrame(list(player_stats.items()), index=None)
    header = ['stat_id', 'value']
    player_stats_df.columns = header

    player_scores = player_stats_df.merge(league_multiplier, on='stat_id', how='left').fillna(0)
    player_scores["stat_multiplier"] = player_scores.stat_multiplier.astype(float)
    player_scores["value"] = player_scores.value.astype(float)
    player_scores["fantasy_points"] = player_scores["stat_multiplier"] * player_scores["value"]

    return round(sum(player_scores["fantasy_points"]),2)

#editorial_team_abbr or display_position or player_key
def get_player_info(player_info=None, info=None, wanted_info=None):

    for i in player_info[0]:
        try:
            if list(i.keys())[0] == info:
                return i[wanted_info or info]
        except:
            pass
    return None

def get_team_week_info(league=None, team_num=None, week=None):
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/team/{0}.t.{1}/roster;week={2}'.format(league_id,team_num,week)
    response = oauth.session.get(url, params={'format': 'json'})
    r = response.json()

    team_week_info = []
    team_info = r['fantasy_content']['team'][1]['roster']['0']['players']
    num_players = team_info['count']
    for i in range(num_players):
        player_info = team_info[str(i)]['player']
        player_position = get_player_info(player_info, 'display_position')
        player_team_abbr = get_player_info(player_info, 'editorial_team_abbr')
        player_status = get_player_info(player_info, 'status', 'status_full')
        player_injury = get_player_info(player_info, 'injury_note')
        player_key = get_player_info(player_info, 'player_key')
        player_points = get_player_points(player_season_id=player_key, week=week, league_id=league)
        team_name = teams[team_num]['team_name']
        team_player_info = (team_name, week, player_info[0][2]['name']['full'], player_position, player_team_abbr, player_info[1]['selected_position'][1]['position'], player_points, player_status, player_injury, player_key)

        team_week_info.append(team_player_info)

    team_week_info_df = pd.DataFrame(team_week_info, index=None)
    header = ['team_name', 'week', 'player_name', 'player_position', 'player_team', 'lineup_position', 'fantasy_points', 'player_status', 'player_injury', 'player_key']
    team_week_info_df.columns = header
    return team_week_info_df

week_end = week_start + 1

team_ids = get_team_ids(league_id)

final = pd.DataFrame()
for week in range(week_start, week_end):
    for team in team_ids:
        print('running team {}'.format(team))
        a = get_team_week_info(league_id, str(team), week)
        final = final.append(a, ignore_index=True)

final_stats=final[['team_name', 'week', 'player_name', 'player_position', 'player_team', 'lineup_position', 'fantasy_points', 'player_key']]
final_injury_report=final[['team_name', 'week', 'player_name', 'player_position', 'player_team', 'lineup_position', 'player_status', 'player_injury', 'player_key']]

final_injury_report['date'] = pd.Timestamp('today').strftime("%Y-%m-%d")

final_stats.to_csv("rawdata/fantasy_player_stats_by_week_{}_on.csv".format(week_start), index=False)
final_injury_report.to_csv("rawdata/fantasy_injury_report.csv", index=False, header=False, mode='a')

a=pd.read_csv('rawdata/fantasy_injury_report.csv')

a.loc[a['player_status'] == 'Reserve: COVID-19', 'player_injury'] = 'COVID-19'
a.loc[a['player_status'] == 'Reserve: COVID-19', 'player_status'] = 'Out'

a.loc[a['player_status'] == 'Injured Reserve - Designated for Return', 'player_injury'] = float('nan')
a.loc[a['player_status'] == 'Injured Reserve - Designated for Return', 'player_status'] = float('nan')

a=a.dropna(subset=['player_status'])

a.loc[a['player_status'] == 'Injured Reserve', 'injury_value'] = 5
a.loc[a['player_status'] == 'Out', 'injury_value'] = 4
a.loc[a['player_status'] == 'Doubtful', 'injury_value'] = 3
a.loc[a['player_status'] == 'Questionable', 'injury_value'] = 2
a = a.sort_values(['player_key','week', 'injury_value'])
b = a.drop_duplicates(subset=['player_key','week'], keep='last', inplace=False)

b.to_csv('rawdata/final_injury_data.csv', index=False)

file_list = []
for root, dirs, files in os.walk("rawdata"):
    if root == 'rawdata':
        for filename in files:
            file_list.append(filename)

player_files = [file for file in file_list if 'fantasy_player_stats_by_week_' in file]

player_stats = pd.DataFrame()

for file in player_files:
    a = pd.read_csv('rawdata/'+file)
    player_stats = player_stats.append(a)

player_stats

player_stats.to_csv("rawdata/fantasy_player_stats.csv", index=False)
print('done')
