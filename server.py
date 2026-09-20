import os
import time
from pathlib import Path
import socket
from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Random import get_random_bytes

DATA_DIR = "OpenTasks_data"

DAY = 24*60*60

class UserHandle:
    def __init__(self, path):
        # So we can just use concatenation
        # on all OSs later
        self.path = os.path.join(path, "")
    def read_file(self, name):
        with open(self.path + name, "rb") as f:
            d = f.read()
        return d
    def read_file_section(self, name, start, size):
        with open(self.path + name, "rb") as f:
            f.seek(start, 0)
            d = f.read(size)
        return d
    def get_file_size(self, name):
        with open(self.path + name, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
        return size
    def write_file(self, name, data):
        with open(self.path + name, "wb") as f:
            f.write(data)
    def write_file_section(self, name, start, data):
        with open(self.path + name, "r+b") as f:
            f.seek(start, 0)
            f.write(data)
    def append(self, name, data):
        with open(self.path + name, "ab") as f:
            f.write(data)
    def delete(self, name):
        os.remove(self.path + name)
    def list_files(self):
        return os.listdir(self.path)
    def push_line(self, name, data):
        with open(self.path + name, "r+b") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")
            f.write(data)
    def pop_ending_line(self, name):
        d = []
        with open(self.path + name, "rb") as f:
            for line in f:
                d.append(f.read().strip("\r\n"))
        if len(d[-1]) == 0:
            d.pop()
        data = d.pop()
        with open(self.path + name, "wb") as f:
            for i in d:
                f.write(i)
                f.write(b"\n")
        return data
    def pop_starting_line(self, name):
        d = []
        with open(self.path + name, "rb") as f:
            for line in f:
                d.append(f.read().strip("\r\n"))
        if len(d[-1]) == 0:
            d.pop()
        data = d.pop(0)
        with open(self.path + name, "wb") as f:
            for i in d:
                f.write(i)
                f.write(b"\n")
        return data


class DataManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.mkdir(DATA_DIR)
        elif not os.path.isfile(DATA_DIR):
            raise Exception(
                f"A file named {DATA_DIR} conflicts with the data directory!"
            )
    def get_user(self, name):
        if not name.isalnum():
            raise ValueError("Invalid username!")
        if not name.isascii():
            raise ValueError("Invalid username!")
        return UserHandle(os.path.join(DATA_DIR, name))
    def close(self):
        pass


data = DataManager()
used_timestamps = []

def clear_old_timestamps():
    global used_timestamps
    l = len(used_timestamps)
    now = time.time()
    for bw in range(l):
        i = l-bw-1
        if used_timestamps[i] < now - 5 * 60 - 10:
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
        if timestamp in used_timestamps:
            return
        clear_old_timestamps()
        # Verify key
        key = data.get_user(username).get_key()
        nonce = encrypted[-24:]
        ciphertext = encrypted[(aad_size+2):(-16-24)]
        tag = encrypted[(-24-16):-24]
        cipher = ChaCha20_Poly1305.new(key=key, nonce=nonce)
        try:
            cipher.update(aad)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            used_timestamps.append(timestamp)
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
    key = data.get_user(username).get_key()
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
            raise ValueError("Client not sending correct data!")
        data.extend(part)
    return bytes(data)


try:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("0.0.0.0", 5324))
    listener.listen(1)
    print("Listening on port 5324.")
    while True:
        conn, addr = listener.accept()
        with conn:
            print(f"Connection from {addr}.")
            for _ in range(1):
                version = int.from_bytes(recieve(conn, 1), byteorder="big")
                if version != 1:
                    break
                # We can now continue with the protocol
                size = int.from_bytes(recieve(conn, 2), byteorder="big")
                # Refuse if the request is more than 1kb long
                if size > 1024:
                    break
                processed = process_encrypted_data(recieve(conn, size))
                if processed is None:
                    break
                username, request = processed
                if len(request) < 1:
                    break
                request_type = int.from_bytes(request[0:1], byteorder="big")
                try:
                    request_body = request[1:].decode("utf-8").split("\n")
                except UnicodeDecodeError:
                    break
                response = None
                user = data.get_user(username)
                try:
                    # TODO!TODO
                    conn.sendall(len(response).to_bytes(
                        2, byteorder="big"
                    ))
                    conn.sendall(response)
                except:
                    pass
finally:
    data.close()
    listener.close()
