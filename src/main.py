'''
Created on Mar 2, 2016
@author: yoav
'''
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.properties import *
from kivy.clock import Clock
from kivy.core.window import Window
from collections import defaultdict
from kivy.uix.widget import Widget
from kivy.uix.button import Button
import itertools
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
import cmath
import math
from math import radians, tan, atan, sin, cos
import random
from kivy.config import Config, ConfigParser
import kivyoav.autosized_label
import os
from kivy.uix.settings import SettingItem
from kivyoav.autosized_label import AutoSizedLabel
from kivy.uix.popup import Popup
from kivy.core.audio import SoundLoader
import json
import time
from kivy.animation import Animation

sm = ScreenManager()

KEYS = defaultdict(lambda: None)
import sys


#very ugly fix for the sdl2.joystick issue ...
del sys.modules['sdl2']
from sdl2 import joystick
for joy_i in range(joystick.SDL_NumJoysticks()):
    joystick.SDL_JoystickOpen(joy_i)



class Sprite(Scatter):



    source = StringProperty('')
    radius = NumericProperty(0.0)
    thrust =  NumericProperty(0.0)



    def __init__(self, game, velocity_x=0.0, velocity_y=0.0,
                 **kwargs):
        self.game = game
        attrs = {}
        for attr in 'rgba':
            if attr in kwargs:
                attrs[attr] = kwargs.pop(attr)
        super(Sprite, self).__init__( **kwargs )
        for attr, value in attrs.items():
            setattr(self, attr, value)

        self.velocity_x = velocity_x
        self.velocity_y = velocity_y

    def check_wall_collision(self):
        x, y = self.center
        if x  < 0:
            return True
        if x  > GlobalStuff.right:
            return True
        if y > GlobalStuff.top:
            return True
        if y < 0:
            return True

    def update(self, plats=[],):
        thrust = self.thrust
        y_t = sin(radians(self.rotation)) * thrust
        x_t = cos(radians(self.rotation)) * thrust

        self.velocity_x += x_t
        self.velocity_y += y_t

        self.y += self.velocity_y
        self.x += self.velocity_x

#         self.velocity_x *= 0.998
#         self.velocity_y *= 0.998



    def distance(self, other):
        a = (self.center_x - other.center_x) ** 2
        b = (self.center_y - other.center_y)  ** 2
        return a+b


    def collide(self, other, area=0):
        #this may make the game faster
        if area==0 and not self.collide_widget(other):
            return
        d = self.distance(other)
        if d < ((self.radius+other.radius+area)**2):
            return 1



class GlobalStuff(object):


    @classmethod
    def init(cls):
        cls.right = Window.width
        cls.left = 0
        cls.top = Window.height
        cls.buttom = 0
        cls.center_x = Window.width / 2
        cls.center_y = Window.height / 2
        cls.size = cls.width, cls.height = Window.width, Window.height


class Bullet(Sprite):

    blow = NumericProperty(1.0)
    damage = NumericProperty(1)

    def __init__(self, game, owner, direction, **kw):
        super(Bullet, self).__init__(game, **kw)
        self.rotation = direction#owner.rotation
        self.velocity_x = owner.velocity_x + cos(radians(self.rotation)) * 10
        self.velocity_y = owner.velocity_y +  sin(radians(self.rotation)) * 10

        self.active = True
        self.first = 1
        self.owner = owner

        self.center = -200, -200
        self.blow_rate = 2.0
        self.max_counter = 100
        self.counter = 0
        self.a = 1
    def hit_by(self, other):
        if self.active:
            self.active = False
            self.counter = 40


    def update(self):
        if self.first:
            self.center = self.owner.center
            self.first=0
        self.counter +=1
        bingo = False
        if self.active:
            bingo = self.game.check_player_collision(self, [self.owner])

        if bingo:
            self.active = False
            bingo.hit_by(self)
            self.counter = 25
        if self.counter > self.max_counter:
            self.game.remove_bullet(self)
            self.active = False
        if not self.active:
            self.velocity_x *= 0.75
            self.velocity_y *= 0.75
            self.blow *= self.blow_rate
            self.blow_rate *= 0.90
        super(Bullet, self).update()

class BigBullet(Bullet):

    def __init__(self, *args, **kw):
        super(BigBullet, self).__init__(*args, **kw)
        self.size_hint_x *= 2
        self.size_hint_y *= 2

class HomingMissle(Bullet):



    def update(self):
        speed = 0.5
        super(HomingMissle, self).update()
        p = self.game.check_player_collision(self, [self.owner], self.owner.radius*10)
        if p:

            self.velocity_x += speed if p.center_x > self.center_x else -speed
            self.velocity_y += speed if p.center_y > self.center_y else -speed


