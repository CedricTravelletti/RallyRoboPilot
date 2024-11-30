from rallyrobopilot import Car, Track, SunLight, MultiRaySensor
from json import loads
from ursina import *

RESOLUTION_X = 256
RESOLUTION_Y = 256


def prepare_game_app(time_scale=1.0):
    from ursina import window, Ursina

    application.time_scale = time_scale

    # Load finish lines.
    with open('finish_lines_blue.json', 'r') as file:
        finish_lines = loads(file.read())['finish_lines']
        print(finish_lines)
    
    # Create Window
    window.vsync = True # Set to false to uncap FPS limit of 60
    app = Ursina(size=(RESOLUTION_X, RESOLUTION_Y))
    print("Asset folder")
    print(application.asset_folder)

    # Set assets folder. Here assets are one folder up from current location.
    application.asset_folder = application.asset_folder.parent
    print("Asset folder")
    print(application.asset_folder)

    window.title = "Rally"
    window.borderless = False
    window.show_ursina_splash = False
    window.cog_button.disable()
    # window.fps_counter.enable()
    window.exit_button.disable()
    
    #   Global models & textures
    #                   car model       particle model    raycast model
    global_models = [ "assets/cars/sports-car.obj", "assets/particles/particles.obj",  "assets/utils/line.obj"]
    #                Car texture             Particle Textures
    global_texs = [ "assets/cars/garage/sports-car/sports-red.png", "sports-blue.png", "sports-green.png", "sports-orange.png", "sports-white.png", "particle_forest_track.png", "red.png"]
    
    # load assets
    track_name = "VisualTrack"
    track = Track(track_name, finish_lines)
    print("loading assets after track creation")
    track.load_assets(global_models, global_texs)
    
    # Car
    car = Car()
    car.sports_car()
    # Tracks
    car.set_track(track)
    
    
    # car.multiray_sensor = MultiRaySensor(car, 15, 90)
    # car.multiray_sensor.enable()
    # Hide rays. 
    # car.multiray_sensor.set_enabled_rays(False)
    
    # Lighting + shadows
    sun = SunLight(direction = (-0.7, -0.9, 0.5), resolution = 3072, car = car)
    ambient = AmbientLight(color = Vec4(0.5, 0.55, 0.66, 0) * 0.75)
    
    render.setShaderAuto()
    
    # Sky
    Sky(texture = "sky")
    
    car.visible = True
    
    mouse.locked = False
    mouse.visible = True
    
    car.enable()
    
    car.camera_angle = "top"
    car.change_camera = True
    car.camera_follow = True
    
    track.activate()
    track.played = True
   
    return app, car
