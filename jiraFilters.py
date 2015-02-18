import os
import requests
from requests.auth import HTTPBasicAuth
from jira.client import JIRA
from db import *
import json
import re
import calendar, datetime
from datetime import date,timedelta

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
		appSettings = dataBase.getMainSettings()
		username = appSettings['bamboo_token'].split(":")[0]
		password = appSettings['bamboo_token'].split(":")[1]

		url = options['server'] + filterPostfix
		newFilter = {
			"jql": JQL
		}
		headers = { "Content-Type": "application/json" }

		r = requests.put(url + str(filterId), data = json.dumps(newFilter), headers = headers, auth=HTTPBasicAuth(username, password))
		return r

	# ориентировочное количество рабочего времени в месяце
	def worktimeInMonth(self, _year, _month):
		lastDay = calendar.monthrange(year, month)[1]
		fromdate = date(_year, _month, 1)
		todate = date(_year, _month, lastDay)

		daygenerator = (fromdate + timedelta(x) for x in range((todate - fromdate).days + 1))
		res = sum(1 for day in daygenerator if day.weekday() < 5)

		if(_month == 2 or _month == 3 or _month == 6 or _month == 11 ):
			res -= 1
		if(_month == 5 ):
			res -= 2
		if(_month == 1 ):
			res -= 7
		return res

	# получение метрик
	def getMetrics(self, user, daysInMonth, month, year):
		# user - пользователь, для которого считаются метрики
		# daysInMonth - количество рабочих дней в месяце
		# month - месяц
		# year - год

		appSettings = dataBase.getMainSettings()
		username = appSettings['bamboo_token'].split(":")[0]
		password = appSettings['bamboo_token'].split(":")[1]
		url = options['server'] + "rest/api/latest/search"

		lastDay = calendar.monthrange(year, month)[1]
		# строки запросов_________________________________________________________________________
		## Задачи, созданные пользователем, в категории Development
		jql_user_issues_reporter  = 'category = Development AND created >= ' + str(year) + '-' + str(month) + '-01 AND created <= ' + str(year) + '-' + str(month) + '-' + str(lastDay) + ' AND reporter = ' + user
		data_user_issues_reporter = {
			'jql': jql_user_issues_reporter,
			'startAt': 0,
			'fields': [
			    'key',
			    'priority',
			    'timetracking',
			    'issuetype',
			    'component'
			],
			'maxResults': 200
		}

		## задачи, которые пользователь выполнил в проекте QA
		jql_user_issues_assignee  = 'project in (DQC) AND resolution = fixed AND status in (resolved,closed) AND resolved >= ' + str(year) + '-' + str(month) + '-01 AND resolved <= ' + str(year) + '-' + str(month) + '-' + str(lastDay) + ' AND assignee = ' + user
		data_user_issues_assignee = {
			'jql': jql_user_issues_assignee,
			'startAt': 0,
			'fields': [
			    'key',
			    'priority',
			    'created',
			    'timetracking',
			    'component'
			],
			'maxResults': 200
		}

		## задачи, которые пользователь выполнил в проектах категории Development
		jql_user_dev_issues_assignee  = 'category = Development AND created >= ' + str(year) + '-' + str(month) + '-01 AND created <= ' + str(year) + '-' + str(month) + '-' + str(lastDay) + ' AND assignee = ' + user
		data_user_dev_issues_assignee = {
			'jql': jql_user_dev_issues_assignee,
			'startAt': 0,
			'fields': [
			    'key',
			    'timetracking',
			    'component'
			],
			'maxResults': 200
		}

		## отчет о потраченном времени
		timesheet_report = 'rest/timesheet-gadget/1.0/raw-timesheet.json?targetmUser=' + user + '&startDate=' + str(year) + '-' + str(month) + '-01&endDate=' + str(year) + '-' + str(month) + '-' + str(lastDay)

		# end of строки запросов__________________________________________________________________
		
		# получение списков задач по jql__________________________________________________________
		headers = { "Content-Type": "application/json" }
		user_issues_reporter     = requests.post(url, data = json.dumps(data_user_issues_reporter), headers = headers, auth=HTTPBasicAuth(username, password)).json()
		user_issues_assignee     = requests.post(url, data = json.dumps(data_user_issues_assignee), headers = headers, auth=HTTPBasicAuth(username, password)).json()
		user_dev_issues_assignee = requests.post(url, data = json.dumps(data_user_dev_issues_assignee), headers = headers, auth=HTTPBasicAuth(username, password)).json()
		user_timesheet_report    = requests.get(options['server'] + timesheet_report, headers = headers, auth=HTTPBasicAuth(username, password)).json()
		# end of получение списков задач по jql___________________________________________________

		# функции для расчета_____________________________________________________________________
			

		## количетсво созданных пользователем замечаний по типу. Использовать user_issues_reporter
		def issuesCountByType(issuesList):
			issuesCount = { 'bugs_blocker' : 0,
							'bugs_critical': 0,
							'bugs_major'   : 0,
							'bugs_minor'   : 0,
							'bugs_trivial' : 0,
							'bugs_total'   : 0,
							'improvements' : 0,
							'requirements' : 0 }
			for issue in issuesList:
				if(issue['fields']['issuetype']['name']    == 'Improvement'):
					issuesCount['improvements']  += 1
				if(issue['fields']['issuetype']['name']    == 'Project requirement'):
					issuesCount['requirements']  += 1
				if(issue['fields']['issuetype']['name']    == 'Bug'):
					issuesCount['bugs_total']  += 1
					if(issue['fields']['priority']['name'] == 'Blocker'):
						issuesCount['bugs_blocker']  += 1
					if(issue['fields']['priority']['name'] == 'Critical'):
						issuesCount['bugs_critical'] += 1
					if(issue['fields']['priority']['name'] == 'Major'):
						issuesCount['bugs_major']    += 1
					if(issue['fields']['priority']['name'] == 'Minor'):
						issuesCount['bugs_minor']    += 1
					if(issue['fields']['priority']['name'] == 'Trivial'):
						issuesCount['bugs_trivial']  += 1
			return issuesCount

		## запланированное и потраченное время
		def OETSCount(issuesList):
			timeTracking = { 'OE'   : 0,
							 'TS'   : 0,
							 'TSint': 0 }
			for issue in issuesList:
				try:
					timeTracking['OE'] += int(issue['fields']['timetracking']['originalEstimateSeconds'])
				except:
					pass
				try:
					timeTracking['TS'] += int(issue['fields']['timetracking']['timeSpentSeconds'])
				except:
					pass
				try:
					# TODO:
					if(issue['fields']['component']['name'] == ""):
						timeTracking['TS'] += int(issue['fields']['timetracking']['timeSpentSeconds'])
				except:
					pass
			return timeTracking

		# подсчет количества пропущенных дней
		## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
		## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
		def daysMissedCount(timesheet_report):
			fromdate = date(year, month, 1)       # c
			todate   = date(year, month, lastDay) # по
			
			daygenerator = (fromdate + timedelta(x) for x in range((todate - fromdate).days + 1))

			missedCount = 0
			# цикл по дням в месяце
			for day in daygenerator:
				time = 0 # залогировано за день
				# цикл по задачам в отчете
				for issue in timesheet_report:
					# в каждой задаче есть список entries - фактов логирования времени. Цикл по списку
					for entry in issue['entries']:
						# определение дня, когда был залогирован очередной entry
						currDay = datetime.datetime.utcfromtimestamp(entry['created']/1000).date()
						# если в определенный день хоть что-то залогировано, увеличиваем time
						if(str(currDay) == str(day)):
							time += int(entry['timeSpent'])
					#print(str(time) + "-" + str(datetime.datetime.utcfromtimestamp(entry['created']/1000).date()))
				# print("День " + str(day) + ". залогировано " + str(time))
				# если time за день не стало больше 0, увеличиваем количество пропущенных дней
				if(time == 0):
					missedCount += 1
			# вычитаем выходные
			missedCount -= (lastDay - daysInMonth)
			# print(missedCount)
			return missedCount

		# end of функции для расчета______________________________________________________________
		
		# расчет__________________________________________________________________________________
		## Требуемое время (часов)
		hoursRequired = daysInMonth * 8
		## список с количеством задач
		__issuesCountByType = issuesCountByType(user_issues_reporter['issues'])
		## время, затраченное в QA
		__QA_OETSCount = OETSCount(user_issues_assignee['issues'])
		## время, затраченное в DEV
		__DevOETSCount = OETSCount(user_dev_issues_assignee['issues'])
		#print(user_timesheet_report['worklog'][0]['entries'])
		__daysMissedCount = daysMissedCount(user_timesheet_report['worklog'])
		__testVelocity = (__issuesCountByType['bugs_total'] + __issuesCountByType['improvements'] + __issuesCountByType['requirements']) / daysInMonth
		try:
			OE_TS = __QA_OETSCount['OE']/__QA_OETSCount['TS']
		except:
			OE_TS = 0
		# end of расчет___________________________________________________________________________

		# сохранение в БД ________________________________________________________________________
		metricsDB = MetricsDB()

		_user = metricsDB.getmUser(user)
		if(_user != False):
			userID = _user['id']
		else:
			return False

		metricsValues = {   'user_id':           userID,
							'month':             month,
							'year':              year,
							'bugs_blocker':      __issuesCountByType['bugs_blocker'],
							'bugs_critical':     __issuesCountByType['bugs_critical'],
							'bugs_major':        __issuesCountByType['bugs_major'],
							'bugs_minor':        __issuesCountByType['bugs_minor'],
							'bugs_trivial':      __issuesCountByType['bugs_trivial'],
							'improvements':      __issuesCountByType['improvements'],
							'requirements':      __issuesCountByType['requirements'],
							'issues_count':      __issuesCountByType['bugs_total'] + __issuesCountByType['improvements'] + __issuesCountByType['requirements'],
							'original_estimate': __QA_OETSCount['OE'],
							'time_spent':        __QA_OETSCount['TS'],
							'time_internal':     __QA_OETSCount['TSint'],
							'time_testing':      0,
							'hours_required':    hoursRequired,
							'days_missed':       __daysMissedCount,
							'logging_quality':   0,
							'testing_velocity':  __testVelocity,
							'oe_ts': OE_TS }
		# print(__QA_OETSCount['OE']/__QA_OETSCount['TS'])
		if(metricsDB.addMetrics(metricsValues)):
			return metricsDB.getMetrics(month, year)
		else:
			return []