class SineMissle(Bullet):
    def __init__(self, game, owner, direction, **kw):
        super(SineMissle, self).__init__(game, owner, owner.rotation, **kw)
        self.speed_x = math.cos(radians(self.rotation)) * 30
        self.speed_y = math.sin(radians(self.rotation)) * 30
        self.max_counter = 200

    def update(self):
        #TBD: play with the 10 value below (in the angle - the Dgima value, and in the speed)
        angle = (self.counter * 10) % 360
        if angle < 90 or angle > 270:
            self.velocity_x = 10 * math.cos(radians(self.rotation-45))
            self.velocity_y = 10 * math.sin(radians(self.rotation-45))
        else:
            self.velocity_x = 10 * math.cos(radians(self.rotation+45))
            self.velocity_y = 10 * math.sin(radians(self.rotation+45))
        super(SineMissle, self).update()

class Mine(Bullet):

    def __init__(self, game, owner, **kw):
        super(Mine, self).__init__(game, owner, owner.rotation, **kw)
        self.velocity_x = 0  #owner.velocity_x + math.cos(radians(self.rotation)) * 10
        self.velocity_y = 0  #owner.velocity_y + math.sin(radians(self.rotation)) * 10

        self.blow_rate = 1.2
        self.max_counter = 500

    def update(self):
        if self.counter == 75:
            self.owner = None
            Animation(a=0, d=0.8).start(self)

        super(Mine, self).update()
        if not self.active:
            self.a = 1


class SplitBullet(Bullet):
    def __init__(self, game, owner, **kw):
        super(SplitBullet, self).__init__(game, owner, owner.rotation, **kw)
        self.velocity_x = owner.velocity_x + math.cos(radians(self.rotation)) * 10
        self.velocity_y = owner.velocity_y + math.sin(radians(self.rotation)) * 10
        self.max_counter = 50

    def update(self):
        print (self.center)
        super(SplitBullet, self).update()
        if self.counter == (self.max_counter-1):
            # TBD: play with the counter and number of bullets.
            num_of_bullets = 8
            angle = 360/num_of_bullets
            for i in range(num_of_bullets):
                b = Bullet(self.game, self.owner, i * angle)
                b.center = self.center
                b.counter = b.max_counter - 50
                b.first = 0
                self.game.add_bullet(b)


class AirCraft(Sprite):
    lives = NumericProperty(5)
    hit_sounds = [SoundLoader.load('Music/shots/hit.mp3'),SoundLoader.load('Music/shots/hit.mp3'),SoundLoader.load('Music/shots/hit.mp3'),
                  SoundLoader.load('Music/shots/hit.mp3'),SoundLoader.load('Music/shots/hit.mp3'),
                  SoundLoader.load('Music/shots/ouch.mp3'),SoundLoader.load('Music/shots/ouch.mp3'),SoundLoader.load('Music/shots/ouch.mp3'),
                  SoundLoader.load('Music/shots/ouch.mp3'),SoundLoader.load('Music/shots/ouch.mp3')]

    dead_sounds = [SoundLoader.load('Music/shots/dead.mp3')
                     for _ in range(5)]
    fire_sounds = [SoundLoader.load('Music/shots/gunshot-00.mp3')
                     for _ in range(50)]
    random.shuffle(fire_sounds)
    for sound in fire_sounds:
        sound.volume = 0.5
    random.shuffle(hit_sounds)
    next_dead_sound = itertools.cycle(dead_sounds)
    next_hit_sound = itertools.cycle(hit_sounds)
    next_fire_sound = itertools.cycle(fire_sounds)

    def __init__(self, game, **kw):
        super(AirCraft, self).__init__(game, **kw)
        self.velocity_x = 0.0 * math.cos(radians(self.rotation))
        self.velocity_y = 0.0 * math.sin(radians(self.rotation))
        self.bullets = 1
        self.reload = 50
        self.reload_time = 20
        self.speed = 0.2
        self.special_bullets = []
        self.lives = 1



    def update(self):
        if self.lives<=0 or self.check_wall_collision():
            self.game.mark_dead(self)
        self.reload -= 1
        super(AirCraft, self).update()
        self.velocity_x *=0.99
        self.velocity_y *=0.99

    def hit_by(self, something):
        self.lives -= min(self.lives, something.damage)
        if self.lives == 0:
            next(self.next_dead_sound).play()
        else:
            next(self.next_hit_sound).play()

    def fire(self):
        if self.reload > 0:
            return
        self.reload = self.reload_time
        next(self.next_fire_sound).play()
        d  = self.rotation
        sb = list(self.special_bullets)
        for i in range(self.bullets):
            B = sb.pop() if sb else Bullet
            bullet = B(self.game, self, d + (i*8*((i%2) or -1)))
            self.game.add_bullet(bullet)



