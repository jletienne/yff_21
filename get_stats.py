import pandas as pd
from yahoo_oauth import OAuth2
import logging
import json
from json import dumps
import datetime
import yaml
import os

league_id = yaml.safe_load(open('config.yaml'))['league_id']

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


week_num = 1


weekly_team_stats = []

opponent = {'0': '1', '1': '0'}
for week in range(week_num, week_num+1):
    url = 'https://fantasysports.yahooapis.com/fantasy/v2/league/{}/scoreboard;week={}'.format(league_id , week)
    response = oauth.session.get(url, params={'format': 'json'})
    r = response.json()

    for game in ['0', '1', '2', '3', '4']:

        try:
            for team in ['0','1']:
                name = r['fantasy_content']['league'][1]['scoreboard']['0']['matchups'][game]['matchup']['0']['teams'][team]['team'][0][2]['name']
                manager = r['fantasy_content']['league'][1]['scoreboard']['0']['matchups'][game]['matchup']['0']['teams'][team]['team'][0][-1]['managers'][0]['manager']['nickname']
                points = r['fantasy_content']['league'][1]['scoreboard']['0']['matchups'][game]['matchup']['0']['teams'][team]['team'][1]['team_points']['total']
                points_against = r['fantasy_content']['league'][1]['scoreboard']['0']['matchups'][game]['matchup']['0']['teams'][opponent[team]]['team'][1]['team_points']['total']

                projected_points = r['fantasy_content']['league'][1]['scoreboard']['0']['matchups'][game]['matchup']['0']['teams'][team]['team'][1]['team_projected_points']['total']

                stats={'week': week, 'manager': manager, 'team_name': name, 'points': points, 'points_against': points_against, 'projected_points': projected_points}

                weekly_team_stats.append(stats)
        except:
            pass

pd.DataFrame(weekly_team_stats).to_csv("rawdata/fantasy_team_stats_by_week_{}.csv".format(week_num), index=None)


file_list = []
for root, dirs, files in os.walk("rawdata"):
    if root == 'rawdata':
        for filename in files:
            file_list.append(filename)



team_files = [file for file in file_list if 'fantasy_team_stats_by_week_' in file]

team_stats = pd.DataFrame()

for file in team_files:
    a = pd.read_csv('rawdata/'+file)
    team_stats = team_stats.append(a)


team_stats.to_csv("rawdata/fantasy_team_stats.csv", index=False)
