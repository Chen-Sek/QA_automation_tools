import logging
from flask import Flask, request, Response, make_response, render_template
from flask.ext.restful import reqparse, abort, Api, Resource
import requests
from requests.auth import HTTPBasicAuth
from db import *
from downloader import *
from jiraFilters import *
from confluencePages import *
import json
from datetime import datetime
import calendar, datetime

logging.basicConfig(filename='QAAutomationTools.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

dataBase = SettingsDB()
metrics = MetricsDB()
appSettings = dataBase.getMainSettings()

app = Flask(__name__, template_folder="html")
api = Api(app, default_mediatype="application/json")

# параметры нового плана
plan_parser = reqparse.RequestParser()
plan_parser.add_argument('name',                type=str)
plan_parser.add_argument('bamboo_plan',         type=str)
plan_parser.add_argument('jira_filter_issues',  type=str)
plan_parser.add_argument('jira_filter_checked', type=str)
plan_parser.add_argument('prev_date',           type=str)
plan_parser.add_argument('confluence_page',     type=str)

# параметры для загрузки артефакта
artifact_parser = reqparse.RequestParser()
artifact_parser.add_argument('link', type=str)

# параметры для обновления страниц
page_parser = reqparse.RequestParser()
page_parser.add_argument('filename',            type=str)

# параметры основных настроек
settings_parser = reqparse.RequestParser()
settings_parser.add_argument('username',       type=str)
settings_parser.add_argument('password',       type=str)
settings_parser.add_argument('bamboo_url',     type=str)
settings_parser.add_argument('jira_url',       type=str)
settings_parser.add_argument('confluence_url', type=str)

# параметры метрик. Добавление сотрудника
mUsers_parser = reqparse.RequestParser()
mUsers_parser.add_argument('username',       type=str)

# параметры метрик. Расчет
metrics_parser = reqparse.RequestParser()
metrics_parser.add_argument('users',    type=str)
metrics_parser.add_argument('month',       type=str)
metrics_parser.add_argument('daysInMonth', type=str)
metrics_parser.add_argument('year',        type=str)

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]

# объект, управляющий загрузкой артефактов
artifact = Downloader()

class Index(Resource):
	def get(self):
		html = render_template("/index.html")
		return Response(html, status = "200", mimetype='text/html')

class WeeklyBuilds(Resource):
	def get(self):
		html = render_template("/builds.html")
		return Response(html, status = "200", mimetype='text/html')

class Metrics(Resource):
	def get(self):
		html = render_template("/metrics.html")
		return Response(html, status = "200", mimetype='text/html')

class MainSettings(Resource):
	def get(self):
		html = render_template("/settings.html")
		return Response(html, status = "200", mimetype='text/html')

# получение основных настроек
class getSettingsValues(Resource):
	def get(self):
		appSettings = dataBase.getMainSettings()
		settings = {"username": appSettings['bamboo_token'].split(":")[0], "bamboo_url": appSettings['bamboo_url'], "jira_url": appSettings['jira_url'], "confluence_url": appSettings['confluence_url'] }
		return settings

# сохранение основных настроек
class saveSettingsValues(Resource):
	def post(self):
		# получаем пользовательские данные
		args = settings_parser.parse_args()
		# получаем данные из БД
		appSettings = dataBase.getMainSettings()
		# обновление пользователя
		if(args['password'] != ""):
			# если пароль не пустой, обновляем все
			dataBase.editMainSettings('bamboo_token', args['username'] + ":" + args['password'])
		else:
			# если пароль пустой, осталяем пароль старым
			dataBase.editMainSettings('bamboo_token', args['username'] + ":" + appSettings['bamboo_token'].split(":")[1])
		# обновляем остальное
		for a in args:
			if(a != 'username' and a != 'password'):
				dataBase.editMainSettings(a, args[a])
		# получаем обновленные параметры из БД
		appSettings = dataBase.getMainSettings()
		# возвращаем новые параметры
		settings = {"username": appSettings['bamboo_token'].split(":")[0], "bamboo_url": appSettings['bamboo_url'], "jira_url": appSettings['jira_url'], "confluence_url": appSettings['confluence_url'] }
		return settings

class Settings(Resource):
	def get(self):
		logging.debug('Settings requested')
		return appSettings

