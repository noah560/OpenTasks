import time
import socket
from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Random import get_random_bytes

DAY = 24*60*60

def get_key():
    with open("OpenTasks_data/user_key", "rb") as f:
        d = f.read()
    return d

# List of (timestamp, username, nonce)
used_timestamps = []

def clear_old_timestamps():
    global used_timestamps
    l = len(used_timestamps)
    now = time.time()
    for bw in range(l):
        i = l-bw-1
        if used_timestamps[i][0] < now - 5 * 60 - 10:
            del used_timestamps[i]


# Returns a tuple of (username, plaintext)
# if checks succede and returns None if
# checks fail
def process_encrypted_data(encrypted):
    try:
        if len(encrypted) < 2 + 9 + 16 + 24:
            return
        aad_size = int.from_bytes(encrypted[0:2], byteorder="big")
        if aad_size <= 8:
            # Doesn't include username or full timestamp
            return
        aad = encrypted[2:(2+aad_size)]
        if len(encrypted) < 2 + aad_size + 0 + 16 + 24:
            return
        timestamp = int.from_bytes(aad[0:8], byteorder="little")
        try:
            username = aad[8:].decode("utf-8")
        except UnicodeDecodeError:
            return
        # Verify timestamp
        now = int(time.time())
        if timestamp > now + 10:
            return
        if timestamp < now - 5 * 60:
            return
        clear_old_timestamps()
        # Verify key
        key = get_key()
        if len(key) != 32:
            raise ValueError(
                f"Incorrect key length for user {username}."
            )
        nonce = encrypted[-24:]
        if (timestamp, username, nonce) in used_timestamps:
            return
        ciphertext = encrypted[(aad_size+2):(-16-24)]
        tag = encrypted[(-24-16):-24]
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        try:
            cipher.update(aad)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            used_timestamps.append((timestamp, username, nonce))
            return (username, plaintext)
        except ValueError:
            return
    except IndexError:
        return

# Encrypts a message
def encrypt_data(plaintext, username):
    username_bin = username.encode("utf-8")
    timestamp = int(time.time()).to_bytes(8, byteorder="little")
    aad = timestamp + username_bin
    key = get_key()
    if len(key) != 32:
        raise ValueError(
            f"Incorrect key length for user {username}."
        )
    nonce = get_random_bytes(24)
    cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    cipher.update(aad)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return len(aad).to_bytes(2, byteorder="big") + aad + ciphertext + tag + nonce


def recieve(conn, size):
    data = bytearray()
    while len(data) < size:
        part = conn.recv(size - len(data))
        if not part:
            raise ValueError(
                "Not enough data!"
            )
        data.extend(part)
    return bytes(data)


def request(data):
    en = encrypt_data(data, "user")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 5324))
    s.sendall(b"\x01")
    try:
        if len(en) > 65535:
            raise ValueError("Encrypted data too big!")
        s.sendall(len(en).to_bytes(2, byteorder="big"))
        s.sendall(en)
        size = int.from_bytes(recieve(s, 2), byteorder="big")
        response = recieve(s, size)
        result = process_encrypted_data(response)
        if result is None:
            raise ValueError("The response could not be validated!")
        return result[1]
    finally:
        s.close()

while True:
    print("Select a request type:")
    print("  0: read file")
    print("  1: read file section")
    print("  2: get file size")
    print("  3: write entire file")
    print("  4: write preexisting section")
    print("  5: append to file")
    print("  6: delete file end")
    print("  7: delete file")
    print("  8: list files")
    print("  9: push line")
    print(" 10: pop line from end")
    print(" 11: pop line from start")
    item = input("Enter your selection: ")
    if not item.isnumeric():
        print("Enter a number!")
        break
    item = int(item)
    item_byte = item.to_bytes(1, byteorder="big")
    if item == 0: # read file
        f = input("Filename: ")
        print("Data: ")
        print(request(
            item_byte + f.encode("utf-8")
        ).decode("utf-8"))
    elif item == 1: # read section of file
        f = input("Filename: ")
        print("First 10 bytes: ")
        print(request(
            item_byte + f.encode("utf-8") +
            b"\n0\n10"
        ).decode("utf-8"))
    elif item == 2: # get file size
        f = input("Filename: ")
        print(request(
            item_byte + f.encode("utf-8")
        ).decode("utf-8"))
    elif item == 3: # write entire file
        f = input("Filename: ")
        d = input("Data: ").replace("\\n", "\n").replace("\\\\", "\\")
        request(item_byte + f.encode("utf-8") + b"\n" + d.encode("utf-8"))
    elif item == 4: # write preexisting section
        f = input("Filename: ")
        start = int(input("Start: "))
        data = input("Data: ")
        request(
            item_byte +
            f.encode("utf-8") + b"\n" +
            str(start).encode("utf-8") + b"\n" +
            data.encode("utf-8")
        )
    elif item == 5: # append to file
        f = input("Filename: ")
        data = input("Data: ")
        request(
            item_byte +
            f.encode("utf-8") + b"\n" +
            data.encode("utf-8")
        )
    elif item == 6: # delete file end
        f = input("Filename: ")
        amount = int(input("Amount: "))
        request(
            item_byte +
            f.encode("utf-8") + b"\n" +
            str(amount).encode("utf-8")
        )
    elif item == 7: # delete file
        f = input("Filename: ")
        request(
            item_byte +
            f.encode("utf-8")
        )
    elif item == 8: # list files
        print(request(
            item_byte
        ).decode("utf-8"))
    elif item == 9: # push line
        request(
            item_byte +
            input("Filename: ").encode("utf-8") + b"\n" +
            input("Line: ").encode("utf-8")
        )
    elif item == 10: # pop line from end
        print(request(
            item_byte +
            input("Filename: ").encode("utf-8")
        ).decode("utf-8"))
    elif item == 11: # pop line from start
        print(request(
            item_byte +
            input("Filename: ").encode("utf-8")
        ).decode("utf-8"))
    else:
        print("Type a valid option!")

