import os
import requests
from requests.auth import HTTPBasicAuth
from jira.client import JIRA
from db import *
import json
import re
import calendar, datetime
from datetime import date,timedelta
from threading import Thread

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]
options  = { 'server': appSettings['jira_url'] }

filterPostfix = "rest/api/latest/filter/"

# управляет работой с Jira
class JiraFilters:
	# поток, в котором будет выполняться сбор метрик
	metricsThread     = None
	jira = None
	# сообщения о прогрессе сбора метрик
	infoMessage = ""
	# флаг завершения
	done = 0

	metricsDB = MetricsDB()

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

	# получение прогресса сбора метрик
	def getMetricsProgress(self):
		return { "info": self.infoMessage, "done": self.done }

	# получение метрик
	def getMetrics(self, users, daysInMonth, month, year):
		# users - пользователи, для которых считаются метрики
		# daysInMonth - количество рабочих дней в месяце
		# month - месяц
		# year - год
		self.infoMessage = str(datetime.datetime.now().time()) + " сбор метрик запущен..." 
		# print(users)

		# функция для потока сбора метрик
		def process():
			startTime = datetime.datetime.now()
			appSettings = dataBase.getMainSettings()
			username = appSettings['bamboo_token'].split(":")[0]
			password = appSettings['bamboo_token'].split(":")[1]
			url = options['server'] + "rest/api/latest/search"
			errorsCount = 0

			# функции для расчета_____________________________________________________________________
				
			## количетсво созданных пользователем замечаний по типу. Использовать user_issues_reporter
			def issuesCountByType(issuesList):
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
				return issuesCount
	
			## запланированное и потраченное время
			def OETSCount(issuesList):
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
				return timeTracking
	
			# подсчет количества пропущенных дней
			## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
			## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
			def daysMissedCount(timesheet_report):
				fromdate = date(year, month, 1)       # c
				todate   = date(year, month, lastDay) # по
				
				daygenerator = (fromdate + timedelta(x) for x in range((todate - fromdate).days + 1))
				# количество пропущенных дней
				missedCount = 0
				days = {} # рабочих дней
				# цикл по дням в месяце
				for day in daygenerator:
					# цикл по задачам в отчете
					for issue in timesheet_report:
						# в каждой задаче есть список entries - фактов логирования времени. Цикл по списку
						for entry in issue['entries']:
							# определение дня, когда был залогирован очередной entry
							currDay = datetime.datetime.utcfromtimestamp(entry['startDate']/1000).date()
							# если в определенный день хоть что-то залогировано, увеличиваем time
							if(str(currDay) == str(day)):
								days[str(currDay)] = 1
				# вычитаем выходные
				missedCount = daysInMonth - len(days)
				if(missedCount < 0):
					missedCount = 0
				return missedCount
	
			# подсчет времени на внутренние задачи
			## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
			## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
			def getTimeInternal(timesheet_report):
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
				return timeInternal
	
			# подсчет общего рабочего времени
			## timesheet_report возвращается timesheet report api и содержит информацию о залогированном времени.
			## подробнее http://www.jiratimesheet.com/wiki/RESTful_endpoint.html
			def getTimeTotal(timesheet_report):
				# общее рабочее время
				timeTotal = 0
				# цикл по задачам в отчете
				for issue in timesheet_report:
					for entry in issue['entries']:
						# если задача таки внутренняя, учитываем ее время
						timeTotal += int(entry['timeSpent'])
				return timeTotal
	
			# end of функции для расчета______________________________________________________________
	
			lastDay = calendar.monthrange(year, month)[1]

			for user in users:
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
				self.infoMessage = str(datetime.datetime.now().time())[0:8]  + ": пользователь " + user + " получение информации от Jira"
				user_issues_reporter     = requests.post(url, data = json.dumps(data_user_issues_reporter), headers = headers, auth=HTTPBasicAuth(username, password)).json()
				user_issues_assignee     = requests.post(url, data = json.dumps(data_user_issues_assignee), headers = headers, auth=HTTPBasicAuth(username, password)).json()
				user_dev_issues_assignee = requests.post(url, data = json.dumps(data_user_dev_issues_assignee), headers = headers, auth=HTTPBasicAuth(username, password)).json()
				user_timesheet_report    = requests.get(options['server'] + timesheet_report, headers = headers, auth=HTTPBasicAuth(username, password)).json()
				# end of получение списков задач по jql___________________________________________________
	
				# расчет__________________________________________________________________________________
				## Требуемое время (часов)
				hoursRequired = daysInMonth * 8
				
				## список с количеством задач
				self.infoMessage = str(datetime.datetime.now().time())[0:8] + ": пользователь " + user + " данные получены, идет расчет метрик" # debug
				__issuesCountByType = issuesCountByType(user_issues_reporter['issues'])
				
				## время, затраченное в QA
				__QA_OETSCount = OETSCount(user_issues_assignee['issues'])
				## время, затраченное в DEV
				#__DevOETSCount = OETSCount(user_dev_issues_assignee['issues'])
				
				## пропущено дней	
				__daysMissedCount = daysMissedCount(user_timesheet_report['worklog'])
				
				## время на внутренние задачи
				__timeInternal = getTimeInternal(user_timesheet_report['worklog'])
				
				## общее отработанное время
				__timeTotal = getTimeTotal(user_timesheet_report['worklog'])
		
				__timeTesting = __timeTotal - __timeInternal
		
				try:
					__loggingQuality = (__timeTotal/60/60) / hoursRequired
				except:
					__loggingQuality = 0
		
				bugs_total_weights = (__issuesCountByType['bugs_blocker'] + __issuesCountByType['bugs_critical'] + __issuesCountByType['bugs_major']) * 4 + (__issuesCountByType['bugs_minor'] + __issuesCountByType['bugs_trivial'] + __issuesCountByType['requirements'] + __issuesCountByType['improvements'])
		
				try:
					__testVelocity = round(bugs_total_weights * 8 / (__timeTesting/60/60), 2)
				except:
					__testVelocity = 0
		
				try:
					OE_TS = __QA_OETSCount['OE']/__QA_OETSCount['TS']
				except:
					OE_TS = 0
		
				self.infoMessage = str(datetime.datetime.now().time())[0:8]  + ": пользователь " + user + " запись данных в БД"
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
				# print(str(datetime.datetime.now().time()) + " Done!") # debug
				if(self.metricsDB.addMetrics(metricsValues)):
					pass
				else:
					errorsCount += 1
			endTime = datetime.datetime.now() - startTime
			self.infoMessage = str(datetime.datetime.now().time())[0:8]  + ": Сборк метрик завершен. Количество ошибок: " + str(errorsCount) + ". Общее время: " + str(endTime.seconds) + " секунд"
			self.done = 1
			if(errorsCount == 0):
				return True
			else:
				return False
		
		self.metricsThread = Thread( target = process, args = ( ) )
		self.done = 0
		if(self.metricsThread.start()):
			return True

		# if(self.metricsDB.addMetrics(metricsValues)):
		# 	return self.metricsDB.getMetrics(month, year)
		# else:
		# 	return []
