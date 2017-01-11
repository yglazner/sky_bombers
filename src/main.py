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
import json

sm = ScreenManager()

KEYS = defaultdict(lambda: None)


class Sprite(Scatter):
   
   
   
    source = StringProperty('')
    radius = NumericProperty(0.0)
    
    def __init__(self, game, **kwargs):
        self.game = game
        super(Sprite, self).__init__( **kwargs )
        self.velocity = 0.0
        
        
    def update(self, plats=[],):
        
        self.y += self.velocity * math.sin(radians(self.rotation))
        self.x += self.velocity * math.cos(radians(self.rotation))
        
        

    def distance(self, other):
        a = (self.center_x - other.center_x) ** 2
        b = (self.center_y - other.center_y)  ** 2
        return math.sqrt(a+b)
    
    
    def collide(self, other):
        d = self.distance(other)
        if d < (self.radius+other.radius):
            return 1
        
            

class GlobalStuff(object):
    
    
    @classmethod
    def init(cls):
        
        cls.center_x = Window.width / 2
        cls.center_y = Window.height / 2
        cls.size = cls.width, cls.height = Window.width, Window.height

    
class Bullet(Sprite):
    
    blow = NumericProperty(1.0)
    damage = NumericProperty(1)
    def __init__(self, game, owner, **kw):
        super(Bullet, self).__init__(game, **kw)        
        self.velocity = owner.velocity + 3.0
        
        self.active = True
        self.first = 1
        self.owner = owner
        
        self.center = -200, -200
        self.rotation = owner.rotation
        
        self.counter = 0
        
        
    def update(self):
        if self.first:
            self.center = self.owner.center
            self.first=0
        self.counter +=1
        bingo = self.game.check_player_collision(self, [self.owner])
        if bingo and self.active:
            self.active = False
            bingo.hit_by(self)
            self.counter = 25
        if self.counter > 50:
            self.game.remove_bullet(self)
            self.active = False
        if not self.active:
            self.velocity *= 0.95
            self.blow *= 1.05
            
        super(Bullet, self).update()

class Player(Sprite):
    
    lives = NumericProperty(5)
    
    def __init__(self, game, name, keys, **kw):
        super(Player, self).__init__(game, **kw)
        self.velocity = 5.0
        self.reload = 0
        self.keys = keys
        self.name = name
        
    def update(self,  keys=KEYS):
        if self.lives <= 0:
            self.counter = 20
            self.game.mark_dead(self)
            self.update = self.play_dead
        self.reload -= 1

        if keys[self.keys['left']]:
            self.rotation += 5
        elif keys[self.keys['right']]:    
            self.rotation -= 5
        if keys[self.keys['fire']]:
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
    
    def fire(self):
        if self.reload > 0:
            return
        self.reload = 10
        bullet = Bullet(self.game, self)
        self.game.add_bullet(bullet)
        
