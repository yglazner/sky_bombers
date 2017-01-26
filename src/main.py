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
from math import radians
import random
from kivy.config import Config, ConfigParser
import kivyoav.autosized_label
import os
from kivy.uix.settings import SettingItem
from kivyoav.autosized_label import AutoSizedLabel
from kivy.uix.popup import Popup
from kivy.core.audio import SoundLoader
import json

sm = ScreenManager()

KEYS = defaultdict(lambda: None)


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
       
        
        
    def update(self, plats=[],):
        thrust = self.thrust
        y_t = math.sin(radians(self.rotation)) * thrust
        x_t = math.cos(radians(self.rotation)) * thrust
        
        self.velocity_x += x_t
        self.velocity_y += y_t
        
        self.y += self.velocity_y
        self.x += self.velocity_x
        
        self.velocity_x *= 0.998
        self.velocity_y *= 0.998
        
        

    def distance(self, other):
        a = (self.center_x - other.center_x) ** 2
        b = (self.center_y - other.center_y)  ** 2
        return math.sqrt(a+b)
    
    
    def collide(self, other, area=0):
        d = self.distance(other)
        if d < (self.radius+other.radius+area):
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
    
    bullet_sounds = [SoundLoader.load('Music/shots/gunshot-00.mp3')
                     for _ in range(50)
                ]
    random.shuffle(bullet_sounds)
    
    for sound in bullet_sounds:
        sound.volume = 0.5
        
    next_bullet_sound = itertools.cycle(bullet_sounds)
        
    def __init__(self, game, owner, direction, **kw):
        super(Bullet, self).__init__(game, **kw)     
        self.rotation = direction#owner.rotation   
        self.velocity_x = owner.velocity_x + math.cos(radians(self.rotation)) * 4
        self.velocity_y = owner.velocity_y +  math.sin(radians(self.rotation)) * 4
        
        self.active = True
        self.first = 1
        self.owner = owner
        
        self.center = -200, -200
        self.blow_rate = 2.0
        self.max_counter = 100
        self.counter = 0
        
    def hit_by(self, other):
        self.active = False
        self.counter = 40
        
        
    def update(self):
        if self.first:
            self.center = self.owner.center
            self.first=0
            next(self.next_bullet_sound).play()
        self.counter +=1
        bingo = self.game.check_player_collision(self, [self.owner])
        
        if bingo and self.active:
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

class Player(Sprite):    
    lives = NumericProperty(5)
    hit_sounds = [SoundLoader.load('Music/shots/hit.mp3'),SoundLoader.load('Music/shots/hit.mp3'),SoundLoader.load('Music/shots/hit.mp3'),
                  SoundLoader.load('Music/shots/hit.mp3'),SoundLoader.load('Music/shots/hit.mp3'),
                  SoundLoader.load('Music/shots/ouch.mp3'),SoundLoader.load('Music/shots/ouch.mp3'),SoundLoader.load('Music/shots/ouch.mp3'),
                  SoundLoader.load('Music/shots/ouch.mp3'),SoundLoader.load('Music/shots/ouch.mp3')]
                     
    dead_sounds = [SoundLoader.load('Music/shots/dead.mp3')
                     for _ in range(5)]
    random.shuffle(hit_sounds)
    next_dead_sound = itertools.cycle(dead_sounds)
    next_hit_sound = itertools.cycle(hit_sounds)
    def __init__(self, game, name, team, keys, **kw):
        super(Player, self).__init__(game, **kw)
        self.velocity_x = 0.0 * math.cos(radians(self.rotation))
        self.velocity_y = 0.0 * math.sin(radians(self.rotation))
        self.reload = 0
        self.reload_time = 20
        self.keys = keys
        self.name = name
        self.team = team
        self.speed = 0.2
        self.bullets = 1
        

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
            

    def update(self,  user_pressed=KEYS):
        
        
        if self.lives <= 0 or self.check_wall_collision():
            self.lives = 0
            self.counter = 20
            self.game.mark_dead(self)
            self.update = self.play_dead
        self.reload -= 1
        keys = self.keys
        self.thrust = 0
        if user_pressed[keys['left']]:
            self.rotation += 5
        elif user_pressed[keys['right']]:    
            self.rotation -= 5
        if user_pressed[keys['thrust']]:
            self.thrust = self.speed
        if user_pressed[keys['fire']]:
            self.fire()
        
        super(Player, self).update()
        
    def play_dead(self):
        self.counter -= 1
        if self.counter < 0:
            self.game.remove_player(self)
            self.game = None
            return
        self.size_hint_x * 1.05
        self.a *= 0.9
        super(Player, self).update()
    
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
        d  = self.rotation
        
        for i in range(self.bullets):
            bullet = Bullet(self.game, self, d + (i*8*((i%2) or -1)))
            self.game.add_bullet(bullet)

class BaseGift(Sprite):
    
    src = StringProperty("")
    
    def __init__(self, game, **kwargs):
        super(BaseGift, self).__init__(game, **kwargs)
        self.src = self.SOURCE
        
    def update(self):
        p = self.game.check_player_collision(self)
        if p:
            self.apply_gift(p)
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
        

gift_types = [SpeedGift, LivesGift, ExtraShotGift, ]

