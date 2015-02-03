from flask import Flask, request, Response, render_template
from flask.ext.restful import reqparse, abort, Api, Resource
import requests
from requests.auth import HTTPBasicAuth
from db import *
import json

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

app = Flask(__name__, template_folder="html")
api = Api(app, default_mediatype="application/json")

# параметры нового плана
plan_parser = reqparse.RequestParser()
plan_parser.add_argument('name',          type=str)
plan_parser.add_argument('key',         type=str)
plan_parser.add_argument('filters',         type=str)
plan_parser.add_argument('page',         type=str)

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]

class Index(Resource):
	def get(self):
		html = render_template("/index.html")
		return Response(html, status = "200", mimetype='text/html')

class Settings(Resource):
	def get(self):
		return appSettings

class BambooAuth(Resource):
	def get(self):
		print(username, password)
		#r = requests.get(appSettings['bamboo_url'] +'plan?os_authType=basic', auth=HTTPBasicAuth('roma,nbukharov', '21c0cd79Itv'))
		r = requests.get('https://build.itvgroup.ru/bamboo/rest/api/latest/plan.json?os_authType=basic', auth=HTTPBasicAuth(username, password))
		return r.json()

class Plans(Resource):
	def get(self):
		return dataBase.getBuilds()

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

class Builds(Resource):
	def get(self, key):
		r = requests.get('https://build.itvgroup.ru/bamboo/rest/api/latest/result/' + key + '.json?os_authType=basic&expand=results[0:9].result.artifacts', auth=HTTPBasicAuth(username, password))
		return r.json()

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

if __name__ == '__main__':

	# запуск API
	app.run(host='0.0.0.0', port=5000, debug=True)
