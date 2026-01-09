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
        
        while total_played < rounds:
            # We sit in a loop receiving payloads
            # Server payload is 9 bytes
            data = tcp_sock.recv(9)
            if not data: break
            
            result, rank, suit = protocol.unpack_payload_server(data)
            
            if result == protocol.RESULT_ACTIVE:
                # We received a card
                card_name = get_card_name(rank, suit)
                print(f"Received card: {card_name}")
                my_cards.append(rank) # simplify storage for logic
                
                # Simple logic to decide Hit or Stand (User interactive)
                # In the assignment, user is prompted.
                print("Your hand value: Calculating...") 
                
                choice = input("Hit or Stand? ").strip().lower()
                if choice == 'hit':
                    # Send Hittt [cite: 100]
                    tcp_sock.sendall(protocol.pack_payload_client("Hittt"))
                else:
                    tcp_sock.sendall(protocol.pack_payload_client("Stand"))
                    
            elif result != protocol.RESULT_ACTIVE:
                # Round Over
                if result == protocol.RESULT_WIN:
                    print("You Won!")
                    wins += 1
                elif result == protocol.RESULT_LOSS:
                    print("You Lost.")
                else:
                    print("It's a Tie.")
                
                total_played += 1
                my_cards = [] # Reset for next round
                print("-" * 20)

        print(f"Finished playing {rounds} rounds, win rate: {wins/rounds:.2f}") # [cite: 82]

    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        tcp_sock.close()

if __name__ == "__main__":
    start_client()