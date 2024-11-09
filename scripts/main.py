from rallyrobopilot import prepare_game_app, LocalWriter
from flask import Flask, request, jsonify
from threading import Thread


# Setup Flask
flask_app = Flask(__name__)
flask_thread = Thread(target=flask_app.run, kwargs={'host': "0.0.0.0", 'port': 5000})
        

app, car = prepare_game_app()
print("Flask server running on port 5000")
flask_thread.start()
local_writer = LocalWriter(car = car)
app.run()