# получение списка планов с bamboo
class BambooAuth(Resource):
	def get(self):
		appSettings = dataBase.getMainSettings()
		logging.debug('Bamboo plans requested')
		#r = requests.get(appSettings['bamboo_url'] +'plan?os_authType=basic', auth=HTTPBasicAuth('roma,nbukharov', '21c0cd79Itv'))
		try:
			r = requests.get(appSettings['bamboo_url'] + 'rest/api/latest/' + 'plan.json?os_authType=basic', auth=HTTPBasicAuth(appSettings['bamboo_token'].split(":")[0], appSettings['bamboo_token'].split(":")[1]))
			logging.debug('Bamboo plans recieved')
			return r.json()
		except:
			return {}

# управление планами
class Plans(Resource):
	# получение планов из БД
	def get(self):
		logging.debug('Bamboo plans from DB requested')
		return dataBase.getBuilds()

	# добавление нового плана
	def post(self):
		logging.debug('Adding plan to DB:')
		
		args = plan_parser.parse_args()
		
		logging.debug('New plan parameters: \nkey: ' + args['bamboo_plan'], '\nfilter issues: ', args['jira_filter_issues'], '\nfilter checked: ', args['jira_filter_checked'], '\nprev_date: ' + args['prev_date'], '\npage', args['confluence_page'])
		
		# если плана нет в БД, создаем его
		if(not dataBase.getBuild( args['bamboo_plan'] )):
			if(dataBase.createBuild(args['bamboo_plan'],
									"Plan" + args['bamboo_plan'],
									args['jira_filter_issues'],
									args['jira_filter_checked'],
									args['prev_date'],
									args['confluence_page'])):
				logging.debug('Plan ' + args['bamboo_plan'] + ' added')
				
				return {"message": "Plan added", "key": args['bamboo_plan']}
			else:
				logging.debug('Plan ' + args['bamboo_plan'] + ' adding failed')
				
				return {"message": "Adding plan failed", "key": "-1"}
		# если план существует, обновляем его параметры
		else:
			logging.debug('Plan ' + args['bamboo_plan'] + ' already exists. Update parameters')
			
			dataBase.updateBuild(args['bamboo_plan'],
									"Plan" + args['bamboo_plan'],
									args['jira_filter_issues'],
									args['jira_filter_checked'],
									args['prev_date'],
									args['confluence_page'])

			logging.debug('Plan ' + args['bamboo_plan'] + ' parameters updated')
			
			return {"message": "Plan updated", "key": args['bamboo_plan']}

# получение списка последних 10 сборок
class Builds(Resource):
	def get(self, key):
		appSettings = dataBase.getMainSettings()
		logging.debug('Get builds from bamboo')
		r = requests.get(appSettings['bamboo_url'] + 'rest/api/latest/result/' + key + '.json?os_authType=basic&expand=results[0:9].result.artifacts', auth=HTTPBasicAuth(appSettings['bamboo_token'].split(":")[0], appSettings['bamboo_token'].split(":")[1]))
		return r.json()

# загрузка артефакта
class Download(Resource):
	def post(self):
		logging.debug('Publish build')
		if(artifact.checkState()):
			filename = artifact.getFilename()
			logging.debug('Another build is publishing')
			return {"result": "busy", "message": "Публикуется сборка " + filename + ". Дождитесь завершения"}
		args = artifact_parser.parse_args()
		link = args['link']
		print(link)
		if(link != None):
			artifact.downloadAxxonNextArtifact(link)
			logging.debug('Download started')
			return {"result": "done", "message": "Download started"}
		else:
			logging.debug('Starting download failed')
			return {"result": "failed", "message": "Failed"}

# получение прогресса загрузки
class DownloadProgress(Resource):
	def get(self):
		return artifact.getProgress()

# получение имени файла
class getFilename(Resource):
	def get(self):
		return artifact.getFilename()

# проверка, запущена ли публикация сборки
class checkState(Resource):
	def get(self):
		if(artifact.checkState()):
			filename = artifact.getFilename()
			return {"result": "busy", "message": "Публикуется сборка " + filename + ". Дождитесь завершения и обновите страницу"}
		else:
			return {"result": "free", "message": "---"}

# остановка процесса загрузки
class CancelDownload(Resource):
	def get(self):
		return artifact.cancelDownload()

# обнуление счетчиков
class clearCounters(Resource):
	def get(self):
		return artifact.clear()