def gen_gift(*args, **kw):
    return random.choice(gift_types)(*args, **kw)
    

class Planet(Sprite):
    
    color = ListProperty([1.0, 0.0, 0.0, 0.5])
    def __init__(self, game, color, size_hint, pos_hint):
        self.color = color
        self.damage = 99
        super(Planet, self).__init__(game, size_hint=size_hint, pos_hint=pos_hint)
        
    def update(self):
        area = self.radius * 3
        for obj in itertools.chain(self.game.players, self.game.bullets):
            if obj.collide(self, area):
                if obj.collide(self):
                    obj.hit_by(self)
                else:
                    self._attract(obj)
                    
        
    def _attract(self, obj):
        diffx = obj.center_x - self.center_x
        diffy = obj.center_y - self.center_y
        speed = 0.20
        ratio = float(abs(diffx)) / (abs(diffy)+abs(diffx))
        speedx = speed * ratio
        speedy = speed * (1-ratio)
        obj.velocity_x -= speedx if diffx > 0 else -speedx
        obj.velocity_y -= speedy if diffy > 0 else -speedy
        

class Game(Screen):
    area = ObjectProperty(None)
    
    
    
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
        
    
        
    def on_enter(self, *args):
        Screen.on_enter(self, *args)
        for w in list(self.area.children):
            self.area.remove_widget(w)
        self.players = []
        self.planets = []
        self.gifts = []
        self.dead_players = []
        self.bullets = []
        for p, s in zip(ConfigScreen.players, self.players_setup):
            if not s['play']: continue
            p = Player(self, team=s['team_name'], **p)
            self.players.append(p)
            self.area.add_widget(p)
            
        for planet in self.level['planets']:
            p = Planet(self, 
                       color=planet['color'],
                       size_hint=planet['size'], 
                       pos_hint={'center_x': planet['x'],
                                 'center_y': planet['y']})
            self.area.add_widget(p)
            self.planets.append(p)
            
        
        self.background_sound.loop = True
        self.background_sound.volume = 0.5
        self.background_sound.play()
        self.label = Label(text="FPS: ?", pos=(200,200)) 
        self.area.add_widget(self.label)
        self._loop = Clock.schedule_interval(self._update, 1.0/25)
        self.count = 0.0
        self.frames_count = 1
        
    def on_leave(self, *args):
        Screen.on_leave(self, *args)
        self._loop.cancel()
        self.background_sound.stop()

    def add_bullet(self, bullet):
        self.bullets.append(bullet)
        self.area.add_widget(bullet)
    
    def remove_bullet(self, bullet):
        if bullet in self.bullets:
            self.bullets.remove(bullet)
            self.area.remove_widget(bullet)
            
    def mark_dead(self, player):
        self.players.remove(player)
        self.dead_players.append(player)
        
    def remove_player(self, player):
        self.dead_players.remove(player)
        self.remove_widget(player)

    def check_player_collision(self, obj, filter=[]):
        
        for p in self.players:
            if p.collide(obj):
                if p not in filter:
                    return p
                
    
                
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
                x = 0
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
                y = 0
                stuff['velocity_y'] = 1*speed
    
        gift = gen_gift(self, center_x=x, center_y=y, **stuff)
        self.area.add_widget(gift)
        self.gifts.append(gift)
        
    
    def _update(self, dt=None, keys= KEYS):
   
        self.count += dt
        self.frames_count += 1
        random.shuffle(self.players)
        for b in self.bullets:
            b.update()
        for p in self.planets:
            p.update()
        
        for p in itertools.chain(self.players, self.dead_players, self.gifts):
            p.update()
            
        if self.count > 1.0:
            self.label.text = "FPS: %.1f" % (self.frames_count / self.count)
            self.count = self.frames_count = 0.0
            
        if len(self.players+self.dead_players) < 2:
            s = self.manager.get_screen('game_over')
            s.set_winner(self.players[0].name if self.players else None)
            self.manager.current = 'game_over'
        
        teams_left = set(p.team for p in self.players if p.team)
        if len(teams_left) == 1:
            winner = 'Team %s' % (self.players[0].team)
            self.gameover(winner)
        
        if random.random() > 0.995:
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
            print(self.value)
            return self.dismiss()
        
        Clock.schedule_once(self._get_key,0.01)
        
class SettingButtonItem(SettingItem):
    
    def __init__(self, **kw):
        super(SettingButtonItem, self).__init__(**kw)
        
        Clock.schedule_once(self._after, 1)
        
        
        
    def _after(self, dt=None):
        self.l = Label(text=str(self.value))
        self.add_widget(self.l)
        print('cool', self.value)
    
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
    
    player_keys = 'left right thrust fire special'.split()
    
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
        
        self.level = 1
        
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
        pass
        #import cProfile
        #self.profile = cProfile.Profile()
        #self.profile.enable()

    def on_stop(self):
        pass
        #self.profile.disable()
        #self.profile.dump_stats('myapp.profile')
    
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
        Clock.schedule_once(lambda dt: GlobalStuff.init(), 5)
        return sm

if __name__ == '__main__':
    #Window.size = screensize
    Window.maxfps = 36
    #Config.fullscreen = 1
    #Config.set('graphics', 'fullscreen', 'auto')
    Window.fullscreen = 'auto'
    SkyBombersApp().run()