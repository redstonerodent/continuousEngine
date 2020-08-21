import continuousEngine
import pygame
import threading
import socket
import json
import chess
import sys
import traceback
import asyncio
class NetworkGame:
    """
    represents the client side of a game connected to a server.
    This is a wrapper for a continuousEngine.Game object
    the continuousEngine.Game object must defined attempt_move, load_state
    The client can be in two states: live or offline.
    In offline mode, the game works exactly as if you were not connected
    In live mode, loading state is disabled, and the game tracks the server's state. 
    Attempting to make a move results in it being sent to the server; no change is made to your local gamestate.
    
    """
    def __init__(self,game):
        self.game = game
        self.server = None
        self.live_mode = 0
        self.server_state = {}
        #self.lock = threading.RLock()
        self.game.keyPress[pygame.K_n] = lambda e:(setattr(self,"live_mode",1-self.live_mode), self.update_to_server_state() if self.live_mode else 0) if self.server!=None else 0
        self.game.handlers[pygame.USEREVENT] = lambda e:self.game.load_state(e.state)
        #self.game.handle = self.handle
        self.f = self.game.attemptMove
        self.game.attemptMove = self.attemptMove

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
        self.live_mode = 1
        self.server=server
        send(server,d)
        print("joined game {} as user {} on team {}".format(i, user, team))
        print("started server listening thread",flush=True)
        a = asyncio.get_running_loop().run_in_executor(None, self.game.run)
        await asyncio.gather(self.server_listener(), a)
        #threading.Thread(target=(lambda :print("hi",flush=True))).start()
    async def run():
        await self.game.run()

#    def handle(self, event):
#        if event.type in self.game.handlers:
#            with self.lock:
#                self.game.handlers[event.type](event)

    def update_to_server_state(self):
        if not self.server_state:
            return
        #with self.lock:
            #self.game.load_state(self.server_state)
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, state=self.server_state))
            
    async def server_listener(self):
        while True:
            try:
                print("listening for gamestate",flush=True)
                s = await recieve(self.server)
                if not s or s["action"]!="move":
                    print(str(s),flush = True)
                else:
                    print("recieved gamestate",flush=True)
                    self.server_state = s["state"]
                    if self.live_mode:
                        self.update_to_server_state()
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
    #asyncio.create_task(server[1].drain())
    #await server[1].drain()
async def recieve(server):
    return json.loads((await server[0].readline()).strip())
    #return json.loads(server.makefile(mode="r").readline().strip())

async def initial_script():
    ip = "localhost" if len(sys.argv)==1 else sys.argv[1]
    port = 9999
    #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #s.connect((ip,port))
    s = await asyncio.open_connection(host=ip, port=port)
    print("connected to {}".format(ip))
    joined=False
    while not joined:
        send(s,{"action":"list"})
        games = await recieve(s)
        print("listing games")
        print(games,flush=True)
        for i in games:
            available_colors = [x for x in ["white","black"] if x not in [p["team"] for p in games[i]["players"]]]
            if available_colors:
                g = await asyncio.get_running_loop().run_in_executor(None, chess.Chess)
                await NetworkGame(g.game).join(s,i,available_colors[0],"brunnerj")
                #threading.Thread(target = g.game.run).start()
                joined = True
                
        if not joined:
            d = {
                "action":"create",
                "name":"chess"
            }
            send(s,d)

asyncio.run(initial_script())

            
        