class UpdateFilters(Resource):
	def get(self, key):
		print("key = " + key)
		plan = dataBase.getBuild( key )
		print("plan = " + plan['name'])
		if(plan != None):
			try:
				# получение ID фильтров
				jiraFilterIssuesID  = int(plan['jira_filter_issues'])
				jiraFilterCheckedID = int(plan['jira_filter_checked'])
			except:
				return {"result": "ferror", "message": "Невозможно получить параметры фильтров из БД, либо ID фильтра не является числом"}
			try:
				jiraExecutor = JiraFilters()
				# получение фильтров
				jiraFilterIssues = jiraExecutor.getFilter(jiraFilterIssuesID)
				jiraFilterChecked = jiraExecutor.getFilter(jiraFilterCheckedID)
				# обновление параметров фильтров
				# даты
				prev_date = plan['prev_date']
				curr_date = datetime.today().strftime("%Y-%m-%d")
				# обновление JQL
				jiraFilterIssuesNewJQL  = jiraExecutor.changeDateInJQL(jiraFilterIssues.jql, prev_date, curr_date)
				jiraFilterCheckedNewJQL = jiraExecutor.changeDateInJQL(jiraFilterChecked.jql, prev_date, curr_date)

				jiraExecutor.updateFilterJQL(jiraFilterIssuesID, jiraFilterIssuesNewJQL)
				jiraExecutor.updateFilterJQL(jiraFilterCheckedID, jiraFilterCheckedNewJQL)
				if(dataBase.updateBuild(plan = key, prev_date = curr_date)):
					print("Date updated!")
				return {"result": "done", "message": "Filters updated"}
			except:
				return {"result": "ferror", "message": "Ошибка при обращении к Jira API. Возможно, Jira не работает, либо ID фильтра задан некорректно"}
		else:
			return {"result": "ferror", "message": "Ошибка при обращении к БД"}

class UpdatePages(Resource):
	def post(self, key):
		pageArgs = page_parser.parse_args()
		print("key = " + key)
		print("filename = " + pageArgs['filename'])

		plan = dataBase.getBuild( key )
		print("plan = " + plan['name'])
		pagesIDs = []
		if(plan != None):
			try:
				# получение ID страниц
				pagesIDs  = str(plan['confluence_page']).split(",")
				print("IDS: " + str(pagesIDs))
			except:
				print("perror")
				return {"result": "perror", "message": "Невозможно получить параметры страниц из БД, либо параметры указаны некорректно"}
			confluenceExecutor = Confluence()
			for pageID in pagesIDs:
				print("ID: " + pageID)
				try:
					# получение страницы
					pageBody = confluenceExecutor.getPageBody(pageID)
				except:
					print("perror")
					return {"result": "perror", "message": "Ошибка при обращении к Confluence API. Невозможно получить страницу"}
				# обновление содержимого
				pageNewBody  = confluenceExecutor.changeTextInBody(pageBody['body'], pageArgs['filename'])
				try:
	
					confluenceExecutor.updatePageBody(pageID, pageNewBody, pageBody['version'], pageBody['name'], pageBody['ancestors'])
				except:
					print("perror")
					return {"result": "perror", "message": "Ошибка при обращении к Confluence API. Невозможно обновить страницу"}

			return {"result": "done", "message": "Pages updated"}
		else:
			return {"result": "perror", "message": "Ошибка при обращении к БД"}

class Users(Resource):
	def get(self):
		return metrics.getmUsers()

	def post(self):
		args = mUsers_parser.parse_args()
		user = metrics.addmUser(args['username'])
		if(user != False):
			return {"message": "user successfully added"}
		else:
			return {"message": "error add user"}

class User(Resource):
	def get(self, name):
		user = metrics.getmUser(name)
		if(user != False):
			return user
		else:
			return {"message": "error get user"}

	def delete(self, name):
		user = metrics.removemUser(name)
		if(user != False):
			return {"message": "user successfully removed"}
		else:
			return {"message": "error remove user"}

jiraMetrics = JiraFilters()

class StartMetrics(Resource):
	def get(self):
		args = metrics_parser.parse_args()
		if(args['users'] != None):
			users = args['users'].split(",")
			jiraMetrics.getMetrics(users, int(args['daysInMonth']), int(args['month']), int(args['year']))
		return {"message": "Metrics collection started"}

class GetMetrics(Resource):
	def get(self):
		args = metrics_parser.parse_args()
		return metrics.getMetrics(int(args['month']), int(args['year']))

