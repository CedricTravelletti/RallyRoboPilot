from rallyrobopilot import prepare_game_app, LocalWriter, LocalInjecter
from pandas import read_pickle


df = read_pickle("./race_data.pkl")

app, car = prepare_game_app(time_scale=0.5)
# local_writer = LocalWriter(car = car)
local_injecter = LocalInjecter(car, df, frequency='0.02s')
app.run()
