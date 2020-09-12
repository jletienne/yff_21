import pandas as pd
from yahoo_oauth import OAuth2
import logging
import json
from json import dumps
import datetime

week_num = 1
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



weekly_team_stats = []

opponent = {'0': '1', '1': '0'}
for week in range(1, week_num+1):
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

pd.DataFrame(weekly_team_stats).to_csv("rawdata/2019_fantasy_stats.csv", index=None)
