"""Simple blackjack client: listen for UDP offers then play via TCP.

This module listens for server UDP offers, connects via TCP and follows the
binary protocol defined in `protocol.py` to play a number of rounds.
"""

import socket
import sys
import protocol

# Human-readable mappings for card display
SUITS = {0: "Hearts", 1: "Diamonds", 2: "Clubs", 3: "Spades"}
RANKS = {1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}


def get_card_name(rank, suit):
    r_str = RANKS.get(rank, str(rank))
    s_str = SUITS.get(suit, "?")
    return f"{r_str} of {s_str}"


def start_client():
    """Discover a server via UDP and play the requested number of rounds."""
    print("Client started, listening for offer requests...")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Cross-platform option: SO_REUSEPORT exists on Unix, fall back to SO_REUSEADDR on Windows
    try:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    udp_sock.bind(("", protocol.UDP_PORT))

    server_ip = None
    server_port = None

    # Wait for an offer packet from a server
    while True:
        data, addr = udp_sock.recvfrom(1024)
        res = protocol.unpack_offer(data)
        if res:
            server_port, server_name = res
            server_ip = addr[0]
            print(f"Received offer from {server_ip} (Server: {server_name})")
            break

    # Connect to the server over TCP and play
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.connect((server_ip, server_port))

        rounds_input = input("How many rounds to play? ")
        try:
            rounds = int(rounds_input)
        except Exception:
            rounds = 1

        team_name = "TeamJoker"
        tcp_sock.sendall(protocol.pack_request(rounds, team_name))

        wins = 0
        total_played = 0

        while total_played < rounds:
            total_played += 1
            print(f"\n--- Starting Round {total_played} ---")

            # Each server payload packet is 9 bytes
            card1Pack = tcp_sock.recv(9)
            card2Pack = tcp_sock.recv(9)
            dealerCardPack = tcp_sock.recv(9)
            if not card1Pack or not card2Pack or not dealerCardPack:
                break

            _, fRank, fSuit = protocol.unpack_payload_server(card1Pack)
            res, sRank, sSuit = protocol.unpack_payload_server(card2Pack)
            _, dRank, dSuit = protocol.unpack_payload_server(dealerCardPack)

            my_cards = [(fRank, fSuit), (sRank, sSuit)]
            dealer_cards = [(dRank, dSuit)]

            print(
                f"Dealt cards: {get_card_name(fRank, fSuit)} and {get_card_name(sRank, sSuit)} , sum : "
                + protocol.calculate_hand(my_cards).__str__()
            )
            print(f"Dealer's visible card: {get_card_name(dRank, dSuit)}")

            stand = False
            while res == protocol.RESULT_ACTIVE and not stand:
                choice = input("Hit or Stand? ").strip().lower()
                if choice == "hit":
                    tcp_sock.sendall(protocol.pack_payload_client("Hittt"))
                else:
                    tcp_sock.sendall(protocol.pack_payload_client("Stand"))
                    stand = True
                    break

                nextPack = tcp_sock.recv(9)
                if not nextPack:
                    print("No more data from server.")
                    break
                res, nRank, nSuit = protocol.unpack_payload_server(nextPack)

                my_cards.append((nRank, nSuit))
                print(
                    f"Dealt card: {get_card_name(nRank, nSuit)} , sum : "
                    + protocol.calculate_hand(my_cards).__str__()
                )
                if res != protocol.RESULT_ACTIVE:
                    break

            if stand:
                while True:
                    nextDealerCardPack = tcp_sock.recv(9)
                    res, cardRank, cardSuit = protocol.unpack_payload_server(nextDealerCardPack)
                    dealer_cards.append((cardRank, cardSuit))
                    print(f"Next dealer card is {cardRank}, {cardSuit} status : {res}")
                    if res != protocol.RESULT_ACTIVE:
                        print("----------------------------------------")
                        break

            if res == protocol.RESULT_DEALER_WIN:
                print("Dealer wins!")
            elif res == protocol.RESULT_CLIENT_WIN:
                wins += 1
                print("You win!")
            else:
                print("It's a tie!")

        print(f"Finished playing {rounds} rounds, win rate: {wins/rounds:.2f}")

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        tcp_sock.close()


if __name__ == "__main__":
    start_client()