import os
import shutil
import requests
from requests.auth import HTTPBasicAuth
from html.parser import HTMLParser
import threading
from threading import Thread
from db import *

dataBase = SettingsDB()
appSettings = dataBase.getMainSettings()

username = appSettings['bamboo_token'].split(":")[0]
password = appSettings['bamboo_token'].split(":")[1]

# путь для загрузки
#dlPath = "\\\\fs\\weekly\\test\\"
dlPath = "temp\\"
# dlPath = "\\\\A-VASILIEV\\downloads\\temp\\"

# управляет загрузкой артефактов с bamboo на fs
class Downloader:

	# поток, в котором будет выполняться загрузка
	thread     = None
	uplThread     = None
	# событие для завершения потока
	t_stop       = threading.Event()
	# загружено на данный момент
	downloaded = 0
	# размер файла
	total = 0
	# путь к файлу
	fullPath = ""

	def getProgress(self):
		return { "downloaded": self.downloaded, "total": self.total }

	def getFilename(self):
		return self.fullPath.split('\\')[-1]

	def cancelDownload(self):
		if(self.thread != None):
			# установка события завершения потока
			self.t_stop.set()
			# когда поток остановился, сбрасываем событие и меняем состояние монитора
			self.thread.join()
			self.t_stop.clear()
			self.downloaded = 0;
			self.total = 0;
			self.fullPath = ""
			self.thread = None
			return { "message": "Download canceled" }
		else:
			return { "message": "Nothing to cancel" }

	# сброс счетчиков
	def clear(self):
		self.downloaded = 0
		self.total = 0
		self.fullPath = ""
		self.thread = None
		return { "message": "counters cleared" }

	# проверка запущенности
	def checkState(self):
		if(self.thread == None):
			return False
		else:
			return True


	# при загрузе артефакта AN сначала нужно распарсить страницу, получаемую
	# по адресу типа https://build.itvgroup.ru/bamboo/browse/ASIP-AN362-186/artifact/JOB1/installer/
	# и получить ссылку на full installer типа 
	# https://build.itvgroup.ru/bamboo/artifact/ASIP-AN362/JOB1/build-186/installer/AxxonNext-3.6.3.186-full.zip
	# все это выносится в отдельный метод
	def downloadAxxonNextArtifact(self, _link):
		prefix = "https://build.itvgroup.ru/"
		# получение страницы, которую нужно парсить
		try:
			page = requests.get(_link, auth=HTTPBasicAuth(username, password))
		except:
			return False

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

		if(link != None):
			fullLink = str(prefix + link)
			
			# функция потока загрузки
			def download(_fullLink, stop_event):
				filename = _fullLink.split('/')[-1]
				#dirname  = filename.split('/')[-1][ : len(filename) - 9]

				if not os.path.exists(dlPath):
					try:
						os.makedirs(dlPath)
					except:
						return False

				self.fullPath = dlPath + "\\" + filename
				r = requests.get(_fullLink, auth=HTTPBasicAuth(username, password), stream=True)
				
				self.total = int(r.headers.get('content-length'))
				
				print("File length: " + str(self.total))
				
				with open(self.fullPath, 'wb') as f:
					for chunk in r.iter_content(chunk_size=1048576): 
						if chunk: # filter out keep-alive new chunks
							f.write(chunk)
							self.downloaded += len(chunk)
							f.flush()
							if(stop_event.is_set()):
								f.close()
								self.downloaded = 0
								try:
									os.remove(self.fullPath)
								except:
									pass
								return False
				return self.fullPath
			
			# создание и запуск потока
			self.thread = Thread( target = download, args = (fullLink, self.t_stop, ) )
			self.thread.start()
		else:
			return False

	#def uploadAxxonNextArtifact(self, filename):
	#	# функция потока загрузки
	#	def upload(stop_event):
	#		#filename = self.fullPath.split('\\')[-1]
	#		if not os.path.exists(uplPath):
	#			try:
	#				os.makedirs(uplPath)
	#			except:
	#				return False
	#		self.fullPath = uplPath + "\\" + filename
#
	#		source = open(dlPath + filename, 'rb')
	#		target = open(self.fullPath,     'wb')
#
	#		while(chunk = source.read(32768)):
	#			if chunk: # filter out keep-alive new chunks
	#				target.write(chunk)
	#				self.downloaded += len(chunk)
	#				if(stop_event.is_set()):
	#					source.close()
	#					target.close()
	#					self.downloaded = 0
	#					try:
	#						os.remove(self.fullPath)
	#					except:
	#						pass
	#					return False
	#		return self.fullPath
	#		
	#	# создание и запуск потока
	#	self.uplThread = Thread( target = upload, args = (self.t_stop, ) )
	#	self.uplThread.start()
	#	return True
