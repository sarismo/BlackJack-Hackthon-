import struct

# --- Constants ---
MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2
MSG_TYPE_REQUEST = 0x3
MSG_TYPE_PAYLOAD = 0x4

# Ports
UDP_PORT = 13117  # Hardcoded per source [114]

# Game Constants
RESULT_DEALER_WIN = 0x2
RESULT_CLIENT_WIN = 0x3
RESULT_TIE = 0x1
RESULT_ACTIVE = 0x0

def pack_offer(server_port, server_name):
    """Server -> Client UDP Offer"""
    # Pad name to 32 bytes
    server_name_bytes = server_name.encode('utf-8')[:32].ljust(32, b'\x00')
    return struct.pack('!IBH32s', MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, server_name_bytes)

def unpack_offer(data):
    try:
        if len(data) != 39: return None
        cookie, msg_type, port, name_bytes = struct.unpack('!IBH32s', data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_OFFER: return None
        return port, name_bytes.decode('utf-8').rstrip('\x00')
    except: return None

def pack_request(num_rounds, team_name):
    """Client -> Server TCP Request"""
    team_name_bytes = team_name.encode('utf-8')[:32].ljust(32, b'\x00')
    return struct.pack('!IBB32s', MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds, team_name_bytes)



def calculate_hand( cards):
    """Calculates blackjack value."""
    total = 0
    for rank, suit in cards:
        if rank == 1: # Ace
            total += 11
        elif rank >= 10: # Face cards + 10
            total += 10
        else:
            total += rank
    
    
    return total
    
def unpack_request(data):
    try:
        if len(data) != 38: return None
        cookie, msg_type, rounds, name_bytes = struct.unpack('!IBB32s', data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_REQUEST: return None
        return rounds, name_bytes.decode('utf-8').rstrip('\x00')
    except: return None

def pack_payload_client(decision):
    """
    Client -> Server Payload (Player Decision).
    Decision MUST be "Hittt" or "Stand" (5 bytes)[cite: 100].
    """
    decision_bytes = decision.encode('utf-8')[:5].ljust(5, b'\x00')
    return struct.pack('!IB5s', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, decision_bytes)

def unpack_payload_client(data):
    try:
        if len(data) != 10: return None
        cookie, msg_type, decision_bytes = struct.unpack('!IB5s', data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD: return None
        return decision_bytes.decode('utf-8').rstrip('\x00')
    except: return None

def pack_payload_server(result, card_rank, card_suit):
    """
    Server -> Client Payload (Game State).
    Rank: 1-13 (2 bytes), Suit: 0-3 (1 byte)[cite: 102, 103].
    """
    return struct.pack('!IBBHB', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result, card_rank, card_suit)

def unpack_payload_server(data):
    try:
        #print("unpack_payload_server called")
        if len(data) != 9: return None
        #print(f"unpack_payload_server data length: {len(data)}")
        cookie, msg_type, result, rank, suit = struct.unpack('!IBBHB', data)
        #print(f"unpack_payload_server unpacked: cookie={cookie}, msg_type={msg_type}, result={result}, rank={rank}, suit={suit}")
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD: return None
        return result, rank, suit
    except: 
        #print("unpack_payload_server error")
        return None


def get_card_points(rank,suit):
    """Returns the blackjack point value of a card rank."""
    if rank == 1:
        return 11  # Ace
    elif rank >= 10:
        return 10  # Face cards and 10
    else:
        return rank