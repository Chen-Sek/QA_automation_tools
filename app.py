import logging
from flask import Flask, request, Response, render_template
from flask.ext.restful import reqparse, abort, Api, Resource
import requests
from requests.auth import HTTPBasicAuth
from db import *
from downloader import *
from jiraFilters import *
from confluencePages import *
import json
from datetime import datetime

logging.basicConfig(filename='QAAutomationTools.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

dataBase = SettingsDB()
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

class Settings(Resource):
	def get(self):
		logging.debug('Settings requested')
		return appSettings

# получение списка планов с bamboo
class BambooAuth(Resource):
	def get(self):
		logging.debug('Bamboo plans requested')
		#r = requests.get(appSettings['bamboo_url'] +'plan?os_authType=basic', auth=HTTPBasicAuth('roma,nbukharov', '21c0cd79Itv'))
		try:
			r = requests.get(appSettings['bamboo_url'] + 'plan.json?os_authType=basic', auth=HTTPBasicAuth(username, password))
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
		logging.debug('Get builds from bamboo')
		r = requests.get(appSettings['bamboo_url'] + 'result/' + key + '.json?os_authType=basic&expand=results[0:9].result.artifacts', auth=HTTPBasicAuth(username, password))
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
				print("ferror")
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
				print("error")
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
	

# routing

api.add_resource(Index,
	'/')

api.add_resource(Metrics,
	'/metrics')

api.add_resource(MainSettings,
	'/mainsettings')

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

if __name__ == '__main__':

	# запуск API
	host='0.0.0.0'
	port=5000
	app.run(host=host, port=port, debug=True)
