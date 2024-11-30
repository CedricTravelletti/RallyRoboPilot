from ursina import *
import socket
import numpy as np
from  pandas import DataFrame
from json import dump

from flask import Flask, request, jsonify
from pandas import to_timedelta


from .sensing_message import SensingSnapshot, SensingSnapshotManager
from .remote_commands import RemoteCommandParser


REMOTE_CONTROLLER_VERBOSE = False
PERIOD_REMOTE_SENSING = 0.02

# Which variables we keep
SENSE_VARS = ['up', 'down', 'left', 'right',
               'absolute_time','last_lap_duration',
               'car_position x','car_position y','car_position z',
               'car_speed','car_angle']

def resample_commands(df, frequency):
    df['absolute_time'] = to_timedelta(df['absolute_time'], unit='s')
    df.set_index('absolute_time', inplace=True)

    # Resample every 0.1 seconds and keep the first row in each interval
    resampled_df = df.resample(frequency).first().dropna().reset_index()

    # Convert the index back to elapsed seconds
    resampled_df['absolute_time'] = resampled_df['absolute_time'].dt.total_seconds()
    return resampled_df

def printv(str):
    if REMOTE_CONTROLLER_VERBOSE:
        print(str)

def get_last_image():
    #   Collect last rendered image
    tex = base.win.getDisplayRegion(0).getScreenshot()
    arr = tex.getRamImageAs("RGB")
    data = np.frombuffer(arr, np.uint8)
    image = data.reshape(tex.getYSize(), tex.getXSize(), 3)
    image = image[::-1, :, :]#   Image arrives with inverted Y axis
    return image

def get_sensing_data(car):
    current_controls = (held_keys['w'] or held_keys["up arrow"],
                        held_keys['s'] or held_keys["down arrow"],
                        held_keys['a'] or held_keys["left arrow"],
                        held_keys['d'] or held_keys["right arrow"])
    car_position = car.world_position
    car_speed = car.speed
    car_angle = car.rotation_y
    raycast_distances = car.multiray_sensor.collect_sensor_values()
    return {'up': current_controls[0],
            'down': current_controls[1],
            'left': current_controls[2], 
            'right': current_controls[3],
            'absolute_time': car.count,
            'last_lap_duration': car.last_lap_duration,
            'car_position x': car_position[0],
            'car_position y': car_position[1],
            'car_position z': car_position[2],
            'car_speed': car_speed,
            'car_angle': car_angle,
            }
    
""" 
    Format the dict returned by process_sensing so that 
    we only save what we need, in lightweight format.
        
"""
def format_data(data):
    formatted_data = [data[key] for key in SENSE_VARS]
    return formatted_data

def save_to_pandas(data, output_file):
    print("Saving to pandas")
    df = DataFrame(data=data, columns=SENSE_VARS) 
    df.to_pickle(output_file)

    