class Drone(AirCraft):


    def __init__(self, game, creator):
        owner = self.owner = creator.owner
        self.rotation = owner.rotation
        super(Drone, self).__init__(game)
        self.speed = 0.1
        self.reload_time = self.owner.reload_time * 2
        self._first_time = 1
        self.name = "Drone"
        self.creator= creator
        self.r = owner.r
        self.g = owner.g
        self.b = owner.b
        self.a = owner.a

    def update(self):
        if self._first_time:
            self._first_time = 0
            self.center = self.owner.center
            self.rotation= self.owner.rotation

        area = self.radius
        self.thrust = self.speed
        p = None
        for _ in range(10):
            area += self.radius * 10
            p = self.game.check_player_collision(self, [self, self.owner], area)
            if p: break
        if p:
            b = p.center_x - self.center_x
            a = p.center_y - self.center_y
            if b!=0:
                r = atan(abs(a)/float(abs(b)))
                d = math.degrees(r)
                #print('angle = %d a=%s b=%s' % (d, a, b))
                if a < 0:
                    d = -d
                if b < 0:
                    d = 180 - d
                self.rotation = d % 360

        self.fire()
        super(Drone, self).update()
        self.velocity_x *= 0.99
        self.velocity_y *= 0.99

    def dead(self):
        self.creator.drone_dead()


class Player(AirCraft):


    def __init__(self, game, name, team, keys, **kw):
        super(Player, self).__init__(game, **kw)

        self.keys = dict(keys)
        self.name = name
        self.team = team
        self.speed = 0.33
        self.lives = 5
        self.specials_defense = None#set()
        self.specials_attack = None#set()

    def add_special_defense(self, s):
        self.specials_defense = s

    def add_special_attack(self, s):
        self.specials_attack = s

    def update(self,  user_pressed=KEYS):

        if self.lives <= 0 or self.check_wall_collision():
            self.lives = 0
            self.counter = 20
            self.game.mark_dead(self)
            self.update = self.play_dead
        keys = self.keys
        self.thrust = 0
        if user_pressed[keys['left']]:
            self.rotation += 10
            #print(self.rotation)
        elif user_pressed[keys['right']]:
            self.rotation -= 10
            #print(self.rotation)
        if user_pressed[keys['thrust']]:
            self.thrust = self.speed
        if user_pressed[keys['fire']]:
            self.fire()
        if user_pressed[keys['special_defense']]:
            self.activate_special_defense()
        if user_pressed[keys['special_attack']]:
            self.activate_special_attack()

        super(Player, self).update()
        self.velocity_x *= 0.99
        self.velocity_y *= 0.99

    def play_dead(self):
        self.counter -= 1
        if self.counter < 0:
            self.game.remove_player(self)
            self.game = None
            return
        self.size_hint_x * 1.05
        self.a *= 0.9
        super(Player, self).update()

    def activate_special_defense(self):
        if self.specials_defense != None:
            self.specials_defense.activate(self)

    def activate_special_attack(self):
        if self.specials_attack != None:
            self.specials_attack.activate(self)




class BaseGift(Sprite):

    src = StringProperty("")

    def __init__(self, game, **kwargs):
        super(BaseGift, self).__init__(game, **kwargs)
        self.src = self.SOURCE
        self.count = 0

    def update(self):
        self.count = (self.count+1) % 3
        if self.count:
            p = self.game.check_player_collision(self, filter=self.game.drones)
            if p:
                self.apply_gift(p)
                self.game.remove_gift(self)
                return
        else:
            if self.check_wall_collision():
                self.game.remove_gift(self)
                return
        super(BaseGift, self).update()

    def apply_gift(self, player):
        raise NotImplementedError("BaseGift is not a real Gift :)")

class SpeedGift(BaseGift):

    SOURCE = "imgs/speedometer-32.png"

    def apply_gift(self, player):
        player.speed *= 1.3
        print("player %s thrust is %d" % (player.name, player.thrust))

class LivesGift(BaseGift):

    SOURCE = "imgs/heart.png"

    def apply_gift(self, player):
        print("player %s had %d lives" % (player.name, player.lives))
        player.lives += 1
        print("and now he has %d lives" % (player.lives))

class ExtraShotGift(BaseGift):

    SOURCE = "imgs/triple_bullet.png"

    def apply_gift(self, player):
        player.bullets += 1

class HomingMissleGift(BaseGift):

    SOURCE = 'imgs/homing_missle_gift.png'

    def apply_gift(self, player):
        player.special_bullets.append(HomingMissle)

class SineMissleGift(BaseGift):

    SOURCE = 'imgs/skull.png'

    def apply_gift(self, player):
        player.special_bullets.append(SineMissle)

class BiggerBulletGift(BaseGift):

    SOURCE = 'imgs/big_bullet_gift.png'

    def apply_gift(self, player):
        player.special_bullets.append(BigBullet)


class FasterReloadGift(BaseGift):
    SOURCE = "imgs/ammo.png"

    def apply_gift(self, player):
        player.reload_time -= 5
        if player.reload_time <=5:
            player.reload_time = 5