class Game(Screen):
    area = ObjectProperty(None)
    
    def __init__(self, **kw):
        Screen.__init__(self, **kw)
        self.player_nums = []
        
    def setup(self, players):
        self.player_nums = players
        
        
    def on_enter(self, *args):
        Screen.on_enter(self, *args)
        for w in list(self.area.children):
            self.area.remove_widget(w)
        self.players = []
        self.dead_players = []
        self.bullets = []
        for i, p in enumerate(ConfigScreen.players, start=1):
            if i not in self.player_nums: continue
            p = Player(self, **p)
            self.players.append(p)
            self.area.add_widget(p)
            
        self.label = Label(text="FPS: ?", pos=(200,200)) 
        self.area.add_widget(self.label)
        self._loop = Clock.schedule_interval(self._update, 1.0/36)
        self.count = 0.0
        self.frames_count = 1
        
    def on_leave(self, *args):
        Screen.on_leave(self, *args)
        self._loop.cancel()

    def add_bullet(self, bullet):
        self.bullets.append(bullet)
        self.add_widget(bullet)
    
    def remove_bullet(self, bullet):
        if bullet in self.bullets:
            self.bullets.remove(bullet)
            self.remove_widget(bullet)
            
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
    
    def _update(self, dt=None, keys= KEYS):
        self.count += dt
        self.frames_count += 1
        random.shuffle(self.players)
        for b in self.bullets:
            b.update()
        
        for p in itertools.chain(self.players, self.dead_players):
            p.update()
            
        if self.count > 1.0:
            self.label.text = "FPS: %.1f" % (self.frames_count / self.count)
            self.count = self.frames_count = 0.0
            
        if len(self.players+self.dead_players) < 2:
            s = self.manager.get_screen('game_over')
            s.set_winner(self.players[0].name if self.players else None)
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
    
    player_keys = 'left right power fire special'.split()
    
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
                   'size_hint': (0.05, 0.05),
                   'rotation': 45 
                   },
                {'name': 'Player2', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (-50, 50),
                   'size_hint': (0.05, 0.05),
                   'rotation': 45 
                   },
                {'name': 'Player3', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (250, 50),
                   'size_hint': (0.05, 0.05),
                   'rotation': 45 
                   },
               
                {'name': 'Player4', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (350, 50),
                   'size_hint': (0.05, 0.05),
                   'rotation': 45 
                   },
                {'name': 'Player5', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (450, 50),
                   'size_hint': (0.05, 0.05),
                   'rotation': 45 
                   },
                {'name': 'Player6', 
                   'source': 'imgs/DUCK.GIF', #'weapon': 'gun',
                   'pos': (550, 50),
                   'size_hint': (0.05, 0.05),
                   'rotation': 45 
                   },
               ]
               
               
               
               
    
    
        
            

class Menu(Screen):
    
    def __init__(self, **kw):
        super(Menu, self).__init__(**kw)


class GameSetup(Screen):
    
    players = ListProperty([])
    
    def __init__(self, **kw):
        super(GameSetup, self).__init__(**kw)
        
    def on_enter(self, *args):
        Screen.on_enter(self, *args)
        self.event = Clock.schedule_interval(self._tick, 0.02)
    
    def go(self):
        self.manager.get_screen('game').setup(players=list(self.players))
        self.manager.current = 'game'
    
    def on_leave(self, *args):
        Screen.on_leave(self, *args)
        self.event.cancel()
        self.players = []
    
    def _tick(self, dt=None):
        fire2player = [(p['keys']['fire'], i) for i, p in enumerate(ConfigScreen.players, start=1)]
        
        players = list(self.players)
        for k, i in fire2player:
            if KEYS[k] and i not in players:
                players.append(i)
        self.players = players    
        
        


class GameOver(Screen):
    
    def __init__(self, **kw):
        super(GameOver, self).__init__(**kw)

    def set_winner(self, winner=None):
        
        self.winner = "%s Wins!" % winner if winner else 'TIE :('
        
    

class SkyBombersApp(App):
    def on_start(self):
        import cProfile
        self.profile = cProfile.Profile()
        self.profile.enable()

    def on_stop(self):
        self.profile.disable()
        self.profile.dump_stats('myapp.profile')
    
    def build(self):
        def on_key_down(window, keycode, *rest):
            KEYS[keycode] = True
        def on_key_up(window, keycode, *rest):
            KEYS[keycode] = False
        Window.bind(on_key_down=on_key_down, on_key_up=on_key_up)
        GlobalStuff.init()
        
        config= ConfigScreen(name='config')
        sm.add_widget(config)
        game = Game(name='game')
        sm.add_widget(game)
        
        sm.add_widget(GameSetup(name='game_setup'))
        sm.add_widget(GameOver(name='game_over'))
        sm.add_widget(Menu(name='menu'))
        sm.current = 'menu'
        return sm

if __name__ == '__main__':
    SkyBombersApp().run()