class GetCSV(Resource):
	def get(self):
		args = metrics_parser.parse_args()
		if(args['month'] != None and args['year'] != None):
			csv = "User;Month;Year;Year Month;Blocker + Critical + Major;Trivial + Minor;Work time (hours);Required time (hours);Days missed;Original estimate (sec);Time spent (sec);OE/TS;Logging quality;Internal tasks time (hours);Work in testing (hours);Issues count;Testing velocity;Comment;premium amount, %;bugs blocker;bugs critical;bugs major;bugs minor;bugs trivial;improvements;PM\n"
			csvList = metrics.getMetrics(int(args['month']), int(args['year']))
			for item in csvList:
				user = item['user_id'].split(".")
				csv +=  user[0] +" " + user[1] + ";" + str(item['month']) + ";" + str(item['year']) + ";" + "-;" + str(item['bugs_blocker'] + item['bugs_critical'] + item['bugs_major']) + ";" + str(item['bugs_minor'] + item['bugs_trivial'] + item['improvements']) + ";" + str(round(item['time_total']/60/60, 2)) + ";" + str(item['hours_required']) + ";" + str(item['days_missed']) + ";" + str(item['time_spent']) + ";" + str(item['original_estimate']) + ";" +  str(item['oe_ts']) + ";" + str(item['logging_quality']) + ";" + str(round(item['time_internal']/60/60,2)) + ";" + str(round(item['time_testing']/60/60,2)) + ";" +  str(item['issues_count']) + ";" + str(item['testing_velocity']) + ";" +  "-;" +   "-;" +  str(item['bugs_blocker']) + ";" + str(item['bugs_critical']) + ";" +  str(item['bugs_major']) + ";" +  str(item['bugs_minor']) + ";" +  str(item['bugs_trivial']) + ";" + str(item['improvements']) + ";" + str(item['requirements']) + "\n"
			csv = csv.replace(".", ",")
			output = make_response(csv)
			output.headers["Content-Disposition"] = "attachment; filename=Metrics-"+ args['year'] + "-" + args['month'] + ".csv"
			output.headers["Content-type"] = "text/csv"
			return output
		else:
			return False

class GetMetricsProgress(Resource):
	def get(self):
		return jiraMetrics.getMetricsProgress()

class WorkDays(Resource):
	def get(self, year, month):
		# ориентировочное количество рабочего времени в месяце
		month = int(month)
		year = int(year)
		lastDay = calendar.monthrange(year, month)[1]
		fromdate = date(year, month, 1)
		todate = date(year, month, lastDay)

		daygenerator = (fromdate + timedelta(x) for x in range((todate - fromdate).days + 1))
		res = sum(1 for day in daygenerator if day.weekday() < 5)

		if(month == 2 or month == 3 or month == 6 or month == 11 ):
			res -= 1
		if(month == 5 ):
			res -= 2
		if(month == 1 ):
			res -= 7
		return {'workdays': res }
		


# routing

api.add_resource(Index,
	'/')

api.add_resource(Metrics,
	'/metrics')

api.add_resource(MainSettings,
	'/mainsettings')

api.add_resource(getSettingsValues,
	'/mainsettings/get')

api.add_resource(saveSettingsValues,
	'/mainsettings/save')

api.add_resource(WeeklyBuilds,
	'/builds')

api.add_resource(Settings,
	'/settings')

api.add_resource(BambooAuth,
	'/auth')

api.add_resource(Plans,
	'/plans')

api.add_resource(Builds,
	'/plans/<string:key>/builds')

api.add_resource(Download,
	'/download')

api.add_resource(DownloadProgress,
	'/download/progress')

api.add_resource(CancelDownload,
	'/download/cancel')

api.add_resource(checkState,
	'/download/state')

api.add_resource(clearCounters,
	'/download/clear')
api.add_resource(getFilename,
	'/download/filename')

api.add_resource(UpdateFilters,
	'/plans/<string:key>/updatefilters')

api.add_resource(UpdatePages,
	'/plans/<string:key>/updatepages')

api.add_resource(Users,
	'/metrics/users')

api.add_resource(User,
	'/metrics/users/<string:name>')

api.add_resource(GetMetrics,
	'/metrics/get')

api.add_resource(StartMetrics,
	'/metrics/start')

api.add_resource(GetMetricsProgress,
	'/metrics/progress')

api.add_resource(GetCSV,
	'/metrics/csv')

api.add_resource(WorkDays,
	'/metrics/workdays/<string:year>/<string:month>')

if __name__ == '__main__':

	# запуск API
	host='0.0.0.0'
	port=5000
	app.run(host=host, port=port, debug=True)