class SlowerReloadGift(BaseGift):
    SOURCE = "imgs/skull.png"

    def apply_gift(self, player):
        player.reload_time += 5

class ReverseKeysGift(BaseGift):
    SOURCE = "imgs/skull.png"

    def apply_gift(self, player):
        temp = player.keys['right']
        player.keys['right'] = player.keys['left']
        player.keys['left'] = temp


class ElectroMagnetShield(BaseGift):

    SOURCE = "imgs/e-m-shield.png"

    def apply_gift(self, player):
        player.add_special_defense(ElectroMagnet())

class InvisibilityGift(BaseGift):

    SOURCE = "imgs/invisible.png"

    def apply_gift(self, player):
        player.add_special_defense(Invisibility())


class DroneGift(BaseGift):
    SOURCE = 'imgs/drone.png'

    def apply_gift(self, player):
        player.add_special_attack(FightingDroneSpecial())


class MineGift(BaseGift):
    SOURCE = 'imgs/mine.png'

    def apply_gift(self, player):
        player.add_special_attack(MineSpecial())


class SplitBulletGift(BaseGift):
    SOURCE = 'imgs/split_bullet.png'

    def apply_gift(self, player):
        player.add_special_attack(SplitBulletSpecial())


gift_types = [SplitBulletGift]#[SpeedGift, LivesGift, ExtraShotGift, HomingMissleGift,
              #FasterReloadGift, ReverseKeysGift, SlowerReloadGift, ElectroMagnetShield,
              #DroneGift, MineGift, BiggerBulletGift, SineMissleGift, InvisibilityGift,
              #]

class Special(object):

    COOLDOWN = 3

    def __init__(self):
        self.last_activation = 0

    def activate(self, owner):
        self.owner = owner
        t = time.time()
        if t - self.last_activation > self.COOLDOWN:
            self.last_activation = t
            self.engage()

class FightingDroneSpecial(Special):

    COOLDOWN = 10

    def __init__(self):
        super(FightingDroneSpecial, self).__init__()
        self.active = 0

    def engage(self):
        if self.active:
            return
        self.active = 1
        owner = self.owner
        d = Drone(owner.game, creator=self,
                  )

        d.rotation = owner.rotation
        d.center = owner.center
        d.size_hint = 0.01, 0.01
        owner.game.add_drone(d)

    def drone_dead(self):
        self.active = 0
        self.last_activation = time.time()



class ElectroMagnet(Special):

    def engage(self):
        owner = self.owner
        game = owner.game
        area = owner.radius * 10
        game.add_pulse(self.owner.center, area)
        speed = 10
        for obj in game.flying_objects:
            if obj == owner: continue
            if obj.collide(owner, area):
                diffx = owner.center_x - obj.center_x
                diffy =  owner.center_y - obj.center_y

                ratio = abs(diffx) / (abs(diffx)+abs(diffy) + 0.1)
                obj.velocity_x -= ratio * speed * (1 if diffx>0 else -1)
                obj.velocity_y -= (1-ratio) * speed * (1 if diffy>0 else -1)

class Invisibility(Special):
    COOLDOWN = 7.5

    
    def reappear(self, dt=None):
        Animation(a=self._old_alpha, d=0.165).start(self.owner)
    
    
    def engage(self):
        if self.owner.a < 0.2:
            return
        self._old_alpha = self.owner.a
        Animation(a=0.0, d=0.165).start(self.owner)
        Clock.schedule_once(self.reappear, timeout=3.1)
         
class MineSpecial(Special):
    COOLDOWN = 3.5

    def __init__(self):
        super(MineSpecial, self).__init__()

    def engage(self):
        owner = self.owner
        game = owner.game
        mine = Mine(game, owner=self.owner)
        mine.size_hint = 0.05, 0.05
        game.add_bullet(mine)

class SplitBulletSpecial(Special):
    COOLDOWN = 3.5

    def __init__(self):
        super(SplitBulletSpecial, self).__init__()

    def engage(self):
        owner = self.owner
        game = owner.game
        SpB = SplitBullet(game, owner=self.owner)
        game.add_bullet(SpB)


def gen_gift(*args, **kw):
    return random.choice(gift_types)(*args, **kw)
    

