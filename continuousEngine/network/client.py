# usage (see initial_script):
# python client.py game [game_id [team [username [ip]]]]

import continuousEngine
import pygame
import threading
import socket
import json
import sys
import traceback
import asyncio
import random, string
import functools

port = 9974

class NetworkGame:
    """
    represents the client side of a game connected to a server.
    This is a wrapper for a continuousEngine.Game object
    the continuousEngine.Game object must define attempt_move, load_state
    The client can be in two states: live or offline.
    In offline mode, the game works exactly as if you were not connected
    In live mode, loading state is disabled, and the game tracks the server's state. 
    Attempting to make a move results in it being sent to the server; no change is made to your local gamestate.
    
    """
    def __init__(self,game):
        self.game = game
        self.server = None
        self.live_mode = False
        self.server_state = None
        self.server_history = []
        self.players = {t:[] for t in game.teams+['spectator']}
        self.id = ''
        self.user = ''

        def f(e):
            if e.action=="move":
                self.server_history.append(self.server_state)
                self.server_state = e.state
                self.server_timeinfo = e.timeinfo
                self.update_to_server_state()
            elif e.action=="game_info":
                self.players = {t:[] for t in self.game.teams+['spectator']}
                for pl in e.players:
                    self.players[pl["team"]].append(pl["user"])
            elif e.action=="history":
                self.server_history = e.history
                self.update_to_server_state()
                self.game.initialState = (self.server_history+[self.server_state])[0]
        self.game.handlers[pygame.USEREVENT] = f

        def f(_):
            self.live_mode = not self.live_mode
            self.update_to_server_state()
        self.game.keyPress[self.game.keys.toggleLive] = f
        
        if game.allow_skip:
            pass
        else:
            # exit live mode when skipping
            self.game.keyPress[self.game.keys.skipTurn] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.skipTurn])

        # viewing history exits live mode
        self.game.keyPress[self.game.keys.undo] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.undo])
        self.game.keyPress[self.game.keys.redo] = (lambda f: lambda e: (f(e), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.redo])
        self.game.keyPress[self.game.keys.resetGame] = (lambda f: lambda e: (f(e), setattr(self.game, 'future', [self.server_state]+self.server_history[:0:-1]), setattr(self, 'live_mode', False)))(self.game.keyPress[self.game.keys.resetGame])


        self.f = self.game.attemptMove
        self.game.attemptMove = self.attemptMove

        continuousEngine.ScreenBorder(game, 10**10, (100,100,100), 7).GETvisible = lambda _: not self.live_mode

        continuousEngine.GameInfo(game,
            lambda _: [
                ('id', self.id),
                ('turn', self.game.turn),
                ('you', self.user),
                ('live', self.live_mode),
                (None, None),
                *((t, ', '.join(self.players[t])) for t in game.teams+['spectator'])
            ]
        )

    async def join(self,server,i,team,user):
        """
        server is a tcp socket that you've already connected to that is a continuous games server.
        server is actually a tuple (reader, writer) returned from asyncio.open_connection
        """
        d = {
            "action":"join",
            "user":user,
            "id":i,
            "team":team
            }
        self.live_mode = True
        self.server=server
        self.id = i
        self.user = user
        send(server,d)
        print("joined game {} as user {} on team {}".format(i, user, team))
        print("started server listening thread",flush=True)
        a = asyncio.get_running_loop().run_in_executor(None, self.game.run)
        await asyncio.gather(self.server_listener(), a)
        #threading.Thread(target=(lambda :print("hi",flush=True))).start()
#    def handle(self, event):
#        if event.type in self.game.handlers:
#            with self.lock:
#                self.game.handlers[event.type](event)

    def update_to_server_state(self):
        if not self.server_state:
            return
        if self.live_mode:
            self.game.load_state(self.server_state)
            self.game.history = self.server_history.copy()
            self.game.future = []
            self.game.time_left, self.game.turn_started = self.server_timeinfo
            self.game.prep_turn()
            
    async def server_listener(self):
        while True:
            try:
                print("listening",flush=True)
                s = await receive(self.server)
                print("received", s["action"], flush=True)
                pygame.event.post(pygame.event.Event(pygame.USEREVENT,**s))
            except Exception as e:
                print(traceback.format_exc(),flush=True)
                sys.exit()
                


    def attemptMove(self, m):
        """
        in offline mode, simply calls attempt_move
        if connected to a game, it sends the move to the server.
        """
        d = {"action":"move", "move":m}
        if self.live_mode:
            print("sending move to server")
            print(d,flush=True)
            try:
                send(self.server,d)
            except:
                print(traceback.format_exc(),flush=True)
        else:
            self.f(m)

def send(server, m):
    #server.sendall((json.dumps(m)+"\n").encode())
    #server.makefile(mode="w").write((json.dumps(m)+"\n"))
    server[1].write((json.dumps(m)+"\n").encode())
    #asyncio.get_event_loop().create_task(server[1].drain())
    #asyncio.create_task(server[1].drain())
    #await server[1].drain()

async def receive(server):
    return json.loads((await server[0].readline()).strip())
    #return json.loads(server.makefile(mode="r").readline().strip())

async def initial_script(ip, game, game_id, team, time_control, username, new, args):
    kwargs = {'timectrl': time_control}

    s = await asyncio.open_connection(host=ip, port=port, limit=2**20)

    print("connected to {}".format(ip))

    send(s, {"action":"list"})
    ids = await receive(s)
    print("listing ids")
    print(ids,flush=True)

    async def attempt_joining(id, t):
        send(s, {"action":"gameargs", "id":id})
        gargs, gkwargs = await receive(s)
        await NetworkGame(await asyncio.get_running_loop().run_in_executor(None, functools.partial(continuousEngine.game_class(game), *gargs, **gkwargs))).join(s, id, t, username)

    if game_id:
        if new and game_id in ids:
            print('{} already exists'.format(game_id), flush=True)
            sys.exit()

        while game_id not in ids:
            send(s, {"action":"create", "name":game, "id":game_id, "args":args, "kwargs":kwargs})
            send(s, {"action":"list"})
            ids = await receive(s)

        if ids[game_id]["game_type"] != game:
            print('{} is a game of {}, not {}'.format(game_id, ids[game_id]["game_type"], game), flush=True)
            sys.exit()

        if team:
            if team not in ids[game_id]["open teams"]+["spectator"]:
                print("team {} doesn't exist or is already taken in {}".format(team, game_id), flush=True)
                sys.exit()
            await attempt_joining(game_id, team)

        else:
            await attempt_joining(game_id, (ids[game_id]["open teams"]+["spectator"])[0])

    else:
        joined = False
        if not new:
            if team:
                for i in ids:
                    if ids[i]["players"] and ids[i]["game_type"] == game and team in ids[i]["open teams"]+["spectator"]:
                        await attempt_joining(i, team)
                        joined = True
            else:
                for i in ids:
                    if ids[i]["players"] and ids[i]["game_type"] == game and ids[i]["open teams"]:
                        await attempt_joining(i, ids[i]["open teams"][0])
                        joined = True
        if not joined:
            id = None
            while id==None or id in ids:
                id = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
            send(s, {"action":"create", "name":game, "id":id, "args":args, "kwargs":kwargs})
            send(s, {"action":"list"})
            ids = await receive(s)
            if team:
                if team not in ids[id]["open teams"]+["spectator"]:
                    print("team {} doesn't exist or is already taken in {}".format(team, id), flush=True)
                    sys.exit()
                await attempt_joining(id, team)
            else:
                await attempt_joining(id, (ids[id]["open teams"])[0])

