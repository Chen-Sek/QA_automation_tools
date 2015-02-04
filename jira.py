import os
import requests
from requests.auth import HTTPBasicAuth
from db import *
import json

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

	def updateFilter(self, filterId):
		filterId = "20621"
		postfix = "filter/"
		url = jiraURL + postfix
		newFilter = {
			"name": "CLC - changed"
		}
		headers = { "Content-Type": "application/json" }

		r = requests.put(url + filterId, data = json.dumps(newFilter), headers = headers, auth=HTTPBasicAuth(username, password))
		return r