class Planet(Sprite):
    
    START_COUNT = 0
    
    color = ListProperty([1.0, 0.0, 0.0, 0.5])
    def __init__(self, game, color, size_hint, pos_hint):
        self.color = color
        self.damage = 99
        super(Planet, self).__init__(game, size_hint=size_hint, pos_hint=pos_hint)
        
        self.action_count = 3
        self.START_COUNT += 1 
        self.START_COUNT %= self.action_count
        
        self.count = self.START_COUNT
        
    def update(self):
        if self.count < self.action_count:
            self.count += 1
            return
        self.count = 0
        area = self.radius * 3
        for obj in self.game.bullets:
            if obj.collide(self, area):
                if obj.collide(self):
                    obj.hit_by(self)
                else:
                    self._attract(obj)
        for obj in self.game.flying_objects:
            if obj.collide(self):
                obj.hit_by(self)
                    
        
    def _attract(self, obj):
        _abs = abs
        diffx = obj.center_x - self.center_x
        diffy = obj.center_y - self.center_y
        speed = 1 * self.action_count
        ratio = _abs(diffx) / (_abs(diffy)+_abs(diffx))
        speedx = speed * ratio
        speedy = speed * (1-ratio)
        obj.velocity_x -= speedx if diffx > 0 else -speedx
        obj.velocity_y -= speedy if diffy > 0 else -speedy

class Arrow(Sprite):
    
    def __init__(self, game, **kw):
        
        self.power = 3.5
        super(Arrow, self).__init__(game, **kw)
        self.rotation = kw['rotation']
    def update(self):
        for obj in self.game.flying_objects:
            if obj.collide(self):
                self.apply_speed(obj)
                
    def apply_speed(self, obj):
        p = self.power
        angle = radians(self.rotation)
        obj.velocity_y += sin(angle) * p
        obj.velocity_x += cos(angle) * p
        
        

class Cloud(Sprite):

    #color = ListProperty([1.0, 0.0, 0.0, 0.5])

    def __init__(self, game, size_hint, pos_hint):
        self.damage = 99
        self._objs = set()
        super(Cloud, self).__init__(game, size_hint=size_hint, pos_hint=pos_hint)
        self.auto_bring_to_front = True

class Portal(Sprite):
    START_COUNT = 0

    color = ListProperty([1.0, 0.0, 0.0, 0.5])

    def __init__(self, game, color, size_hint, pos_hint, portal_id, destination_id):
        self.color = color
        self.damage = 99
        self.portal_id = portal_id
        self.destination_id = destination_id
        self._objs = set()
        super(Portal, self).__init__(game, size_hint=size_hint, pos_hint=pos_hint)



    def update(self):
        
        for obj in itertools.chain(self.game.players, self.game.drones):
            if obj.collide(self) and not obj in self._objs:
                
                self.obj_in_portal(obj)
                
    def obj_in_portal(self, obj):
        destination_id = self.destination_id#(self.portal_id + 1) % len(self.game.portals)
        entry_point_x = (self.center_x - obj.center_x) * 1.20
        entry_point_y = (self.center_y - obj.center_y) * 1.20
        scale = obj.scale
        a = Animation(center_x=self.center_x, center_y=self.center_y, scale=0.25, d=0.150)
        
        
        def f(obj):
            self.unmark(obj)
            portal = self.game.portals[destination_id]
            obj.center = portal.center
            a = Animation(center_x= portal.center_x + entry_point_x,
                          center_y= portal.center_y + entry_point_y,
                          scale=scale, d=0.150)
            def b(obj):
                portal.unmark(obj)
            a.on_complete = b
            portal.mark(obj)
            a.start(obj)
            
                
        a.on_complete = f
        self.mark(obj)
        a.start(obj)
        
    def mark(self, obj):
        self._objs.add(obj)
        
    def unmark(self, obj):
        self._objs.remove(obj)

class Pulse(Sprite):
    
    pass


