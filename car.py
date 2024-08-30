from ursina import *
from ursina import curve
from particles import Particles, TrailRenderer
from raycast_sensor import MultiRaySensor
import json

sign = lambda x: -1 if x < 0 else (1 if x > 0 else 0)
Text.default_resolution = 1080 * Text.size

class Car(Entity):
    def __init__(self, position = (0, 0, 4), rotation = (0, 0, 0), topspeed = 30, acceleration = 0.35, braking_strength = 30, friction = 0.6, camera_speed = 8, drift_speed = 35):
        super().__init__(
            model = "sports-car.obj",
            texture = "sports-red.png",
            collider = "box",
            position = position,
            rotation = rotation,
        )

        # Rotation parent
        self.rotation_parent = Entity()

        # Controls
        self.controls = "wasd"

        # Car's values
        self.speed = 0
        self.velocity_y = 0
        self.rotation_speed = 0
        self.max_rotation_speed = 2.6
        self.steering_amount = 8
        self.topspeed = topspeed
        self.braking_strenth = braking_strength
        self.camera_speed = camera_speed
        self.acceleration = acceleration
        self.friction = friction
        self.drift_speed = drift_speed
        self.drift_amount = 4.5
        self.turning_speed = 5
        self.max_drift_speed = 40
        self.min_drift_speed = 20
        self.pivot_rotation_distance = 1

        self.reset_position = (12, -35, 76)
        self.reset_rotation = (0, 90, 0)

        # Camera Follow
        self.camera_angle = "top"
        self.camera_offset = (0, 60, -70)
        self.camera_rotation = 40
        self.camera_follow = False
        self.change_camera = False
        self.c_pivot = Entity()
        self.camera_pivot = Entity(parent = self.c_pivot, position = self.camera_offset)

        # Pivot for drifting
        self.pivot = Entity()
        self.pivot.position = self.position
        self.pivot.rotation = self.rotation
        self.drifting = False

        # Car Type
        self.car_type = "sports"

        # Particles
        self.particle_time = 0
        self.particle_amount = 0.07 # The lower, the more
        self.particle_pivot = Entity(parent = self)
        self.particle_pivot.position = (0, -1, -2)

        # TrailRenderer
        self.trail_pivot = Entity(parent = self, position = (0, -1, 2))

        self.trail_renderer1 = TrailRenderer(parent = self.particle_pivot, position = (0.8, -0.2, 0), color = color.black, alpha = 0, thickness = 7, length = 200)
        self.trail_renderer2 = TrailRenderer(parent = self.particle_pivot, position = (-0.8, -0.2, 0), color = color.black, alpha = 0, thickness = 7, length = 200)
        self.trail_renderer3 = TrailRenderer(parent = self.trail_pivot, position = (0.8, -0.2, 0), color = color.black, alpha = 0, thickness = 7, length = 200)
        self.trail_renderer4 = TrailRenderer(parent = self.trail_pivot, position = (-0.8, -0.2, 0), color = color.black, alpha = 0, thickness = 7, length = 200)
        
        self.trails = [self.trail_renderer1, self.trail_renderer2, self.trail_renderer3, self.trail_renderer4]
        self.start_trail = True

        # Audio
        self.audio = True
        self.volume = 1
        self.start_fall = True

        # Collision
        self.copy_normals = False
        self.hitting_wall = False

        # Making tracks accessible in update
        self.sand_track = None
        self.grass_track = None
        self.snow_track = None
        self.forest_track = None
        self.savannah_track = None
        self.lake_track = None

        # Graphics
        self.graphics = "fancy"

        # Stopwatch/Timer
        self.timer_running = False
        self.count = 0.0

        self.last_count = self.count
        self.reset_count = 0.0
        self.timer = Text(text = "", origin = (0, 0), size = 0.05, scale = (1, 1), position = (-0.7, 0.43))

        self.laps_text = Text(text = "", origin = (0, 0), size = 0.05, scale = (1.1, 1.1), position = (0, 0.43))
        self.reset_count_timer = Text(text = str(round(self.reset_count, 1)), origin = (0, 0), size = 0.05, scale = (1, 1), position = (-0.7, 0.43))
        
        self.timer.disable()

        self.laps_text.disable()
        self.reset_count_timer.disable()

        self.gamemode = "race"
        self.start_time = False
        self.laps = 0
        self.laps_hs = 0
        self.anti_cheat = 1

        # Drift Gamemode
        self.drift_text = Text(text = "", origin = (0, 0), color = color.white, size = 0.05, scale = (1.1, 1.1), position = (0, 0.43), visible = False)
        self.drift_timer = Text(text = "", origin = (0, 0), size = 0.05, scale = (1, 1), position = (0.7, 0.43))
        self.start_drift = False
        self.drift_score = 0
        self.drift_time = 0
        self.drift_multiplier = 20
        self.get_hundred = False
        self.get_thousand = False
        self.get_fivethousand = False

        # Bools
        self.driving = False
        self.braking = False

        # Multiplayer
        self.multiplayer = False
        self.multiplayer_update = False
        self.server_running = False

        # Shows whether you are connected to a server or not
        self.connected_text = True
        self.disconnected_text = True

        # Camera shake
        self.shake_amount = 0.1
        self.can_shake = False
        self.camera_shake_option = True

        self.username_text = "Username"

        self.model_path = str(self.model).replace("render/scene/car/", "")

        invoke(self.update_model_path, delay = 0.1)

        self.multiray_sensor = MultiRaySensor(self, 11, 90)
        self.multiray_sensor.enable()

    def sports_car(self):
        self.car_type = "sports"
        self.model = "sports-car.obj"
        self.texture = "sports-red.png"
        self.topspeed = 30
        self.acceleration = 0.38
        self.drift_amount = 5
        self.turning_speed = 5
        self.min_drift_speed = 18
        self.max_drift_speed = 38
        self.max_rotation_speed = 3
        self.steering_amount = 8
        self.particle_pivot.position = (0, -1, -1.5)
        self.trail_pivot.position = (0, -1, 1.5)

    def update(self):
        # Stopwatch/Timer
        # Race Gamemode
        if self.gamemode == "race":
            self.laps_text.disable()
            if self.timer_running:
                self.count += time.dt
                self.reset_count += time.dt

        # Read the username
        self.username_text = "Username"

        self.pivot.position = self.position
        self.c_pivot.position = self.position
        self.c_pivot.rotation_y = self.rotation_y
        self.camera_pivot.position = self.camera_offset

        # Camera
        if self.camera_follow:
            # Side Camera Angle
            if self.camera_angle == "side":
                camera.rotation = (35, -20, 0)
                self.camera_speed = 8
                self.change_camera = False
                camera.world_position = lerp(camera.world_position, self.world_position + (20, 40, -50), time.dt * self.camera_speed)
            # Top Camera Angle
            elif self.camera_angle == "top":
                if self.change_camera:
                    camera.rotation_x = 35
                    self.camera_rotation = 40
                self.camera_offset = (0, 60, -70)
                self.camera_speed = 4
                self.change_camera = False
                #camera.rotation_x = self.camera_rotation
                camera.world_position = self.camera_pivot.world_position
                camera.world_rotation_y = self.world_rotation_y
                """
                camera.rotation_x = lerp(camera.rotation_x, self.camera_rotation, 2 * time.dt)
                camera.world_position = lerp(camera.world_position, self.camera_pivot.world_position, time.dt * self.camera_speed / 2)
                camera.world_rotation_y = lerp(camera.world_rotation_y, self.world_rotation_y, time.dt * self.camera_speed / 2)"""
            # Third Person Camera Angle
            elif self.camera_angle == "behind":
                if self.change_camera:
                    camera.rotation_x = 12
                    self.camera_rotation = 40
                self.camera_offset = (0, 10, -30)
                self.change_camera = False
                self.camera_speed = 8
                camera.rotation_x = lerp(camera.rotation_x, self.camera_rotation / 3, 2 * time.dt)
                camera.world_position = lerp(camera.world_position, self.camera_pivot.world_position, time.dt * self.camera_speed / 2)
                camera.world_rotation_y = lerp(camera.world_rotation_y, self.world_rotation_y, time.dt * self.camera_speed / 2)
            # First Person Camera Angle
            elif self.camera_angle == "first-person":
                self.change_camera = False
                self.camera_speed = 8
                camera.world_position = lerp(camera.world_position, self.world_position + (0.5, 0, 0), time.dt * 30)
                camera.world_rotation = lerp(camera.world_rotation, self.world_rotation, time.dt * 30)

        # The y rotation distance between the car and the pivot
        self.pivot_rotation_distance = (self.rotation_y - self.pivot.rotation_y)

        # Drifting
        if self.pivot.rotation_y != self.rotation_y:
            if self.pivot.rotation_y > self.rotation_y:
                self.pivot.rotation_y -= (self.drift_speed * ((self.pivot.rotation_y - self.rotation_y) / 40)) * time.dt
                if self.speed > 1 or self.speed < -1:
                    self.speed += self.pivot_rotation_distance / self.drift_amount * time.dt
                self.camera_rotation -= self.pivot_rotation_distance / 3 * time.dt
                self.rotation_speed -= 1 * time.dt
                if self.pivot_rotation_distance >= 50 or self.pivot_rotation_distance <= -50:
                    self.drift_speed += self.pivot_rotation_distance / 5 * time.dt
                else:
                    self.drift_speed -= self.pivot_rotation_distance / 5 * time.dt
            if self.pivot.rotation_y < self.rotation_y:
                self.pivot.rotation_y += (self.drift_speed * ((self.rotation_y - self.pivot.rotation_y) / 40)) * time.dt
                if self.speed > 1 or self.speed < -1:
                    self.speed -= self.pivot_rotation_distance / self.drift_amount * time.dt
                self.camera_rotation += self.pivot_rotation_distance / 3 * time.dt
                self.rotation_speed += 1 * time.dt
                if self.pivot_rotation_distance >= 50 or self.pivot_rotation_distance <= -50:
                    self.drift_speed -= self.pivot_rotation_distance / 5 * time.dt
                else:
                    self.drift_speed += self.pivot_rotation_distance / 5 * time.dt

        # Gravity
        movementY = self.velocity_y / 50
        direction = (0, sign(movementY), 0)

        # Main raycast for collision
        y_ray = raycast(origin = self.world_position, direction = (0, -1, 0), ignore = [self, ])

        if y_ray.distance <= 5:
            # Driving
            if held_keys[self.controls[0]] or held_keys["up arrow"]:
                self.speed += self.acceleration * 50 * time.dt
                self.speed += -self.velocity_y * 4 * time.dt

                self.camera_rotation -= self.acceleration * 30 * time.dt
                self.driving = True

                # Particles
                self.particle_time += time.dt
                if self.particle_time >= self.particle_amount:
                    self.particle_time = 0
                    self.particles = Particles(self, self.particle_pivot.world_position - (0, 1, 0))
                    self.particles.destroy(1)
            
                # TrailRenderer / Skid Marks
                if self.graphics != "ultra fast":
                    if self.drift_speed <= self.min_drift_speed + 2 and self.start_trail:   
                        if self.pivot_rotation_distance > 60 or self.pivot_rotation_distance < -60 and self.speed > 10:
                            for trail in self.trails:
                                trail.start_trail()
                            self.start_trail = False
                            self.drifting = True
                        else:
                            self.drifting = False
                    elif self.drift_speed > self.min_drift_speed + 2 and not self.start_trail:
                        if self.pivot_rotation_distance < 60 or self.pivot_rotation_distance > -60:
                            for trail in self.trails:
                                if trail.trailing:
                                    trail.end_trail()
                            self.start_trail = True
                            self.drifting = False
                        self.drifting = False
                    if self.speed < 10:
                        self.drifting = False
            else:
                self.driving = False
                if self.speed > 1:
                    self.speed -= self.friction * 5 * time.dt
                elif self.speed < -1:
                    self.speed += self.friction * 5 * time.dt
                self.camera_rotation += self.friction * 20 * time.dt

            # Braking
            if held_keys[self.controls[2] or held_keys["down arrow"]]:
                self.speed -= self.braking_strenth * time.dt
                self.drift_speed -= 20 * time.dt
                self.braking = True
            else:
                self.braking = False

            # Hand Braking
            if held_keys["space"]:
                if self.rotation_speed < 0:
                    self.rotation_speed -= 3 * time.dt
                elif self.rotation_speed > 0:
                    self.rotation_speed += 3 * time.dt
                self.drift_speed -= 40 * time.dt
                self.speed -= 20 * time.dt
                self.max_rotation_speed = 3.0

        # If Car is not hitting the ground, stop the trail
        if self.graphics != "ultra fast":
            if y_ray.distance > 2.5:
                if self.trail_renderer1.trailing:
                    for trail in self.trails:
                        trail.end_trail()
                    self.start_trail = True

        # Steering
        self.rotation_y += self.rotation_speed * 50 * time.dt

        if self.rotation_speed > 0:
            self.rotation_speed -= self.speed / 6 * time.dt
        elif self.rotation_speed < 0:
            self.rotation_speed += self.speed / 6 * time.dt

        if self.speed > 1 or self.speed < -1:
            if held_keys[self.controls[1]] or held_keys["left arrow"]:
                self.rotation_speed -= self.steering_amount * time.dt
                self.drift_speed -= 5 * time.dt
                if self.speed > 1:
                    self.speed -= self.turning_speed * time.dt
                elif self.speed < 0:
                    self.speed += self.turning_speed / 5 * time.dt
            elif held_keys[self.controls[3]] or held_keys["right arrow"]:
                self.rotation_speed += self.steering_amount * time.dt
                self.drift_speed -= 5 * time.dt
                if self.speed > 1:
                    self.speed -= self.turning_speed * time.dt
                elif self.speed < 0:
                    self.speed += self.turning_speed / 5 * time.dt
            else:
                self.drift_speed += 15 * time.dt
                if self.rotation_speed > 0:
                    self.rotation_speed -= 5 * time.dt
                elif self.rotation_speed < 0:
                    self.rotation_speed += 5 * time.dt
        else:
            self.rotation_speed = 0

        # Cap the speed
        if self.speed >= self.topspeed:
            self.speed = self.topspeed
        if self.speed <= -15:
            self.speed = -15
        if self.speed <= 0:
            self.pivot.rotation_y = self.rotation_y

        # Cap the drifting
        if self.drift_speed <= self.min_drift_speed:
            self.drift_speed = self.min_drift_speed
        if self.drift_speed >= self.max_drift_speed:
            self.drift_speed = self.max_drift_speed

        # Cap the steering
        if self.rotation_speed >= self.max_rotation_speed:
            self.rotation_speed = self.max_rotation_speed
        if self.rotation_speed <= -self.max_rotation_speed:
            self.rotation_speed = -self.max_rotation_speed

        # Respawn
        if held_keys["g"]:
            self.reset_car()

        if held_keys["v"]:
            self.multiray_sensor.set_enabled_rays(not self.multiray_sensor.enabled)

        # Reset the car's position if y value is less than -100
        if self.y <= -100:
            self.reset_car()

        # Reset the car's position if y value is greater than 300
        if self.y >= 300:
            self.reset_car()

        # Cap the camera rotation
        if self.camera_rotation >= 40:
            self.camera_rotation = 40
        elif self.camera_rotation <= 30:
            self.camera_rotation = 30

        # Camera Shake
        if self.speed >= 1 and self.driving:
            self.can_shake = True
            if self.pivot_rotation_distance > 0:
                self.shake_amount = self.speed * self.pivot_rotation_distance / 200
            elif self.pivot_rotation_distance < 0:
                self.shake_amount = self.speed * -self.pivot_rotation_distance / 200
        else:
            self.can_shake = False

        # Cap the camera shake amount
        if self.shake_amount <= 0:
            self.shake_amount = 0
        if self.shake_amount >= 0.03:
            self.shake_amount = 0.03

        # If the camera can shake and camera shake is on, then shake the camera
        if self.can_shake and self.camera_shake_option and self.camera_angle != "first-person":
            self.shake_camera()

        # Rotation
        self.rotation_parent.position = self.position

        # Lerps the car's rotation to the rotation parent's rotation (Makes it smoother)
        self.rotation_x = lerp(self.rotation_x, self.rotation_parent.rotation_x, 20 * time.dt)
        self.rotation_z = lerp(self.rotation_z, self.rotation_parent.rotation_z, 20 * time.dt)

        # Check if car is hitting the ground
        if self.visible:
            if y_ray.distance <= self.scale_y * 1.7 + abs(movementY):
                self.velocity_y = 0
                # Check if hitting a wall or steep slope
                if y_ray.world_normal.y > 0.7 and y_ray.world_point.y - self.world_y < 0.5:
                    # Set the y value to the ground's y value
                    self.y = y_ray.world_point.y + 1.4
                    self.hitting_wall = False
                else:
                    # Car is hitting a wall
                    self.hitting_wall = True

                if self.copy_normals:
                    self.ground_normal = self.position + y_ray.world_normal
                else:
                    self.ground_normal = self.position + (0, 180, 0)

                # Rotates the car according to the grounds normals
                if not self.hitting_wall:
                    self.rotation_parent.look_at(self.ground_normal, axis = "up")
                    self.rotation_parent.rotate((0, self.rotation_y + 180, 0))
                else:
                    self.rotation_parent.rotation = self.rotation

                if self.start_fall and self.audio:
                    self.start_fall = False
            else:
                self.y += movementY * 50 * time.dt
                self.velocity_y -= 50 * time.dt
                self.rotation_parent.rotation = self.rotation
                self.start_fall = True

        # Movement
        movementX = self.pivot.forward[0] * self.speed * time.dt
        movementZ = self.pivot.forward[2] * self.speed * time.dt

        # Collision Detection
        if movementX != 0:
            direction = (sign(movementX), 0, 0)
            x_ray = raycast(origin = self.world_position, direction = direction, ignore = [self, ])

            if x_ray.distance > self.scale_x / 2 + abs(movementX):
                self.x += movementX

        if movementZ != 0:
            direction = (0, 0, sign(movementZ))
            z_ray = raycast(origin = self.world_position, direction = direction, ignore = [self, ])

            if z_ray.distance > self.scale_z / 2 + abs(movementZ):
                self.z += movementZ

    def reset_car(self):
        """
        Resets the car
        """
        if self.forest_track.enabled:
            self.position = self.reset_position
            self.rotation = self.reset_rotation

        #   Project car directly on ground when resetting
        y_ray = raycast(origin = self.reset_position, direction = (0,-1,0), ignore = [self,])
        self.y = y_ray.world_point.y + 1.4

        camera.world_rotation_y = self.rotation_y
        self.speed = 0
        self.velocity_y = 0
        self.anti_cheat = 1
        self.timer_running = False
        if self.gamemode == "race":
            self.count = 0.0
            self.reset_count = 0.0
        elif self.gamemode == "time trial":
            self.count = 100.0
            self.reset_count = 100.0
            self.laps = 0
            self.start_time = False
        elif self.gamemode == "drift":
            self.reset_drift_score()
        for trail in self.trails:
            if trail.trailing:
                trail.end_trail()
        self.start_trail = True

    def simple_intersects(self, entity):
        """
        A faster AABB intersects for detecting collision with
        simple objects, doesn't take rotation into account
        """
        minXA = self.x - self.scale_x
        maxXA = self.x + self.scale_x
        minYA = self.y - self.scale_y + (self.scale_y / 2)
        maxYA = self.y + self.scale_y - (self.scale_y / 2)
        minZA = self.z - self.scale_z
        maxZA = self.z + self.scale_z

        minXB = entity.x - entity.scale_x + (entity.scale_x / 2)
        maxXB = entity.x + entity.scale_x - (entity.scale_x / 2)
        minYB = entity.y - entity.scale_y + (entity.scale_y / 2)
        maxYB = entity.y + entity.scale_y - (entity.scale_y / 2)
        minZB = entity.z - entity.scale_z + (entity.scale_z / 2)
        maxZB = entity.z + entity.scale_z - (entity.scale_z / 2)
        
        return (
            (minXA <= maxXB and maxXA >= minXB) and
            (minYA <= maxYB and maxYA >= minYB) and
            (minZA <= maxZB and maxZA >= minZB)
        )

    def reset_timer(self):
        """
        Resets the timer
        """
        self.count = self.reset_count
        self.timer.enable()
        self.reset_count_timer.disable()

    def reset_drift(self):
        """
        Resets the drift
        """
        self.animate_text(self.drift_text, 1.7, 1.1)
        invoke(self.drift_text.animate_position, (-0.8, 0.43), 0.3, curve = curve.out_expo, delay = 0.3)
        invoke(self.reset_drift_text, delay = 0.4)
        self.get_hundred = False
        self.get_thousand = False
        self.get_fivethousand = False

    def reset_drift_text(self):
        """
        Resets the drift text
        """
        self.drift_score += self.count
        self.drift_multiplier = 20
        self.count = 0
        self.drifting = False
        invoke(setattr, self.drift_text, "visible", False, delay = 0.1)
        invoke(setattr, self.drift_text, "position", (0, 0.43), delay = 0.3)

    def reset_drift_score(self):
        self.count = 0
        self.drift_score = 0
        self.drift_multiplier = 20
        self.drifting = False

        if self.sand_track.enabled:
            self.drift_time = 25.0
        elif self.grass_track.enabled:
            self.drift_time = 30.0
        elif self.snow_track.enabled:
            self.drift_time = 50.0
        elif self.forest_track.enabled:
            self.drift_time = 40.0
        elif self.savannah_track.enabled:
            self.drift_time = 25.0
        elif self.lake_track.enabled:
            self.drift_time = 75.0

    def animate_text(self, text, top = 1.2, bottom = 0.6):
        """
        Animates the scale of text
        """
        if self.gamemode != "drift":
            if self.last_count > 1:
                text.animate_scale((top, top, top), curve = curve.out_expo)
                invoke(text.animate_scale, (bottom, bottom, bottom), delay = 0.2)
        else:
            text.animate_scale((top, top, top), curve = curve.out_expo)
            invoke(text.animate_scale, (bottom, bottom, bottom), delay = 0.2)

    def shake_camera(self):
        """
        Camera shake
        """
        camera.x += random.randint(-1, 1) * self.shake_amount
        camera.y += random.randint(-1, 1) * self.shake_amount
        camera.z += random.randint(-1, 1) * self.shake_amount

    def update_model_path(self):
        """
        Updates the model's file path for multiplayer
        """
        self.model_path = str(self.model).replace("render/scene/car/", "")
        invoke(self.update_model_path, delay = 3)

# Class for copying the car's position, rotation for multiplayer
class CarRepresentation(Entity):
    def __init__(self, car, position = (0, 0, 0), rotation = (0, 65, 0)):
        super().__init__(
            parent = scene,
            model = "sports-car.obj",
            texture = "sports-red.png",
            position = position,
            rotation = rotation,
            scale = (1, 1, 1)
        )

        self.model_path = str(self.model).replace("render/scene/car_representation/", "")

        self.text_object = None


# Username shown above the car
class CarUsername(Text):
    def __init__(self, car):
        super().__init__(
            parent = car,
            text = "Guest",
            y = 3,
            scale = 30,
            color = color.white,
            billboard = True
        )
    
        self.username_text = "Guest"

    def update(self):
        self.text = self.username_text