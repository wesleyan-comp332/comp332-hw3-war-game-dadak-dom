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
import threading
import sys


"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""
# p1 and p2 : tuples containing (conn, addr)
# p1given: list of cards given to p1
# p1remaining: list of cards remaining in p1's hand
Game = namedtuple("Game", ["p1", "p2", "p1given", "p2given", "p1remaining", "p2remaining"])

# Stores the clients waiting to get connected to other clients
waiting_clients = []


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
    # TODO
    data = sock.recv(numbytes)
    return data


def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    p1, p2, p1cards, p2cards, p1remain, p2remain = game
    logging.critical("KILLING GAME")
    logging.debug("p1:%s p2%s", p1, p2)
    # logging.debug("p1[0]", p1[0])
    p1[0].close()
    p2[0].close()
    logging.debug("%s", type(p1[0]))
    quit()



def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """
    CARD_MAPPING =  {
        0 : 2,
        1 : 3,
        2 : 4,
        3 : 5,
        4 : 6,
        5 : 7,
        6 : 8,
        7 : 9,
        8 : 10,
        9 : 11, # Jack
        10 : 12, # Queen
        11 : 13,  # King
        12 : 14 # Ace
    }

    card1val = CARD_MAPPING[card1 % 13]
    card2val = CARD_MAPPING[card2 % 13]

    if card1val < card2val:
        return -1
    if card1val > card2val:
        return 1
    return 0
    

def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    deck = list(range(0, 52))
    p1, p2 = [], []
    while len(deck) > 0: # remove a random index from the remaining cards and add it to p1. Repeat for p2. Repeat until done
        p1_card = random.randint(0, len(deck) - 1)
        p1.append(deck.pop(p1_card))
        p2_card = random.randint(0, len(deck) - 1)
        p2.append(deck.pop(p2_card))
    logging.debug("Made two decks:\nplayer1: \n\t%s\nplayer2\n\t%s", p1, p2)
    return p1, p2
    

def play_game(game):
    # Idea is to read the cards that are played by each player (i.e. readexactly), compare, and then send a result for the round
    # p1_move = readexactly
    p1, p2, p1cards, p2cards, p1remain, p2remain = game
    while not p1remain == [] and not p2remain == []:
        try:
            p1_move = list(readexactly(p1[0], 2))
            logging.debug("Player 1 move: %s", list(p1_move))
            p2_move = list(readexactly(p2[0], 2))
            logging.debug("Player 2 move: %s", list(p2_move))

            # CHECKING IF VALID MOVE:
            # Check that the client makes a move (Command.PLAYCARD.value)
            if not (p1_move[0] == Command.PLAYCARD.value or p2_move[0] == Command.PLAYCARD.value):
                raise Exception("Unexpected Command")
            # Check that the move is valid (card is both in cards_given and cards_remaining)
            # p1
            if not (p1_move[1] in p1cards and p1_move[1] in p1remain):
                raise Exception("Player 1 played a card they don't have")
            # p2
            if not (p2_move[1] in p2cards and p2_move[1] in p2remain):
                raise Exception("Player 2 played a card they don't have")
            # Update the game state
            p1remain.remove(p1_move[1])
            p2remain.remove(p2_move[1])

            # Compare cards and send result to each client
            result = compare_cards(p1_move[1], p2_move[1])
            
            if result < 0:
                #p2 won
                p1[0].send(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
                p2[0].send(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
            elif result > 0:
                #p1 won
                p1[0].send(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
                p2[0].send(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
            else:
                # Draw
                p1[0].send(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
                p2[0].send(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))

            logging.debug("Comparing the two cards: %s, %s", p1_move[1], p2_move[1])
            logging.debug("result: %s", result)
        except Exception as e:
            logging.warning("Error occured, must kill game %s %s %s", p1, p2, e)
            kill_game(game)
            # quit()
        # finally:
        #     p1[0].close()
        #     p2[0].close()

def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    # Create server, open connections
    with socket.create_server((host, port)) as server:
        logging.debug("Server created: %s", server)
        while True:
            conn, addr = server.accept()
            logging.debug('Client connected: \n\tConnection: %s \n\tAddress: %s', conn, addr)
            waiting_clients.append((conn, addr))
            logging.debug('Game queue: %s', waiting_clients)
            # Read exactly some number of bytes
            # logging.debug("Test: %s", readexactly(conn, 2).decode('utf-8'))
            # if you have two clients connected, start a game, remove them from waitlist
            if len(waiting_clients) >= 2:
                player1 = waiting_clients.pop(0)
                player2 = waiting_clients.pop(0)
                # Check to make sure that the clients have sent to appropriate WANTGAME message
                p1mes = list(readexactly(player1[0], 2))
                p2mes = list(readexactly(player2[0], 2))

                if p1mes == [0,0] and p2mes == [0,0]:
                    logging.debug("Starting game with %s and %s, queue is now \n\t%s", player1[1], player2[1], waiting_clients)
                    # decide on the decks of cards for each player
                    p1cards, p2cards = deal_cards()
                    # send the cards to each client
                    player1[0].send(bytes([Command.GAMESTART.value] + p1cards))
                    # player1[0].send(bytes(p1cards))
                    player2[0].send(bytes([Command.GAMESTART.value] + p2cards))
                    # player2[0].send(bytes(p2cards))
                    game = Game(player1, player2, p1cards, p2cards, p1cards.copy(), p2cards.copy())
                    thread = threading.Thread(target=play_game, args=(game,))
                    thread.start()
                else:
                    logging.warning("A client has sent an incorrect message: \n\tp1: %s\n\tp2: %s", p1mes, p2mes)
            # Not sure if this should be within the "if" or not, will see...
            # Step through the game
            # for game in games_playing:
            #     # Idea is to read the cards that are played by each player (i.e. readexactly), compare, and then send a result for the round
            #     # p1_move = readexactly
            #     p1, p2, p1cards, p2cards, p1remain, p2remain = game
            #     while not p1remain == [] and not p2remain == []:
            #         try:
            #             p1_move = list(readexactly(p1[0], 2))
            #             logging.debug("Player 1 move: %s", list(p1_move))
            #             p2_move = list(readexactly(p2[0], 2))
            #             logging.debug("Player 2 move: %s", list(p2_move))

            #             # CHECKING IF VALID MOVE:
            #             # Check that the client makes a move (Command.PLAYCARD.value)
            #             if not (p1_move[0] == Command.PLAYCARD.value or p2_move[0] == Command.PLAYCARD.value):
            #                 raise Exception("Unexpected Command")
            #             # Check that the move is valid (card is both in cards_given and cards_remaining)
            #             # p1
            #             if not (p1_move[1] in p1cards and p1_move[1] in p1remain):
            #                 raise Exception("Player 1 played a card they don't have")
            #             # p2
            #             if not (p2_move[1] in p2cards and p2_move[1] in p2remain):
            #                 raise Exception("Player 2 played a card they don't have")
            #             # Update the game state
            #             p1remain.remove(p1_move[1])
            #             p2remain.remove(p2_move[1])

            #             # Compare cards and send result to each client
            #             result = compare_cards(p1_move[1], p2_move[1])
                        
            #             if result < 0:
            #                 #p2 won
            #                 p1[0].send(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
            #                 p2[0].send(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
            #             elif result > 0:
            #                 #p1 won
            #                 p1[0].send(bytes([Command.PLAYRESULT.value, Result.WIN.value]))
            #                 p2[0].send(bytes([Command.PLAYRESULT.value, Result.LOSE.value]))
            #             else:
            #                 # Draw
            #                 p1[0].send(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))
            #                 p2[0].send(bytes([Command.PLAYRESULT.value, Result.DRAW.value]))

            #             logging.debug("Comparing the two cards: %s, %s", p1_move[1], p2_move[1])
            #             logging.debug("result: %s", result)

            #             # p1[0].send(bytes([Command.PLAYRESULT.value, result]))
            #             # p2[0].send(bytes([Command.PLAYRESULT.value, result]))


                    # except Exception as e:
                    #     logging.warning("Error occured, must kill game %s %s %s", p1, p2, e)
                    #     kill_game(game)

                

    

async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port, loop)

async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        # INSERT DEBUG STATEMENT HERE
        logging.debug("CARDS RECEIVED: %s", list(card_msg))
        logging.debug("CARDS RECEIVED: %s", card_msg)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            logging.debug("CARD SENT: %s", list(bytes([Command.PLAYCARD.value, card])))
            result = await reader.readexactly(2)
            logging.debug("Result: %s", result)
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "drew"
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
            serve_game(host, port)
        except KeyboardInterrupt:
            pass
        return
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(loop)
        
    if args[0] == "client":
        loop.run_until_complete(client(host, port, loop))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, loop, sem)
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
        res = loop.run_until_complete(
            asyncio.Task(run_all_clients(), loop=loop))
        logging.info("%d completed clients", res)

    loop.close()

if __name__ == "__main__":
    # Changing logging to DEBUG
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
