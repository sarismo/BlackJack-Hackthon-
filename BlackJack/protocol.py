"""Binary protocol helpers for the Blackjack hackathon.

Provides packing/unpacking helpers for the UDP offer, TCP request,
client payloads and server payloads used by the simple blackjack server
and client in this repository.
"""

import struct

# --- Constants ---
MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_OFFER = 0x2
MSG_TYPE_REQUEST = 0x3
MSG_TYPE_PAYLOAD = 0x4

# UDP discovery port used by server broadcasts
UDP_PORT = 13117

# Game result codes used in payloads
RESULT_DEALER_WIN = 0x2
RESULT_CLIENT_WIN = 0x3
RESULT_TIE = 0x1
RESULT_ACTIVE = 0x0


def pack_offer(server_port, server_name):
    """Create a UDP discovery offer packet.

    The server name is padded/truncated to 32 bytes.
    """
    server_name_bytes = server_name.encode("utf-8")[:32].ljust(32, b"\x00")
    return struct.pack("!IBH32s", MAGIC_COOKIE, MSG_TYPE_OFFER, server_port, server_name_bytes)


def unpack_offer(data):
    """Parse a UDP offer packet, return (port, name) or None on error."""
    try:
        if len(data) != 39:
            return None
        cookie, msg_type, port, name_bytes = struct.unpack("!IBH32s", data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_OFFER:
            return None
        return port, name_bytes.decode("utf-8").rstrip("\x00")
    except Exception:
        return None


def pack_request(num_rounds, team_name):
    """Pack the TCP request sent from client to server.

    `team_name` is padded/truncated to 32 bytes.
    """
    team_name_bytes = team_name.encode("utf-8")[:32].ljust(32, b"\x00")
    return struct.pack("!IBB32s", MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds, team_name_bytes)


def calculate_hand(cards):
    """Return the blackjack numeric value for a list of (rank, suit) cards."""
    total = 0
    aces = 0
    for rank, suit in cards:
        if rank == 1:  # Ace
            aces += 1
            total += 11
        elif rank >= 10:  # Face cards + 10
            total += 10
        else:
            total += rank

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def unpack_request(data):
    """Parse a TCP request packet and return (rounds, team_name) or None."""
    try:
        if len(data) != 38:
            return None
        cookie, msg_type, rounds, name_bytes = struct.unpack("!IBB32s", data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_REQUEST:
            return None
        return rounds, name_bytes.decode("utf-8").rstrip("\x00")
    except Exception:
        return None


def pack_payload_client(decision):
    """Pack a client decision payload (5-byte decision field).

    Accepted decision strings in this project are "Hittt" and "Stand".
    """
    decision_bytes = decision.encode("utf-8")[:5].ljust(5, b"\x00")
    return struct.pack("!IB5s", MAGIC_COOKIE, MSG_TYPE_PAYLOAD, decision_bytes)


def unpack_payload_client(data):
    """Unpack a client payload and return the decision string or None."""
    try:
        if len(data) != 10:
            return None
        cookie, msg_type, decision_bytes = struct.unpack("!IB5s", data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None
        return decision_bytes.decode("utf-8").rstrip("\x00")
    except Exception:
        return None


def pack_payload_server(result, card_rank, card_suit):
    """Pack a server -> client game-state payload.

    Fields: magic cookie, message type, result code, card rank (2 bytes), card suit (1 byte).
    """
    return struct.pack("!IBBHB", MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result, card_rank, card_suit)


def unpack_payload_server(data):
    """Unpack a server payload and return (result, rank, suit) or None."""
    try:
        if len(data) != 9:
            return None
        cookie, msg_type, result, rank, suit = struct.unpack("!IBBHB", data)
        if cookie != MAGIC_COOKIE or msg_type != MSG_TYPE_PAYLOAD:
            return None
        return result, rank, suit
    except Exception:
        return None


def get_card_points(rank, suit):
    """Return the blackjack point value for a single card rank."""
    if rank == 1:
        return 11  # Ace
    elif rank >= 10:
        return 10  # Face cards and 10
    else:
        return rank