class Game(Screen):
    area = ObjectProperty(None)
    foreground = ObjectProperty(None)
    
    
    def __init__(self, **kw):
        Screen.__init__(self, **kw)
        self.player_nums = []
        theme = random.choice(['Music/levels/35-battle-1-hurry.mp3',
                               'Music/levels/19-battle-theme-1.mp3', 'Music/levels/20-battle-theme-2.mp3', 
                               'Music/levels/36-battle-2-hurry.mp3'])
        self.background_sound = SoundLoader.load(theme) 
        
        
    def setup(self, players, level):
        self.players_setup = players
        self.level = level
        
    @property
    def flying_objects(self):
        return itertools.chain(self.players, self.bullets, self.drones)
        

    def _create_arrows(self):
        for arrow in self.level.get('arrows', []):
            a = Arrow(self, 
                pos_hint={'center_x':arrow['x'], 
                    'center_y':arrow['y']}, 
                size_hint=arrow['size'],
                rotation=arrow['rotation'])
            self.area.add_widget(a)
            self.arrows.append(a)
        


    def _create_portals(self):
        for portal in self.level.get('portals', []):
            p = Portal(self, 
                color=portal['color'], 
                size_hint=portal['size'], 
                pos_hint={'center_x':portal['x'], 
                    'center_y':portal['y']}, 
                portal_id=portal['portal_id'],
                destination_id=portal['destination_id'])
            self.area.add_widget(p)
            self.portals.append(p)
        


    def _create_plantes(self, p):
        for planet in self.level['planets']:
            p = Planet(self, 
                color=planet['color'], 
                size_hint=planet['size'], 
                pos_hint={'center_x':planet['x'], 
                    'center_y':planet['y']})
            self.area.add_widget(p)
            self.planets.append(p)
        
        


    def _create_clouds(self):
        for cloud in self.level.get('clouds', []):
            c = Cloud(self, 
                size_hint=cloud['size'], 
                pos_hint={'center_x':cloud['x'], 
                    'center_y':cloud['y']})
            self.foreground.add_widget(c)
         
            self.clouds.append(c)

    def on_enter(self, *args):
        Screen.on_enter(self, *args)
        for a in [self.area, self.foreground]:
            for w in list(a.children) :
                a.remove_widget(w)
        
        self.players = []
        self.planets = []
        self.portals = []
        self.arrows = []
        self.clouds = []
        self.gifts = []
        self.dead_players = []
        self.bullets = []
        self.drones = []
        self.mines = []
        h = GlobalStuff.height * 0.10
        w = GlobalStuff.width * 0.10
        positions = [ (w, h, 45), (w * 5, h * 9, -90), (w * 9, h, 135),
                      (w, h * 9, -45), (w * 9, h * 9, -135), (w * 5, h, 90),
                      ]
        
        self._create_portals()
        self._create_arrows()   
        

        for p, s, pos in zip(ConfigScreen.players, self.players_setup, positions):
            if not s['play']: continue
            p = Player(self, team=s['team_name'], **p)
            p.rotation = pos[2]
            p.center = pos[:2]
            
            self.players.append(p)
            self.area.add_widget(p)
            
        self._create_plantes(p)

        self._create_clouds()

        
        self.background_sound.loop = True
        self.background_sound.volume = 0.5
        self.background_sound.play()
        self.label = Label(text="FPS: ?", pos=(200,200)) 
        self.area.add_widget(self.label)
        self._loop = Clock.schedule_interval(self._update, 1.0/30)
        self.count = 0.0
        self.frames_count = 1
        
    def on_leave(self, *args):
        Screen.on_leave(self, *args)
        self._loop.cancel()
        self.background_sound.stop()

    def add_drone(self, drone):
        self.drones.append(drone)
        self.area.add_widget(drone)
    
        
    def add_bullet(self, bullet):
        self.bullets.append(bullet)
        self.area.add_widget(bullet)
    
    def remove_bullet(self, bullet):
        if bullet in self.bullets:
            self.bullets.remove(bullet)
            self.area.remove_widget(bullet)

    def mark_dead(self, a):
        if a in self.players:
            self.players.remove(a)
            self.dead_players.append(a)
        if a in self.drones:
            self.drones.remove(a)
            self.area.remove_widget(a)
            a.dead()
            
    def remove_player(self, player):
        self.dead_players.remove(player)
        self.remove_widget(player)

    def check_player_collision(self, obj, filter=[], area=0):
        
        for p in itertools.chain(self.players,self.drones):
            if p.collide(obj, area):
                if p not in filter:
                    return p
    
                
    def add_pulse(self, pos, size):
        
        pulse = Pulse(self, center=pos)
        self.area.add_widget(pulse)
        def remove_pulse(*args):
            self.area.remove_widget(pulse)
        x,y = pulse.size_hint
        a = Animation(d=0.2, center=pos, size_hint_x=x*10, size_hint_y=y*10)
        a.on_complete = remove_pulse
        a.start(pulse)
        
                
    def remove_gift(self, gift):
        self.gifts.remove(gift)
        self.area.remove_widget(gift)

    def create_gift(self):
        p = random.choice(['top', 'buttom', 'left', 'right'])
        stuff = {'size_hint': (0.03, 0.03)}
        speed = random.choice([1, 2, 3])
        if p in ['left', 'right']:
            y = (GlobalStuff.top - 20) * random.random() + 10
            if p == 'left':
                x = 50
                stuff['velocity_x'] = 1* speed
            else:
                x = GlobalStuff.right
                stuff['velocity_x'] = -1*speed
        else:
            x = (GlobalStuff.right - 20) * random.random() + 10
            if p == 'top':
                y = GlobalStuff.top
                stuff['velocity_y'] = -1*speed
            else:
                y = 50
                stuff['velocity_y'] = 1*speed
    
        gift = gen_gift(self, center_x=x, center_y=y, **stuff)
        self.area.add_widget(gift)
        self.gifts.append(gift)
        
    
    def _update(self, dt=None, keys= KEYS):
   
        self.count += dt
        self.frames_count += 1
        random.shuffle(self.players)
        for o in itertools.chain(self.bullets,
                                 self.planets,
                                 self.portals,
                                 self.arrows):
            o.update()
       
        for p in itertools.chain(self.players, self.dead_players,
                                 self.gifts, self.drones, self.mines):
            p.update()
            
        if self.count > 3.0:
            self.label.text = "FPS: %.1f\n bullets: %d" % (self.frames_count / self.count,
                                                           len(self.bullets))
            self.count = self.frames_count = 0.0
            #if self.bullets:
                #b = self.bullets[0]
                #print(b.center, b.active, )
            
        if len(self.players+self.dead_players) < 2:
            s = self.manager.get_screen('game_over')
            s.set_winner(self.players[0].name if self.players else None)
            self.manager.current = 'game_over'
        
        teams_left = set(p.team for p in self.players if p.team)
        if len(teams_left) == 1:
            winner = 'Team %s' % (self.players[0].team)
            self.gameover(winner)
        
        if random.random() > 0.985:
            self.create_gift()
            
        #wall collisions
        
    def gameover(self, winner):
        s = self.manager.get_screen('game_over')
        s.set_winner(winner)
        self.manager.current = 'game_over'           


