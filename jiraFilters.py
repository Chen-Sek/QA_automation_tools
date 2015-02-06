import os
import requests
from requests.auth import HTTPBasicAuth
from jira.client import JIRA
from db import *
import json
import re

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]
options  = { 'server': appSettings['jira_url'] }

filterPostfix = "rest/api/latest/filter/"

# управляет работой с Jira
class JiraFilters:
	jira = None

	def __init__(self):
		self.jira = JIRA(options, basic_auth=(username, password))

	# обновление даты в JQL фильтра
	# принимает строку JQL и даты в формате YYYY-MM-DD
	def changeDateInJQL(self, _JQL, prev_date, curr_date):
		JQL = _JQL
		# регулярное выражение, которое получает даты из фильтра Проверено QA в виде "2015-01-22, 2015-02-02"
		regexpFilterChecked   = re.compile('\d{4}-\d{2}-\d{2}, \d{4}-\d{2}-\d{2}')
		# регулярное выражение, которое получает предыдущую дату из фильтра Известные проблемы в виде ">= 2015-02-02"
		regexpFilterKnownPrev = re.compile('>= \d{4}-\d{2}-\d{2}')
		# регулярное выражение, которое получает текущую дату из фильтра Известные проблемы в виде "after 2015-02-02"
		regexpFilterKnownCurr = re.compile('after \d{4}-\d{2}-\d{2}')

		# заменяем даты в JQL
		newJQL = regexpFilterChecked.sub(prev_date + ", " + curr_date, JQL) 
		newJQL = regexpFilterKnownPrev.sub('>= ' + prev_date, newJQL)
		newJQL = regexpFilterKnownCurr.sub('after ' + prev_date, newJQL)

		return newJQL

	# получить параметры фильтра по его ID 
	# принимает ID фильтра, получаемый из БД
	# возвращает объект <JIRA Filter> класса JIRA
	def getFilter(self, filterId):
		filter = self.jira.filter(filterId)
		return filter
		
	# обновление JQL фильтра
	# принимает ID фильтра, получаемый из БД, и строку JQL
	# jira.client не умеет обновлять фильтры. Дклаем сами
	def updateFilterJQL(self, filterId, JQL):
		url = options['server'] + filterPostfix
		newFilter = {
			"jql": JQL
		}
		headers = { "Content-Type": "application/json" }

		r = requests.put(url + str(filterId), data = json.dumps(newFilter), headers = headers, auth=HTTPBasicAuth(username, password))
		return r


