"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import _thread
import sys

"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""
Game = namedtuple("Game", ["p1_sock", "p2_sock","p1_cards", "p2_cards", "p1_score", "p2_score"])

class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2

def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return those. If EOF is found
    before numbytes have been received, be sure to account for that here or in
    the caller.
    """
    data = sock.recv(numbytes)
    while len(data) < numbytes:
        nbytes = sock.recv(numbytes - len(data))
        if not nbytes: break
        data += nbytes
    
    return data
    

def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    pass

def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """
    if card1 % 13 < card2 % 13: return -1
    elif card1 % 13 == card2 % 13: return 0
    else: return 1

def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    deck = list(range(52))
    random.shuffle(deck)
    return deck[:26], deck[26:]

class WarProtocol(asyncio.Protocol):
    connections = 0
    p1_sock = None
    p2_sock = None
    GAME = None
    p1_curr_card = None
    p2_curr_card = None
    

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        WarProtocol.connections += 1
        # save p1 socket in game
        if WarProtocol.connections == 1:
            WarProtocol.GAME = Game(transport, None, [], [], 0, 0)
        elif WarProtocol.connections == 2:
            WarProtocol.GAME = Game(WarProtocol.GAME.p1_sock, transport, [], [], 0, 0)
        else:
            logging.debug("Too many connections, closing...")
            self.transport.close()
        
            
    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))
        if data[0] == Command.WANTGAME.value:
            logging.debug("Want game")
            
            if WarProtocol.connections == 2:
                player_cards = deal_cards()
                logging.debug("2 players found, dealing cards")
                
                # send game start message to both clients
                WarProtocol.GAME = Game(WarProtocol.GAME.p1_sock, WarProtocol.GAME.p2_sock, player_cards[0], player_cards[1], 0, 0)
                WarProtocol.GAME.p1_sock.write(bytes([Command.GAMESTART.value]) + bytes(WarProtocol.GAME.p1_cards))
                WarProtocol.GAME.p2_sock.write(bytes([Command.GAMESTART.value]) + bytes(WarProtocol.GAME.p2_cards))
                WarProtocol.connections = 0
                WarProtocol.GAME = None

        # if message has PLAYCARD byte in it
        elif data[0] == Command.PLAYCARD.value:
            logging.debug("Game started")
            logging.debug("Card played: %d", data[1])
            # check if card is valid
            if data[1] in WarProtocol.GAME.p1_cards:
                WarProtocol.GAME.p1_cards.remove(data[1])
                WarProtocol.p1_curr_card = data[1]
            elif data[1] in WarProtocol.GAME.p2_cards:
                WarProtocol.GAME.p2_cards.remove(data[1])
                WarProtocol.p2_curr_card = data[1]

            if WarProtocol.p1_curr_card is not None and WarProtocol.p2_curr_card is not None:
                result = compare_cards(WarProtocol.p1_curr_card, WarProtocol.p2_curr_card)
                if result == 1:
                    WarProtocol.GAME.p1_sock.write(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                    WarProtocol.GAME.p2_sock.write(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                    WarProtocol.GAME = WarProtocol.GAME._replace(p1_score = WarProtocol.GAME.p1_score + 1)
                elif result == -1:
                    WarProtocol.GAME.p1_sock.write(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                    WarProtocol.GAME.p2_sock.write(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                    WarProtocol.GAME = WarProtocol.GAME._replace(p2_score = WarProtocol.GAME.p2_score + 1)
                else:
                    WarProtocol.GAME.p1_sock.write(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
                    WarProtocol.GAME.p2_sock.write(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
                    
                WarProtocol.p1_curr_card = None
                WarProtocol.p2_curr_card = None
                
                
            
   
        else:
            # close connection
            logging.debug("Wrong message sent by client, closing connection...")
            self.transport.close()
            
    def send_message():
        pass
            

        
        

async def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    loop = asyncio.get_running_loop()
    server = await loop.create_server(WarProtocol,'127.0.0.1', 4444)
    logging.debug("Started server...")
    
    async with server:
        await server.serve_forever()
        
    
    pass
        
    
        

async def limit_client(host, port, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port)

async def client(host, port):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "draw"
        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch a client/server
    """
    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            # your server should serve clients until the user presses ctrl+c
            asyncio.run(serve_game(host, port))
        except KeyboardInterrupt:
            pass
        return

    if args[0] == "client":
        asyncio.run(client(host, port))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            """
            use `as_completed` to spawn all clients simultaneously
            and collect their results in arbitrary order.
            """
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = asyncio.run(run_all_clients())
        logging.info("%d completed clients", res)

    

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
