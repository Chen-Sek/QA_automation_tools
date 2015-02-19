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
	metricsDB = MetricsDB()

	def __init__(self):
		print(str(datetime.datetime.now().time()) + " starting") # debug
		self.jira = JIRA(options, basic_auth=(username, password))
		print(str(datetime.datetime.now().time()) + " jira initialized") # debug


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
		jql_user_issues_reporter  = 'project in (ACR,IPINT,INTL,CLC,ACFA,ATM,AUTO,FACE,POS,RSWT,LH,LS,SDVR,DDP,DRS,INTR,MC,CNV,SALE,SMV,SMN,SPRO,DDOC,WMSS,VIQ) AND issuetype in ("Bug","Task","Sub-task","Project Requirement", "Improvement") AND resolution in ("Unresolved","Fixed","Won\'t Fix") AND created >= ' + str(year) + '-' + str(month) + '-01 AND created <= ' + str(year) + '-' + str(month) + '-' + str(lastDay) + ' AND reporter = ' + user
		data_user_issues_reporter = {
			'jql': jql_user_issues_reporter,
			'startAt': 0,
			'fields': [
			    'key',
			    'priority',
			    'timetracking',
			    'issuetype',
			    'components'
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
			    'components'
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
			    'components'
			],
			'maxResults': 200
		}

		## отчет о потраченном времени
		timesheet_report = 'rest/timesheet-gadget/1.0/raw-timesheet.json?targetUser=' + user + '&startDate=' + str(year) + '-' + str(month) + '-01&endDate=' + str(year) + '-' + str(month) + '-' + str(lastDay)

		# end of строки запросов__________________________________________________________________
		
		# получение списков задач по jql__________________________________________________________
		headers = { "Content-Type": "application/json" }
		user_issues_reporter     = requests.post(url, data = json.dumps(data_user_issues_reporter), headers = headers, auth=HTTPBasicAuth(username, password)).json()
		print(str(datetime.datetime.now().time()) + " first query done") # debug
		user_issues_assignee     = requests.post(url, data = json.dumps(data_user_issues_assignee), headers = headers, auth=HTTPBasicAuth(username, password)).json()
		print(str(datetime.datetime.now().time()) + " second query done") # debug
		user_dev_issues_assignee = requests.post(url, data = json.dumps(data_user_dev_issues_assignee), headers = headers, auth=HTTPBasicAuth(username, password)).json()
		print(str(datetime.datetime.now().time()) + " third query done") # debug
		user_timesheet_report    = requests.get(options['server'] + timesheet_report, headers = headers, auth=HTTPBasicAuth(username, password)).json()
		print(str(datetime.datetime.now().time()) + " fourth query done") # debug
		# end of получение списков задач по jql___________________________________________________

		# функции для расчета_____________________________________________________________________
			

		## количетсво созданных пользователем замечаний по типу. Использовать user_issues_reporter
		def issuesCountByType(issuesList):
			print(str(datetime.datetime.now().time()) + " start calc bugs") # debug
			issuesCount = { 'bugs_blocker'         : 0,
							'bugs_critical'        : 0,
							'bugs_major'           : 0,
							'bugs_minor'           : 0,
							'bugs_trivial'         : 0,
							'bugs_total'           : 0,
							'improvements'         : 0,
							'requirements'         : 0 }
			for issue in issuesList:
				if(issue['fields']['issuetype']['name']    == 'Improvement'):
					issuesCount['improvements']  += 1
				if(issue['fields']['issuetype']['name']    == 'Project requirement'):
					issuesCount['requirements']  += 1
				if(issue['fields']['issuetype']['name']    in ('Bug', 'Task', 'Sub-task')):
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

			print(str(datetime.datetime.now().time()) + " end calc bugs") # debug
			return issuesCount

		## запланированное и потраченное время
		def OETSCount(issuesList):
			print(str(datetime.datetime.now().time()) + " start calc OETSCount") # debug
			timeTracking = { 'OE'   : 0,
							 'TS'   : 0 }
			for issue in issuesList:
				try:
					timeTracking['OE'] += int(issue['fields']['timetracking']['originalEstimateSeconds'])
				except:
					pass
				try:
					timeTracking['TS'] += int(issue['fields']['timetracking']['timeSpentSeconds'])
				except:
					pass
			print(str(datetime.datetime.now().time()) + " end calc OETSCount") # debug
			return timeTracking

		# подсчет количества пропущенных дней
		## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
		## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
		def daysMissedCount(timesheet_report):
			print(str(datetime.datetime.now().time()) + " start calc daysMissedCount") # debug
			fromdate = date(year, month, 1)       # c
			todate   = date(year, month, lastDay) # по
			
			daygenerator = (fromdate + timedelta(x) for x in range((todate - fromdate).days + 1))
			# количество пропущенных дней
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
			if(missedCount < 0):
				missedCount = 0
			print(str(datetime.datetime.now().time()) + " end calc daysMissedCount") # debug
			return missedCount

		# подсчет времени на внутренние задачи
		## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
		## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
		def getTimeInternal(timesheet_report):
			print(str(datetime.datetime.now().time()) + " start calc getTimeInternal") # debug
			# компоненты внутренних задач
			internal_components = ( "Auto Test",
									"Bug Bash",
									"Development",
									"HeadHunting",
									"Internal Task", 
									"IP Test Bench", 
									"Matrix",
									"Recommended Platforms", 
									"Review", 
									"Test Plan",
									"Закупка комплектующих",
									"Претензия",
									"Разработка",
									"Расчет",
									"Ремонт",
									"Сборка",
									"Program Management",
									"TPS",
									"Axxon Technical Pre-sale Consultations" )
			# время на внутренние задачи
			timeInternal = 0
			# цикл по задачам в отчете
			for issue in timesheet_report:
				# получение информации о текущей задаче
				i = self.jira.issue(issue['key'])
				# цикл по компонентам текущей задачи и поиск совпадения с элементом internal_components
				for c in i.fields.components:
					if(c.name in internal_components):
						# в каждой задаче есть список entries - фактов логирования времени. Цикл по списку
						for entry in issue['entries']:
							# если задача таки внутренняя, учитываем ее время
							timeInternal += int(entry['timeSpent'])
						# нужно только первое совпадение, поэтому из цикла по компонентам выходим намеренно
						continue
			print(str(datetime.datetime.now().time()) + " end calc getTimeInternal") # debug
			return timeInternal

		# подсчет общего рабочего времени
		## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
		## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
		def getTimeTotal(timesheet_report):
			print(str(datetime.datetime.now().time()) + " start calc getTimeTotal") # debug
			# общее рабочее время
			timeTotal = 0
			# цикл по задачам в отчете
			for issue in timesheet_report:
				for entry in issue['entries']:
					# если задача таки внутренняя, учитываем ее время
					timeTotal += int(entry['timeSpent'])
			print(str(datetime.datetime.now().time()) + " end calc getTimeTotal") # debug
			return timeTotal

		# end of функции для расчета______________________________________________________________
		
		print(str(datetime.datetime.now().time()) + " start calc values") # debug
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

		__timeInternal = getTimeInternal(user_timesheet_report['worklog'])

		__timeTotal = getTimeTotal(user_timesheet_report['worklog'])

		__timeTesting = __timeTotal - __timeInternal

		__loggingQuality = (__timeTotal/60/60) / hoursRequired

		bugs_total_weights = (__issuesCountByType['bugs_blocker'] + __issuesCountByType['bugs_critical'] + __issuesCountByType['bugs_major']) * 4 + (__issuesCountByType['bugs_minor'] + __issuesCountByType['bugs_trivial'] + __issuesCountByType['requirements'] + __issuesCountByType['improvements'])
		__testVelocity = round(bugs_total_weights * 8 / (__timeTesting/60/60), 2)

		try:
			OE_TS = __QA_OETSCount['OE']/__QA_OETSCount['TS']
		except:
			OE_TS = 0
		print(str(datetime.datetime.now().time()) + " end calc values and start write to DB") # debug
		# end of расчет___________________________________________________________________________

		# сохранение в БД ________________________________________________________________________
		
		_user = self.metricsDB.getmUser(user)
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
							'time_internal':     __timeInternal,
							'time_total':        __timeTotal,
							'time_testing':      __timeTesting,
							'hours_required':    hoursRequired,
							'days_missed':       __daysMissedCount,
							'logging_quality':   round(__loggingQuality, 2),
							'testing_velocity':  round(__testVelocity, 2),
							'oe_ts':             round(OE_TS, 2) }
		# print(__QA_OETSCount['OE']/__QA_OETSCount['TS'])
		print(str(datetime.datetime.now().time()) + " Done!") # debug
		if(self.metricsDB.addMetrics(metricsValues)):
			return self.metricsDB.getMetrics(month, year)
		else:
			return []
