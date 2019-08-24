"""
Taylor Barmak

This twitter bot uses tweepy to play games of chess against people on twitter.

Moves are made by tweeting at the bot with a move in PGN notation. The bot uses the Stockfish engine to generate its
reply moves. The bot also replies to special hashtags.
"""
import tweepy
import re
import chess
import chess.engine
import time
import requests
import os
import email
import smtplib

# Important access keys
CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_KEY = ''
ACCESS_SECRET = ''

# Get access to the api
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)

# File to store the last seen id so it doesn't analyze the same tweet twice
FILE1_NAME = 'last_seen_id.txt'
# File to store the games of each user
FILE2_NAME = 'games.txt'

"""
retrieve_last_seen_id will return the id of the last seen mention (tweet)
file_name - the name of the file from where the id will be read
returns the last seen id
"""
def retrieve_last_seen_id(file_name):
    f_read = open(file_name, 'r')
    last_seen_id = int(f_read.read().strip())
    f_read.close()
    return last_seen_id

"""
store_last_seen_id will write the last seen id to a file
last_seen_id - the id of the last seen mention (tweet)
file_name - the name of the file where the id will be stored
"""
def store_last_seen_id(last_seen_id, file_name):
    f_write = open(file_name, 'w')
    f_write.write(str(last_seen_id))
    f_write.close()

"""
delete_all_tweets will delete all tweets on the account to make testing more efficient
"""
def delete_all_tweets():
    tweets = api.user_timeline()
    for tweet in tweets:
        api.destroy_status(tweet.id)

"""
possible_moves will return a list of all of the possible moves in a position in PGN notation
board - a chess.Board() object
return a list of the possible moves
"""
def possible_moves(board):
    string = re.search(r'\([^\)]*\)', str(board.legal_moves)).group()
    # Remove the parentheses
    string = string[1:-1]
    return string.split(', ')


"""
push_pgn will apply the moves listed in the argument and return a board after those moves have been applied
pgn - a list of moves in PGN notation without numbers
return a chess.Board() object after those moves have been applied in order
"""
def push_pgn(pgn):
    board = chess.Board()
    for move in pgn:
        board.push_san(move)
    return board

"""
apply_player_move will attempt to make a move for the player
game_history - a list of the moves in PGN notation without numbers
attemtped_move - the attemped player move in PGN notation
return True is the move was successfully applied, False otherwise
"""
def apply_player_move(game_history, attempted_move):
    # Get the board to the current position
    board = push_pgn(game_history)
    pos_moves = possible_moves(board)
    if attempted_move not in pos_moves:
        print("That move is not legal in the position.")
        return False
    else:
        game_history.append(attempted_move)
        return True

"""
apply_bot_move will take a board and make a move using stockfish
game_history - a list of the previous moves in PGN notation without numbers
return the move that was made
"""
def apply_bot_move(game_history):
    # Open the stockfish engine
    engine = chess.engine.SimpleEngine.popen_uci("stockfish-10-win\Windows\stockfish_10_x64.exe")
    # Give it 5 seconds per move
    limit = chess.engine.Limit(time=5.0)
    board = push_pgn(game_history)
    my_move = re.search(r'move=([^,]*)', str(engine.play(board, limit))).group(1)
    my_move = board.san(chess.Move.from_uci(my_move))
    game_history.append(my_move)
    return my_move

"""
pgn_list_to_string takes the game moves in a list and converts them to a string separated by spaces for filewriting
pgn_list - a list of moves in pgn notation
return the moves separated by spaces in a string
"""
def pgn_list_to_string(pgn_list):
    ret = ""
    for a in pgn_list:
        ret += a + " "
    return ret

"""
create_board_image will return the filename of an image of the chess board
board - a chess.Board() object
return the file name of an image of a chess board in the same state as the chess.Board() object
"""
def create_board_image(board):
    # URL that loads an image of the board if you concat the FEN to the end of it
    url = "http://www.fen-to-image.com/image/"
    fen = re.findall('\S*', board.fen())[0]
    url = url + fen
    filename = 'board.jpg'
    request = requests.get(url, stream=True)
    with open('board.jpg', 'wb') as image:
        for chunk in request:
            image.write(chunk)
    return filename

"""
split_to_240_char will take a string and split it into pieces with 240 characters or less
string - a string to be split
return a list of the pieces of the string after it has been split
"""
def split_to_240_char(string):
    ret = []
    # Split the string on the spaces so the string fragments will end on a space instead of cutting words in half
    string_list = string.split()
    fragment = ""
    for a in string_list:
        if len(fragment + a) <= 240:
            fragment += a + " "
        else:
            ret.append(fragment)
            fragment = ""
    ret.append(fragment)
    return ret

