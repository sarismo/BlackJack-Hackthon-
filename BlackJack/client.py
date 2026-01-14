import socket
import sys
import protocol

# Mapping for display
SUITS = {0: 'Hearts', 1: 'Diamonds', 2: 'Clubs', 3: 'Spades'}
RANKS = {1: 'Ace', 11: 'Jack', 12: 'Queen', 13: 'King'}

def get_card_name(rank, suit):
    r_str = RANKS.get(rank, str(rank))
    s_str = SUITS.get(suit, '?')
    return f"{r_str} of {s_str}"

def start_client():
    print("Client started, listening for offer requests...")
    
    # UDP Listen
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # --- FIX START: Cross-platform compatibility ---
    try:
        # Try Linux/Mac option first (Required for Hackathon)
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        # Fallback for Windows
        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # --- FIX END ---
    
    udp_sock.bind(("", protocol.UDP_PORT))
    
    server_ip = None
    server_port = None
    
    # Wait for Offer
    while True:
        data, addr = udp_sock.recvfrom(1024)
        res = protocol.unpack_offer(data)
        if res:
            server_port, server_name = res
            server_ip = addr[0]
            print(f"Received offer from {server_ip} (Server: {server_name})") # [cite: 76]
            break
            
    # Connect TCP
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.connect((server_ip, server_port))
        
        # User input for rounds
        # Note: In a real hackathon, you might hardcode this to speed up testing
        rounds_input = input("How many rounds to play? ") 
        try:
            rounds = int(rounds_input)
        except:
            rounds = 1
            
        team_name = "TeamJoker"
        
        # Send Request
        tcp_sock.sendall(protocol.pack_request(rounds, team_name))
        
        # Game Loop
        my_cards = []
        wins = 0
        total_played = 0
        player_value = 0
        
        while total_played < rounds:
            # We sit in a loop receiving payloads
            total_played += 1
            print(f"\n--- Starting Round {total_played } ---")
            card1Pack = tcp_sock.recv(9)
            card2Pack = tcp_sock.recv(9)
            dealerCardPack = tcp_sock.recv(9)
            # print(f"Received card packs lengths: {(card1Pack)}, {(card2Pack)}, {len(dealerCardPack)}")
            if not card1Pack or not card2Pack or not dealerCardPack: break
            
            # Server payload is 9 bytes
            
            _, fRank, fSuit = protocol.unpack_payload_server(card1Pack)
            res , sRank,sSuit = protocol.unpack_payload_server(card2Pack)
            _, dRank, dSuit = protocol.unpack_payload_server(dealerCardPack)
            my_cards = [(fRank, fSuit), (sRank, sSuit)]
            dealer_cards = [(dRank, dSuit)]
            # print(f"Unpacked cards: {(fRank, fSuit)}, {(sRank, sSuit)}, {(dRank, dSuit)}")
            print(f"Dealt cards: {get_card_name(fRank, fSuit)} and {get_card_name(sRank, sSuit)} , sum : "+protocol.calculate_hand(my_cards).__str__())
            print(f"Dealer's visible card: {get_card_name(dRank, dSuit)}")
            
            stand = False
            while res == protocol.RESULT_ACTIVE and not stand:
                choice = input("Hit or Stand? ").strip().lower()
                if choice == 'hit':
                    # Send Hittt [cite: 100]
                    tcp_sock.sendall(protocol.pack_payload_client("Hittt"))
                else:
                    tcp_sock.sendall(protocol.pack_payload_client("Stand"))
                    stand = True
                    break
                
                nextPack = tcp_sock.recv(9)
                # print(f"Received next pack length: {len(nextPack)}")
                if not nextPack:
                    print("No more data from server.")
                    break
                res, nRank, nSuit = protocol.unpack_payload_server(nextPack)
                
                my_cards.append((nRank, nSuit))
                print(f"Dealt card: {get_card_name(nRank, nSuit)} , sum : "+protocol.calculate_hand(my_cards ).__str__())
                if res != protocol.RESULT_ACTIVE:
                    break

            if stand : 
                while True:
                    nextDealerCardPack = tcp_sock.recv(9)
                    res , cardRank,cardSuit = protocol.unpack_payload_server(nextDealerCardPack)
                    dealer_cards.append((cardRank,cardSuit))
                    print(f"Next dealer card is {cardRank}, {cardSuit} status : {res}")
                    if res!=protocol.RESULT_ACTIVE :
                        print("----------------------------------------")
                        break
                        # print("\nWin" if res == protocol.RESULT_CLIENT_WIN else "Lose" if res == protocol.RESULT_DEALER_WIN else "Tie" , "on this round\n")
                    
            if res == protocol.RESULT_DEALER_WIN:
                print("Dealer wins!")
            elif res == protocol.RESULT_CLIENT_WIN:
                wins+=1
                print("You win!")
            else:
                print("It's a tie!")
            
        print(f"Finished playing {rounds} rounds, win rate: {wins/rounds:.2f}") # [cite: 82]

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        tcp_sock.close()

if __name__ == "__main__":
    start_client()