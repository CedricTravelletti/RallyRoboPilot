""" Run a framerate limited version of the game. 

"""
from rallyrobopilot import prepare_game_app, LocalWriter, LocalInjecter, FinishLinesDefiner
from pygame.time import Clock
import time
from pandas import read_pickle


FRAMERATE_LIMIT = 25

from scripts.process_registered_race import *
# df = load_data("./Autopilot/data/raw/race_data_blue.pkl")
df = read_pickle("./race_data.pkl")

app, car = prepare_game_app()
local_writer = LocalWriter(car = car)
# local_injecter = LocalInjecter(car = car, commands_df = df)
# local_injecter = LocalInjecter(car, df, frequency='0.06S')
# finish_line_definer = FinishLinesDefiner(car, "finish_lines.json")

clock = Clock()
time.sleep(1)
while True:
    app.step()
    clock.tick(FRAMERATE_LIMIT)