class ButtonPop(Popup):
    
    def __init__(self, **kw):
        self.value = kw.pop('value', 0)
        key = kw.pop('key', '')
        super(ButtonPop, self).__init__( **kw)
        self.title = 'Press a button to bind "%s"' % key
        
    def on_open(self):
        Clock.schedule_once(self._get_key,0.01)
        
    def _get_key(self, dt=None):
        keys = [k for k, v in  KEYS.items() if v]
        if keys: 
            self.value = keys[0]
            #print(self.value)
            return self.dismiss()
        
        Clock.schedule_once(self._get_key,0.01)
        
class SettingButtonItem(SettingItem):
    
    def __init__(self, **kw):
        super(SettingButtonItem, self).__init__(**kw)
        
        Clock.schedule_once(self._after, 1)
        
        
        
    def _after(self, dt=None):
        self.l = Label(text=str(self.value))
        self.add_widget(self.l)
        
    
    def on_release(self):
        pop = ButtonPop(value=self.value,
                        key=self.key,
                        on_dismiss=lambda a: self._set_val(pop))

        pop.open()
        
    def _set_val(self, pop):
        self.value = pop.value
        
    def on_value(self, instance, value):
        if hasattr(self, 'l'):
            self.l.text = str(self.value)
        return SettingItem.on_value(self, instance, value)
    
    
      
class ConfigScreen(Screen):
    
    s = ObjectProperty(None)
    
    player_keys = 'left right thrust fire special_defense special_attack'.split()
    
    def __init__(self, **kw):
        super(ConfigScreen, self).__init__(**kw)
        self.config = ConfigParser()
        self.config.read('config.ini')
        self._update_players()
        Clock.schedule_once(self._after_build, 1)
        
    def on_leave(self, *args):
        Screen.on_leave(self, *args)
        self._update_players()
        
    def _update_players(self):
        for i, p in enumerate(self.players, start=1):
            self._update_player(i, p) 
    
    def _update_player(self, i, p):
        keys = {}
        for key in self.player_keys:
            keys[key] = int(self.config.get('player%d'%i, key))
        p['keys'] = keys
    
    
    def _after_build(self, dt=None):    
        print(os.path.abspath('.'), os.path.isfile("config.json"))
        s = self.s
        s.register_type('button', SettingButtonItem)
        s.add_json_panel('stuff', self.config, 'config.json')
        for i in range(1, 6):
            player = 'player%d' % i
            j = player+'.json'
            
            with open(j, 'wb') as f:
                f.write(json.dumps(
                    [

                        {
                            "type": "button",
                            "title": a,
                            "desc": "key for applying '%s'"%a,
                            "section": player,
                            "key": a,
                        } for  a in self.player_keys
                        
                    ], indent=4
                    
                    ).encode(encoding='utf_8'))
      
            s.add_json_panel(player, self.config, j)
    
    def save(self):
        self.config.write()
        self.manager.current = 'menu'
    
    players = [ {'name': 'Player1', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (50, 50),
                   
                   'r': 1.0, 'g': 1.0, 'b': 0.75,
                   
                   'rotation': 45 
                   },
                {'name': 'Player2', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (50, 200),
                  
                   'r': 1.0, 'g': 0.5, 'b': 0.75,
                   'rotation': 45 
                   },
                {'name': 'Player3', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (250, 50),
                  
                   'r': 0.5, 'g': 0.2, 'b': 0.75,
                   'rotation': 45 
                   },
               
                {'name': 'Player4', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (350, 50),
                  
                   'r': 0.5, 'g': 0.5, 'b': 0.98,
                   'rotation': 45 
                   },
                {'name': 'Player5', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (450, 50),
                  
                   'r': 1.0, 'g': 0.1, 'b': 0.99,
                   'rotation': 45 
                   },
                {'name': 'Player6', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (550, 50),
                  
                   'r': 0.35, 'g': 0.99, 'b': 0.99,
                   'rotation': 45 
                   },
               ]
    for p in players:
        p['size_hint'] = (0.02, 0.02)
               
               
               
