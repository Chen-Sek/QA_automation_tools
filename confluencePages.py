import requests
from requests.auth import HTTPBasicAuth
from db import *
import json
import re

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]
options  = { 'server': appSettings['confluence_url'] }

pagePostfix = "rest/api/latest/content/"

# управляет работой с Confluence
class Confluence:
	# получение содержимого страницы
	def getPageBody(self, pageId):
		url = options['server'] + pagePostfix
		expand = "?expand=body.storage,version,space,ancestors"
		headers = { "Content-Type": "application/json" }
		r = requests.get(url + str(pageId) + expand, headers = headers, auth=HTTPBasicAuth(username, password))
		return {"body": r.json()['body']['storage']['value'], "version": r.json()['version']['number'], "name": r.json()['title'], "ancestors": r.json()['ancestors'][len(r.json()['ancestors']) - 1]['id']}

	# обновление содержимого страницы
	def updatePageBody(self, pageId, _body, _version, _title, _ancestors):
		url = options['server'] + pagePostfix
		expand = "?expand=body.storage"
		headers = { "Content-Type": "application/json" }
		newBody = {
			"id": str(pageId),
			"type": "page",
			"ancestors":[{"type":"page","id": _ancestors}],
			"title": _title,
			"space":{"key":"DQC"},
			"version":{
						"number": int(_version) + 1
						},
			"body": {
					"storage": 
						{
						"value": _body,
						"representation":"storage"
						}
					}
		}
		print(newBody)
		r = requests.put(url + str(pageId) + expand, data = json.dumps(newBody), headers = headers, auth=HTTPBasicAuth(username, password))
		return r

	# обновление номера сборки на странице
	# принимает текущее содержимое страницы и строку, которую нужно заменить
	def changeTextInBody(self, _body, filename):
		body = _body
		# регулярное выражение, которое получает имя файла в ссылке типа "AxxonNext-3.6.3.1850-full.zip"
		regexpFilename  = re.compile('\D{10}\d\D\d\D\d\D\d{3,4}.[full]{4}.[zip]{3}')
		# регулярное выражение, которое получает текст ссылки типа "[3.6.3.185]"
		regexpBuildname = re.compile('\[\d\D\d\D\d\D\d{3,4}\]')

		newBuildname = filename[10:19]
		print(newBuildname)

		# заменяем даты в содержимом
		newBody = regexpFilename.sub(filename, body) 
		newBody = regexpBuildname.sub("[" + newBuildname + "]", newBody) 

		return newBody