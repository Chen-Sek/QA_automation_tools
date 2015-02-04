from flask import Flask, request, Response, render_template
from flask.ext.restful import reqparse, abort, Api, Resource
import requests
from requests.auth import HTTPBasicAuth
from db import *
from downloader import *
import json

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

app = Flask(__name__, template_folder="html")
api = Api(app, default_mediatype="application/json")

# параметры нового плана
plan_parser = reqparse.RequestParser()
plan_parser.add_argument('name',     type=str)
plan_parser.add_argument('key',      type=str)
plan_parser.add_argument('filters',  type=str)
plan_parser.add_argument('page',     type=str)

# параметры для загрузки артефакта
artifact_parser = reqparse.RequestParser()
artifact_parser.add_argument('link', type=str)

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]

# объект, управляющий загрузкой артефактов
artifact = Downloader()

class Index(Resource):
	def get(self):
		html = render_template("/index.html")
		return Response(html, status = "200", mimetype='text/html')

class Settings(Resource):
	def get(self):
		return appSettings

# получение списка планов с bamboo
class BambooAuth(Resource):
	def get(self):
		#r = requests.get(appSettings['bamboo_url'] +'plan?os_authType=basic', auth=HTTPBasicAuth('roma,nbukharov', '21c0cd79Itv'))
		r = requests.get(appSettings['bamboo_url'] + 'plan.json?os_authType=basic', auth=HTTPBasicAuth(username, password))
		return r.json()

# управление планами
class Plans(Resource):
	# получение планов из БД
	def get(self):
		return dataBase.getBuilds()

	# добавление нового плана
	def post(self):
		args = plan_parser.parse_args()
		print(args['name'])
		print(args['key'])
		if(not dataBase.getBuild(args['key'])):
			if(dataBase.createBuild(args['name'], args['key'], 'test', 'test')):
				return {"message": "Added"}
			else:
				return {"message": "Failed"}
		else:
				return {"message": "Already exists"}

# получение списка последних 10 сборок
class Builds(Resource):
	def get(self, key):
		r = requests.get(appSettings['bamboo_url'] + 'result/' + key + '.json?os_authType=basic&expand=results[0:9].result.artifacts', auth=HTTPBasicAuth(username, password))
		return r.json()

# загрузка артефакта
class Download(Resource):
	def post(self):
		args = artifact_parser.parse_args()
		link = args['link']
		print(link)
		if(link != None):
			artifact.downloadAxxonNextArtifact(link)
			return {"message": "Download started"}
		else:
			return {"message": "Failed"}

# получение прогресса загрузки
class DownloadProgress(Resource):
	def get(self):
		return artifact.getProgress()

# остановка процесса загрузки
class CancelDownload(Resource):
	def get(self):
		return artifact.cancelDownload()

# routing

api.add_resource(Index,
	'/')

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

if __name__ == '__main__':

	# запуск API
	app.run(host='0.0.0.0', port=5000, debug=True)
