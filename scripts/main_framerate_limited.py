""" Run a framerate limited version of the game. 

"""
from rallyrobopilot import prepare_game_app, LocalWriter, LocalInjecter
from pygame.time import Clock


FRAMERATE_LIMIT = 25

from scripts.process_registered_race import *
df = load_data("./race_data.pkl")

app, car = prepare_game_app()
# local_writer = LocalWriter(car = car)
local_injecter = LocalInjecter(car = car, commands_df = df)

clock = Clock()
while True:
    app.step()
    clock.tick(FRAMERATE_LIMIT)
