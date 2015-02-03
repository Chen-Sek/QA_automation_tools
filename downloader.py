import os
import requests
from requests.auth import HTTPBasicAuth
from html.parser import HTMLParser
from db import *

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]

tempDir = "temp\\"

# управляет загрузкой артефактов с bamboo на fs
class Downloader:

	# при загрузе артефакта AN сначала нужно распарсить страницу, получаемую
	# по адресу типа https://build.itvgroup.ru/bamboo/browse/ASIP-AN362-186/artifact/JOB1/installer/
	# и получить ссылку на full installer типа 
	# https://build.itvgroup.ru/bamboo/artifact/ASIP-AN362/JOB1/build-186/installer/AxxonNext-3.6.3.186-full.zip
	# все это выносится в отдельный метод
	def downloadAxxonNextArtifact(self, _link):
		prefix = "https://build.itvgroup.ru/"
		# получение страницы, которую нужно парсить
		page = requests.get(_link, auth=HTTPBasicAuth(username, password))

		# класс для парсера
		class MyHTMLParser(HTMLParser):
			def __init__(self):
				HTMLParser.__init__(self)
				self.data = ""

			def handle_starttag(self, tag, attr):
				if(tag == 'a'):
					for name, value in attr:
						if name == 'href' and "full" in value:
							self.data = value
							print(value)

		# получение ссылки
		parser = MyHTMLParser()
		parser.feed(page.text)
		link = parser.data
		print(link)
		if(link != None):
			fullLink = prefix + link
			print("test1")
			# загрузка 
			local_filename = tempDir + fullLink.split('/')[-1]
			r = requests.get(fullLink, auth=HTTPBasicAuth(username, password), stream=True)
			with open(local_filename, 'wb') as f:
				for chunk in r.iter_content(chunk_size=1024): 
					if chunk: # filter out keep-alive new chunks
						f.write(chunk)
						f.flush()
			return local_filename
		else:
			return False