class RemoteController(Entity):
    def __init__(self, car = None, connection_port = 7654, flask_app=None):
        super().__init__()

        self.ip_address = "127.0.0.1"
        self.port = connection_port
        self.car = car

        self.listen_socket = None
        self.connected_client = None

        self.client_commands = RemoteCommandParser()

        self.reset_location = (0,0,0)
        self.reset_speed = (0,0,0)
        self.reset_rotation = 0

        #   Period for recording --> 0.1 secods = 10 times a second
        self.sensing_period = PERIOD_REMOTE_SENSING
        self.last_sensing = -1

        # Setup http route for updating.
        @flask_app.route('/command', methods=['POST'])
        def send_command_route():
            if self.car is None:
                return jsonify({"error": "No car connected"}), 400

            command_data = request.json
            if not command_data or 'command' not in command_data:
                return jsonify({"error": "Invalid command data"}), 400

            try:
                self.client_commands.add(command_data['command'].encode())
                return jsonify({"status": "Command received"}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
        @flask_app.route('/sensing')
        def get_sensing_route():
            return jsonify(get_sensing_data(self.car)), 200

    def update(self):
        self.update_network()
        self.process_remote_commands()
        self.process_sensing()

    def process_sensing(self):
        if self.car is None or self.connected_client is None:
            return

        if time.time() - self.last_sensing >= self.sensing_period:
            snapshot = SensingSnapshot()
            snapshot.current_controls = (held_keys['w'] or held_keys["up arrow"],
                                         held_keys['s'] or held_keys["down arrow"],
                                         held_keys['a'] or held_keys["left arrow"],
                                         held_keys['d'] or held_keys["right arrow"])
            snapshot.car_position = self.car.world_position
            snapshot.car_speed = self.car.speed
            snapshot.car_angle = self.car.rotation_y
            snapshot.raycast_distances = self.car.multiray_sensor.collect_sensor_values()

            #   Collect last rendered image
            snapshot.image = get_last_image()

            msg_mngr = SensingSnapshotManager()
            data = msg_mngr.pack(snapshot)

            self.connected_client.settimeout(0.01)
            try:
                self.connected_client.sendall(data)
            except socket.error as e:
                print(f"Socket error: {e}")

            self.last_sensing = time.time()


    def process_remote_commands(self):
        if self.car is None:
            return

        while len(self.client_commands) > 0:
            try:
                commands = self.client_commands.parse_next_command()
                print("Processing command", commands)
                if commands[0] == b'push' or commands[0] == b'release':
                    if commands[1] == b'forward':
                        held_keys['w'] = commands[0] == b'push'
                    elif commands[1] == b'back':
                        held_keys['s'] = commands[0] == b'push'
                    elif commands[1] == b'right':
                        held_keys['d'] = commands[0] == b'push'
                    elif commands[1] == b'left':
                        held_keys['a'] = commands[0] == b'push'
                              
                # Release all
                if commands[0] == b'release' and commands[1] == b'all':
                    print("received release all command")
                    held_keys['w'] = False
                    held_keys['s'] = False
                    held_keys['d'] = False
                    held_keys['a'] = False


                elif commands[0] == b'set':
                    if commands[1] == b'position':
                        self.car.reset_position = commands[2]
                    elif commands[1] == b'rotation':
                        self.car.reset_orientation = (0, commands[2], 0)
                    elif commands[1] == b'speed':
                        # Todo
                        pass
                    elif commands[1] == b'ray':
                        self.car.multiray_sensor.set_enabled_rays(commands[2] == b'visible')

                elif commands[0] == b'reset':
                    self.car.reset_car()

            #   Error is thrown when commands do not fit the model --> disconnect client
            except Exception as e:
                print("Invalid command --> disconnecting : " + str(e))
                self.connected_client.close()
                self.connected_client = None

    def update_network(self):
        if self.connected_client is not None:
            data = []
            try:
                while True:
                    recv_data = self.connected_client.recv(1024)

                    #received nothing
                    if len(recv_data) == 0:
                        break
                    self.client_commands.add(recv_data)

            except Exception as e:
                printv(e)

        #   No controller connected
        else:
            if self.listen_socket is None:
                self.open_connection_socket()
            try:
                inc_client, address = self.listen_socket.accept()
                print("Controller connecting from " + str(address))
                self.connected_client = inc_client
                # self.connected_client.setblocking(False)
                self.connected_client.settimeout(0.01)

                #   Close listen socket
                self.listen_socket.close()
                self.listen_socket = None
            except Exception as e:
                printv(e)


    def open_connection_socket(self):
        print("Waiting for connections")
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.ip_address, self.port))
        # self.listen_socket.setblocking(False)
        self.listen_socket.settimeout(0.01)
        self.listen_socket.listen()

""" 
    Class to extract race data from the game and save locally. 
    This Writer extracts data at a fixed interval using the main game loop 
    and saves it to disk locally. 

    The main purpose of this Writer is to keep sync with the game, by deferring 
    the sensing to the main loop (instead of pinging via HTTP according to an external 
    timer. 

    It is meant to be used in conjunction with LocalInjecter

"""
class LocalWriter(Entity):
    def __init__(self, car, output_folder):
        super().__init__()

        self.car = car
        self.output_file = output_file=f"./race_data.pkl"
        self.race_data = []

        #   Period for recording --> 0.1 secods = 10 times a second
        self.sensing_period = PERIOD_REMOTE_SENSING
        self.last_sensing = -1

        self.sensing_id = 0
        self.output_folder = output_folder

    def take_screenshot(self, video_name, sensing_id):
        base.screenshot(
                namePrefix=self.output_folder + f'{str(self.sensing_id).zfill(4)}.png',
                defaultFilename=0)

    def update(self):
        # self.process_sensing()
        dt = time.time() - self.last_sensing 
        if dt >= self.sensing_period:
            current_controls = (held_keys['w'] or held_keys["up arrow"],
                            held_keys['s'] or held_keys["down arrow"],
                            held_keys['a'] or held_keys["left arrow"],
                            held_keys['d'] or held_keys["right arrow"])
            car_position = self.car.world_position
            car_speed = self.car.speed
            car_angle = self.car.rotation_y

            self.take_screenshot(self.experiment_id, self.sensing_id)
            data = {
                'sensing_id': self.sensing_id,
                'up': current_controls[0],
                'down': current_controls[1],
                'left': current_controls[2], 
                'right': current_controls[3],
                'absolute_time': self.car.count,
                'last_lap_duration': self.car.last_lap_duration,
                'car_position x': car_position[0],
                'car_position y': car_position[1],
                'car_position z': car_position[2],
                'car_speed': car_speed,
                'car_angle': car_angle,
                }
            self.last_sensing = time.time()
            data_form = format_data(data)
            self.race_data.append(data_form)
            self.sensing_id += 1

        if held_keys["g"]:
            save_to_pandas(self.race_data, self.output_folder + self.output_file)

    def process_sensing(self, data_gatherer):
        dt = time.time() - self.last_sensing 
        if dt >= self.sensing_period:
            print(dt)
            data = get_sensing_data(self.car)
            self.last_sensing = time.time()
            data_form = format_data(data)
            data_gatherer.append(data_form)

