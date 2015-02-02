from flask import Flask, request, Response, render_template
from flask.ext.restful import reqparse, abort, Api, Resource
import json

app = Flask(__name__, template_folder="html")
api = Api(app, default_mediatype="application/json")

class Index(Resource):
	def get(self):
		html = render_template("/index.html")
		return Response(html, status = "200", mimetype='text/html')

api.add_resource(Index,
	'/')


if __name__ == '__main__':

	# запуск API
	app.run(host='0.0.0.0', port=5000, debug=True)
