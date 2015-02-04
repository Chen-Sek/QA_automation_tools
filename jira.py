import os
import requests
from requests.auth import HTTPBasicAuth
from db import *

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]
jiraURL  = appSettings['jira_url']

# управляет работой с Jira
class Jira:
	def favouriteFilters(self):
		url = jiraURL + "filter/favourite"
		r = requests.get(url, auth=HTTPBasicAuth(username, password))
		return r.text

