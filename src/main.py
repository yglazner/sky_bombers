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

Config.full_screen = 1

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
    def __init__(self, game, owner, **kw):
        super(Bullet, self).__init__(game, **kw)     
        self.rotation = owner.rotation   
        self.velocity_x = owner.velocity_x + math.cos(radians(self.rotation)) * 8
        self.velocity_y = owner.velocity_y +  math.sin(radians(self.rotation)) * 8
        
        self.active = True
        self.first = 1
        self.owner = owner
        
        self.center = -200, -200
        self.blow_rate = 2.0
        
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
            self.velocity_x *= 0.75
            self.velocity_y *= 0.75
            self.blow *= self.blow_rate
            self.blow_rate *= 0.90
            
        super(Bullet, self).update()

class Player(Sprite):
    
    lives = NumericProperty(5)
    
    def __init__(self, game, name, keys, **kw):
        super(Player, self).__init__(game, **kw)
        self.velocity_x = 1.0 * math.cos(radians(self.rotation))
        self.velocity_y = 1.0 * math.sin(radians(self.rotation))
        self.reload = 0
        self.keys = keys
        self.name = name
        self.speed = 0.2
        

    def check_wall_collision(self):
        r = self.radius
        print(r, self.size, self.center)
        x, y = self.center
        if x - r < 0:
            return True
        if x + r > GlobalStuff.right:
            return True
        if y + r > GlobalStuff.top:
            return True
        if y-r < 0:
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
    
    def fire(self):
        if self.reload > 0:
            return
        self.reload = 10
        bullet = Bullet(self.game, self)
        self.game.add_bullet(bullet)

class BaseGift(Sprite):
    
    def __init__(self, game, **kwargs):
        super(BaseGift, self).__init__(game, **kwargs)
    
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
    
    def apply_gift(self, player):
        
        player.speed *= 1.3
        print("player %s thrust is %d" % (player.name, player.thrust))

gift_types = [SpeedGift, ]

def gen_gift(*args, **kw):
    return random.choice(gift_types)(*args, **kw)
    

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
        self.gifts = []
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
        if p in ['left', 'right']:
            y = (GlobalStuff.top - 20) * random.random() + 10
            if p == 'left':
                x = 0
                stuff['velocity_x'] = 5
            else:
                x = GlobalStuff.right
                stuff['velocity_x'] = -5
        else:
            x = (GlobalStuff.right - 20) * random.random() + 10
            if p == 'top':
                y = GlobalStuff.top
                stuff['velocity_y'] = -5
            else:
                y = 0
                stuff['velocity_y'] = 5
    
        gift = gen_gift(self, center_x=x, center_y=y, **stuff)
        self.area.add_widget(gift)
        self.gifts.append(gift)
        
    
    def _update(self, dt=None, keys= KEYS):
        self.count += dt
        self.frames_count += 1
        random.shuffle(self.players)
        for b in self.bullets:
            b.update()
        
        for p in itertools.chain(self.players, self.dead_players, self.gifts):
            p.update()
            
        if self.count > 1.0:
            self.label.text = "FPS: %.1f" % (self.frames_count / self.count)
            self.count = self.frames_count = 0.0
            
        if len(self.players+self.dead_players) < 2:
            s = self.manager.get_screen('game_over')
            s.set_winner(self.players[0].name if self.players else None)
            self.manager.current = 'game_over'
        
        if random.random() > 0.995:
            self.create_gift()
            
        #wall collisions
        
                


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
        
Config.set('graphics', 'fullscreen', 1)

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
        Window.screen = 1
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