class Menu(Screen):
    
    def __init__(self, **kw):
        super(Menu, self).__init__(**kw)


class GameSetup(Screen):
    
    bling = StringProperty(' ')
    level = NumericProperty(1)
    
    team2name = {0: "",
                 1: "N00Bly",
                 2: "Cheesy",}
    
    def __init__(self, **kw):
        self.players = [{'play': False,
                         'team': 0}
                        for _ in range(6)]
        super(GameSetup, self).__init__(**kw)
        
        self.level = 3
        
    def level_click(self):
        self.level += 1
        good = os.path.exists("./levels/%02d.json" % self.level)
        if not good:
            self.level = 1
        
    def on_enter(self, *args):
        Screen.on_enter(self, *args)
        self.event = Clock.schedule_interval(self._tick, 0.02)
    
    def get_player_text(self, num):
        
        p = self.players[num-1]
        if p['play']:
            s = 'Player%d' % num
            team = p['team']
            if team:
                s += " Team %s" % self.team2name[team]
            return s
        return " "
    
    def go(self):
        teams = {p['team'] for p in self.players if p['play']}
        print(teams)
        if 0 in teams and len(teams)> 1:
            return
        if 0 not in teams and len(teams)!=2:
            
            return
        if sum(p['play'] for p in self.players) < 2:
            return
        with open('levels/%02d.json' % self.level) as f:
            level = json.load(f)
        for p in self.players:
            p['team_name'] = self.team2name[p['team']]
        self.manager.get_screen('game'
                ).setup(level=level,
                       players=list(self.players))
        self.manager.current = 'game'
    
    def on_leave(self, *args):
        Screen.on_leave(self, *args)
        self.event.cancel()

    
    def _tick(self, dt=None):
        fire2player = [(p['keys']['fire'], self.players[i-1]) 
                       for i, p in enumerate(ConfigScreen.players, start=1)]
                
        for k, p in fire2player:
            if KEYS[k]:
                KEYS[k] = 0
                if not p['play']:
                    p['play'] = True
                else:
                    if p['team'] == 2:
                        p['team'] = 0
                        p['play'] = False
                    else:
                        p['team'] += 1
                    
                    
       
        self.bling = self.bling * 2 if len(self.bling)<10 else "b"
        
        


class GameOver(Screen):
    
    def __init__(self, **kw):
        super(GameOver, self).__init__(**kw)

    def set_winner(self, winner=None):
        
        self.winner = "%s Wins!" % winner if winner else 'TIE :('
        
Config.set('graphics', 'fullscreen', 1)

class SkyBombersApp(App):
    
    
    
    def on_start(self):
        return
        import cProfile
        self.profile = cProfile.Profile()
        self.profile.enable()

    def on_stop(self):
        return
        self.profile.disable()
        self.profile.dump_stats('myapp.profile')
    
    def build(self, KEYS=KEYS):
        def on_key_down(window, keycode, *rest):
            KEYS[keycode] = True
        def on_key_up(window, keycode, *rest):
            KEYS[keycode] = False
        def on_joy_axis(win, stickid, axisid, value):
            axes = (stickid+1)*1000 + axisid*10
            if value:
                if value > 0:
                    KEYS[axes] = 1
                else:
                    KEYS[axes+1] = 1
            else:
                KEYS[axes] = KEYS[axes+1] = 0
        def on_joy_button_down(_, joynum, btn):
            
            k = (joynum+1) * 1000 + btn + 50
      
            KEYS[k] = 1
        def on_joy_button_up(_, joynum, btn):
            k = (joynum+1) * 1000 + btn + 50
            KEYS[k] = 0
        Window.bind(on_key_down=on_key_down, on_key_up=on_key_up)
        Window.bind(on_joy_axis=on_joy_axis)
        Window.bind(on_joy_button_down=on_joy_button_down)
        Window.bind(on_joy_button_up=on_joy_button_up)
        GlobalStuff.init()
        
        config= ConfigScreen(name='config')
        sm.add_widget(config)
        game = Game(name='game')
        sm.add_widget(game)
        
        sm.add_widget(GameSetup(name='game_setup'))
        sm.add_widget(GameOver(name='game_over'))
        sm.add_widget(Menu(name='menu'))
        sm.current = 'menu'
        for i in range(6):
            Clock.schedule_once(lambda dt: GlobalStuff.init(), i)
       
        return sm

if __name__ == '__main__':
    #Window.size = screensize
    Window.maxfps = 36
    #Config.fullscreen = 1
    #Config.set('graphics', 'fullscreen', 'auto')
    Window.fullscreen = 'auto'
    Clock.max_iteration *= 3
    SkyBombersApp().run()