""" 
    Class for injecting command into the game, read from a local file 
    (all-at-once). 
    This injecter reads a sequence of commands from a file and replays them in 
    the game.

    The main purpose of this Injecter is to keep sync with the game, by directly 
    injecting command in the game's main loop.

    It is meant to be used in conjunction with LocalWriter

    Parameters
    ----------
    car: the Car entity from the running game
    commands_df: a DataFrame containing the commands sequence and metadata. 
                 Should be of the same format as the ones produced by the LocalWriter.

"""
class LocalInjecter(Entity):
    def __init__(self, car, commands_df, frequency=None):
        super().__init__()
        self.car = car

        # Resample and remove endpoints.
        if frequency is not None:
            commands_df = resample_commands(commands_df[1:], frequency)
        self.commands_df = commands_df
        self.sensing_period = PERIOD_REMOTE_SENSING
        self.last_sensing = -1
        self.is_running = False
        self.current_command_ind = 0
        self.launch_count = 0
        self.sync_threshold = 0.005

    def update(self):
        # Make sure we only run once.
        if held_keys["r"] and self.launch_count == 0:
            self.is_running = True
            print("Set runnin to " + str(self.is_running))
            self.init_car(self.car, self.commands_df)

            # Send first command
            current_command = self.commands_df.iloc[self.current_command_ind]
            self.current_command_ind += 1
            self.send_command(current_command)
            self.offset = self.car.count - current_command['absolute_time']

            self.launch_count += 1

        if self.is_running:
            current_command = self.commands_df.iloc[self.current_command_ind]
            if np.abs(self.car.count - current_command['absolute_time'] - self.offset) < self.sync_threshold:
                print("Sending")
                # self.process_next_command()
                self.send_command(current_command)
                self.current_command_ind += 1
                # time_offset = current_command['absolute_time'].item() - time.time()
                self.last_sensing = self.car.count
            # Otherwise re-send last command.
            else:
                self.send_command(current_command)

    def process_next_command(self):
        current_command = self.commands_df.iloc[self.current_command_ind]
        self.send_command(current_command)
        self.current_command_ind += 1

        time_offset = current_command['absolute_time'].item() - self.car.count
        print("offset " + time_offset)

    def send_command(self, command):
        held_keys['w'] = bool(command['up'])
        held_keys['s'] = bool(command['down'])
        held_keys['d'] = bool(command['right'])
        held_keys['a'] = bool(command['left'])

    """ 
        Initialize car so that its parameters (position, speed, angle) 
        are as in the first row of the command sequence. 

    """
    def init_car(self, car, commands_df):
        car.world_position = Vec3(
            commands_df.iloc[0]['car_position x'].item(),
            commands_df.iloc[0]['car_position y'].item(),
            commands_df.iloc[0]['car_position z'].item())
        car.speed = commands_df.iloc[0]['car_speed'].item()
        car.rotation_y = commands_df.iloc[0]['car_angle'].item()
        self.time_offset = commands_df.iloc[0]['absolute_time'].item() - self.car.count
        print("time offset" + str(self.time_offset))
        
        
""" 
    Class to define finish lines manuall while driving. 
    Upon hitting I, this will define a finish line at the current car position 
    with orientation perpendicular to the car. Finish lines are stored 
    in a list and then written to JSON.

"""
class FinishLinesDefiner(Entity):
    def __init__(self, car, output_file):
        super().__init__()

        self.car = car
        self.output_file = output_file
        self.finish_lines = []


    def update(self):
        if held_keys["i"]:
            self.finish_lines.append(self.create_finish_line())
        if held_keys["o"]:
            with open(self.output_file, "w") as outfile: 
                dump({"finish_lines": self.finish_lines}, outfile)

    def create_finish_line(self):
        X_SCALE = 50
        Y_SCALE = 0.01
        car_position = self.car.world_position
        car_angle = self.car.rotation_y
        finish_line = {'finish_line_position': [car_position[0], car_position[1], car_position[2]],
                       'finish_line_rotation': [0, car_angle, 0],
                       'finish_line_scale': [X_SCALE, 5, Y_SCALE]
                       }
        print(finish_line)
        return finish_line
                       
