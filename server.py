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
    def get_key(self):
        with open(self.path + "keyfile", "rb") as f:
            d = f.read()
        return d
    def get_todo(self):
        with open(self.path + "todo", "rb") as f:
            d = f.read()
        return d
    def get_notifications(self):
        unread = os.path.join(os.path.join(
            self.path + "notifications", "unread"
        ), "")
        read = os.path.join(os.path.join(
            self.path + "notifications", "read"
        ), "")
        # Move unread to read
        for n in os.listdir(unread):
            os.rename(unread + n, read + n)
        read_list = os.listdir(read)
        data = b""
        for n in read_list:
            with open(read + n, "rb") as f:
                data += n.encode("utf-8")
                data += b"\n"
                data += f.read().strip()
                data += b"\n"
        for n in read_list:
            passed = time.time() - int(n)
            if passed > (DAY * 1):
                os.remove(read + n)
        return data
    def get_upcoming_events(self, days):
        data = b""
        now = time.time()
        with open(self.path + "events", "rb") as f:
            a = None
            for line in f:
                if a is None:
                    a = int(line.strip())
                else:
                    b = line.strip()
                    # Process the pair of lines
                    remaining = a - now
                    if remaining > 0 and remaining < DAY * days:
                        data += str(a).encode("utf-8")
                        data += b"\n"
                        data += b
                        data += b"\n"
                    # Reset for next round
                    a = None
        return data
    def get_all_events(self):
        with open(self.path + "events", "rb") as f:
            d = f.read()
        return d
    def set_key(self, k):
        with open(self.path + "keyfile", "wb") as f:
            f.write(k)
    def add_todo(self, index, name):
        d = []
        with open(self.path + "todo", "rb") as f:
            for line in f:
                if line.endswith(b"\n"):
                    l = line[:-1]
                else:
                    l = line
                if len(l) != 0:
                    d.append(line)
        index = min(index, int(len(d) // 2))
        # Pushes ones in front back so that
        # name actually comes first
        d.insert(index * 2, b"false")
        d.insert(index * 2, name.encode("utf-8"))
        with open(self.path + "todo", "wb") as f:
            for line in d:
                f.write(line)
                f.write(b"\n")
    def remove_todo(self, index):
        d = []
        with open(self.path + "todo", "rb") as f:
            for line in f:
                if line.endswith(b"\n"):
                    l = line[:-1]
                else:
                    l = line
                if len(l) != 0:
                    d.append(line)
        index = min(index, int(len(d) // 2) - 1)
        del d[index * 2]
        del d[index * 2]
        with open(self.path + "todo", "wb") as f:
            for line in d:
                f.write(line)
                f.write(b"\n")
    def modify_todo(self, index, done):
        d = []
        with open(self.path + "todo", "rb") as f:
            for line in f:
                if line.endswith(b"\n"):
                    l = line[:-1]
                else:
                    l = line
                if len(l) != 0:
                    d.append(line)
        index = min(index, int(len(d) // 2) - 1)
        d[index * 2 + 1] = b"true" if done else b"false"
        with open(self.path + "todo", "wb") as f:
            for line in d:
                f.write(line)
                f.write(b"\n")
    def push_notification(self, name):
        unread = os.path.join(os.path.join(
            self.path + "notifications", "unread"
        ), "")
        timestamp = int(time.time())
        lst = os.listdir(unread)
        while str(timestamp) in lst:
            timestamp += 1
        timestamp = str(timestamp)
        with open(unread + timestamp, "wb") as f:
            f.write(name)
    def add_event(self, timestamp, name):
        with open(self.path + "events", "rb") as f:
            d = f.read()
        if not d.endswith(b"\n"):
            d += b"\n"
        d += str(timestamp).encode("utf-8")
        d += b"\n"
        d += name
        d += b"\n"
        with open(self.path + "events", "wb") as f:
            f.write(d)
    def remove_event(self, timestamp, name):
        d = []
        with open(self.path + "events", "rb") as f:
            for line in f:
                if line.endswith(b"\n"):
                    l = line[:-1]
                else:
                    l = line
                if len(l) != 0:
                    d.append(line)
        del_id = None
        for i in range(int(len(d)//2)):
            if d[2 * i] == str(timestamp).encode("utf-8"):
                if d[2 * i + 1] == name.encode("utf-8"):
                    del_id = i
                    break
        if del_id is not None:
            del d[2 * del_id + 1]
            del d[2 * del_id]
        with open(self.path + "events", "wb") as f:
            for line in d:
                f.write(line)
                f.write(b"\n")


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
                    if request_type == 0:
                        days = int(request_body[0])
                        response = user.get_upcoming_events(days)
                    elif request_type == 1:
                        response = user.get_todo()
                    elif request_type == 2:
                        response = b""
                        index = int(request_body[0])
                        done = request_body[1] == "true"
                        user.modify_todo(index, done)
                    elif request_type == 3:
                        response = b""
                        index = int(request_body[0])
                        name = request_body[1]
                        user.add_todo(index, name)
                    elif request_type == 4:
                        response = b""
                        index = int(request_body[0])
                        user.remove_todo(index)
                    elif request_type == 5:
                        response = b""
                        timestamp = int(request_body[0])
                        name = request_body[1]
                        user.add_event(timestamp, name)
                    elif request_type == 6:
                        response = b""
                        timestamp = int(request_body[0])
                        name = request_body[1]
                        user.remove_event(timestamp, name)
                    elif request_type == 7:
                        response = b""
                        name = request_body[0]
                        user.push_notification(name)
                    elif request_type == 8:
                        response = user.get_notifications()
                    elif request_type == 9:
                        response = user.get_all_events()
                    else:
                        break
                    conn.sendall(len(response).to_bytes(
                        2, byteorder="big"
                    ))
                    conn.sendall(response)
                except:
                    pass
finally:
    data.close()
    listener.close()