"""
send_email method will send an email from ******* to *******
subject - the subject of the message
message - the message to be sent
"""
def send_email(subject, message):
    msg = email.message_from_string(message)
    msg['From'] = ""
    msg['To'] = ""
    msg['Subject'] = subject
    s = smtplib.SMTP("smtp.office365.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login('', '')
    s.sendmail("", "", msg.as_string())
    s.quit()
"""
Main method will answer tweets appropriately.
"""
def main():
    # Retrieve the last seen id and pull the mentions that came after that id
    last_seen_id = retrieve_last_seen_id(FILE1_NAME)
    mentions = api.mentions_timeline(last_seen_id, tweet_mode='extended')

    # Go through each of the mentions
    for mention in reversed(mentions):
        print("Tweet received: " + mention.full_text)
        # Change the last seen id to be the id of the current tweet
        last_seen_id = mention.id
        store_last_seen_id(last_seen_id, FILE1_NAME)
        tweet_text = mention.full_text

        # make_a_move is a boolean to see if the bot should continue to the second if, elif, else structure
        make_a_move = True

        # game_over is a boolean to see if the bot should let the user know how to create a gif of their game
        game_over = False

        # Open the file with the games
        games = open(FILE2_NAME, "r")
        # Store all of the games in a list
        list_of_games = []
        for game in games:
            list_of_games.append(game.strip().split(","))
        games.close()
        print("List of games: " + str(list_of_games))

        # Check if a game with this user already exists
        game_index = -1
        for game in range(len(list_of_games)):
            if mention.user.screen_name.lower() == list_of_games[game][0].lower():
                game_index = game
        print("Game index: " + str(game_index))
        # The following if, elif, else structure checks for special hashtags to act accordingly and makes changes
        # to the current game before any moves are applied
        # If #resign is in the tweet say gg, and erase their game
        if '#resign' in tweet_text.lower():
            make_a_move = False
            # Removes their game from the list of games so it won't be written to the file
            if game_index != -1:
                game_over = True
                curr_game = list_of_games[game_index]
                list_of_games.remove(list_of_games[game_index])
            api.update_status("@" + mention.user.screen_name + " You made me work hard for that. Good game!",
                              mention.id)
        # Check if they are trying to report an error
        elif '#error' in tweet_text.lower():
            make_a_move = False
            print("User tried to report an error.")
            message = "A user reported an error using #error in their tweet. Here are the tweet contents: "
            message += "\nMention ID: " + str(mention.id) + "\nUsername: " + mention.user.screen_name + "\nText: " + mention.full_text
            send_email("An Error Was Reported", message)
        # Check if they want to see all valid moves
        elif '#possiblemoves' in tweet_text.lower():
            make_a_move = False
            print("#possiblemoves was in tweet text.")
            # If the game already exists
            if game_index != -1:
                print("Printing possible moves for an existing game.")
                board = push_pgn(list_of_games[game_index][1].split())
            # If a game with that user has not been started
            else:
                print("Printing possible moves for a game that has not been started.")
                board = chess.Board()
            pos_moves = possible_moves(board)
            filename = create_board_image(board)
            api.update_with_media(filename, status="@" + mention.user.screen_name + " Here are all of the valid moves in this position: " +
                pgn_list_to_string(pos_moves), in_reply_to_status_id=mention.id)
        # Check if they want to see the previous move history of their game
        elif '#getpgn' in tweet_text.lower():
            make_a_move = False
            print("#getpgn in tweet text.")
            if game_index != -1:
                message = str(list_of_games[game_index][1])
                print("Message: ")
                print(message)
                tweets = split_to_240_char(message)
                print("The message was split.")
                print(tweets)
                for a in tweets:
                    api.update_status("@" + mention.user.screen_name + " " + a, mention.id)
            else:
                api.update_status("@" + mention.user.screen_name + " No game found.", mention.id)
        # If they are not in the system and they did not tweet #startgame, let them know
        elif game_index == -1 and "#startgame" not in tweet_text.lower():
            make_a_move = False
            print("User tried to start a game without #startgame")
            api.update_status("@" + mention.user.screen_name + " Include #startgame if you would like to start a game.", mention.id)
        # The games are stored in the file in the format "username, game in pgn notation"
        # For example:
        # codinglover123, e4 e5 d4
        # chessiscool, d4
        # curr_game will store the status of the current game
        elif '#startgame' in tweet_text.lower():
            if game_index != -1:
                # If #startgame is in the tweet and the user is in the system, their previous game will be erased
                print("Previous game erased. New game started.")
                curr_game = list_of_games[game_index]
                # Erase the move history by making it an empty string
                curr_game[1] = ""
            else:
                # Otherwise current game will have the username in the first index and an empty string in the second
                curr_game = [mention.user.screen_name, ""]
                list_of_games.append(curr_game)
                print("Current game: ")
                print(curr_game)
        else:
            curr_game = list_of_games[game_index]

        # If a move should be played (ie no special hashtags or incorrectly following the instructions)
        if make_a_move:
            # If they didn't make a move and want to play as black, their move will be an empty string
            move_tried = ''
            # Extract the move that is trying to be made
            if len(re.findall('captures ([^#]*)', tweet_text)) != 0:
                move_tried = (re.findall('captures ([^#]*)', tweet_text)[0]).strip()
                print("Attempted move found via regex: " + move_tried)
                print("Length of move: " + str(len(move_tried)))

            # Get the move history as a list
            move_history = curr_game[1].split()

            # If the player tried to make a move
            if len(move_tried) > 0:
                print("Player tried to make a move.")
                # If the move was successfully made
                if apply_player_move(move_history, move_tried):
                    print("Player move successfully made.")
                    # Check if they have put the bot in checkmate
                    board = push_pgn(move_history)
                    # If the user's move put the bot in checkmate, congratulate them
                    if board.is_checkmate():
                        game_over = True
                        list_of_games.remove(curr_game)
                        filename = create_board_image(board)
                        api.update_with_media(filename,
                                            status="@" + mention.user.screen_name + " You mated me! Congratulations!",
                                            in_reply_to_status_id=mention.id)
                    # Otherwise, have the bot make a move in reply
                    else:
                        print("Bot successfully made a move in reply.")
                        bot_move = apply_bot_move(move_history)
                        board = push_pgn(move_history)
                        filename = create_board_image(board)
                        # If the bot put the user in checkmate, let the user know
                        if board.is_checkmate():
                            game_over = True
                            list_of_games.remove(curr_game)
                            print("Bot put user in checkmate.")
                            api.update_with_media(filename, status="@" + mention.user.screen_name + " " + bot_move + "Checkmate!",
                                    in_reply_to_status_id=mention.id)
                        # Otherwise, just tweet the bot's move and a picture of the game
                        else:
                            api.update_with_media(filename, status="@" + mention.user.screen_name + " " + bot_move,
                                    in_reply_to_status_id=mention.id)
                # If the user's move didn't go through, tweet them back that it was invalid
                else:
                    print("Player move was invalid.")
                    board = push_pgn(move_history)
                    filename = create_board_image(board)
                    api.update_with_media(filename, status="@" + mention.user.screen_name +
                            " That move is invalid. If you would to see a list of valid moves, use the #possiblemoves",
                            in_reply_to_status_id=mention.id)
            # If they are trying to start the game as black have the bot make the first move
            elif '#startgame' in tweet_text.lower():
                print("Player trying to start the game as black.")
                bot_move = apply_bot_move(move_history)
                print("Move history after applying the bot move: ")
                print(move_history)
                board = push_pgn(move_history)
                filename = create_board_image(board)
                api.update_with_media(filename, status="@" + mention.user.screen_name + " " + bot_move,
                        in_reply_to_status_id=mention.id)
            # If they did not make a move (If they tweeted a # that wasn't one of the ones with a special function without a move before it)
            else:
                print("Player didn't make a move.")
                board = push_pgn(move_history)
                filename = create_board_image(board)
                api.update_with_media(filename, status="@" + mention.user.screen_name + " You need to make a move.", in_reply_to_status_id=mention.id)
            # Delete the file from the computer
            os.remove(filename)

            # Make the changes to the move history in list_of_games
            # Don't write games without moves to the file
            # This happens when the user has the #startgame with an invalid move
            if len(move_history) == 0:
                list_of_games.remove(curr_game)
            # Otherwise replace the moves in curr_game with the updated move_history
            else:
                curr_game[1] = pgn_list_to_string(move_history)

        if game_over:
            pgn = split_to_240_char(curr_game[1])
            print("Here is the pgn: " + str(pgn))
            api.update_status("@" + mention.user.screen_name + " Use this link and the following pgn to create a gif of your game! https://www.chess.com/gifs", mention.id)
            time.sleep(5)
            for a in pgn:
                print("I entered the for loop.")
                api.update_status("@" + mention.user.screen_name + " " + a, mention.id)

        # Write to the games.txt file with the updated result
        f = open(FILE2_NAME, "w")
        for game in list_of_games:
            f.write(game[0] + ',' + game[1] + '\n')

while True:
    print("Loop started.")
    try:
        main()
    except:
        pass
    time.sleep(30)
