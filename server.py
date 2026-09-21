import os
import time
from pathlib import Path
import socket
from Crypto.Cipher import ChaCha20_Poly1305
from Crypto.Random import get_random_bytes

DATA_DIR = "OpenTasks_data"

DAY = 24*60*60

def check_filename(name):
    if not name.isalnum():
        raise ValueError("Invalid file name!")
    if not name.isascii():
        raise ValueError("Invalid file name!")


class UserHandle:
    def __init__(self, path):
        # So we can just use concatenation
        # on all OSs later
        self.path = os.path.join(path + "_files", "")
        self.key_path = path + "_key"
    def get_key(self):
        with open(self.key_path, "rb") as f:
            d = f.read()
        return d
    def read_file(self, name):
        check_filename(name)
        with open(self.path + name, "rb") as f:
            d = f.read()
        return d
    def read_file_section(self, name, start, size):
        check_filename(name)
        if start < 0 or size < 0:
            raise ValueError("Negative start or size!")
        with open(self.path + name, "rb") as f:
            f.seek(start, 0)
            d = f.read(size)
        return d
    def get_file_size(self, name):
        check_filename(name)
        with open(self.path + name, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
        return size
    def write_file(self, name, data):
        check_filename(name)
        with open(self.path + name, "wb") as f:
            f.write(data)
    def write_file_section(self, name, start, data):
        check_filename(name)
        if start < 0:
            raise ValueError("Start is negative!")
        with open(self.path + name, "r+b") as f:
            f.seek(start, 0)
            f.write(data)
    def append(self, name, data):
        check_filename(name)
        with open(self.path + name, "ab") as f:
            f.write(data)
    def delete_file_end(self, name, amount):
        check_filename(name)
        if amount < 0:
            raise ValueError("Amount is negative!")
        with open(self.path + name, "r+b") as f:
            f.seek(0, 2)
            if amount > f.tell():
                raise ValueError(
                    "Can't delete more than the file size!"
                )
            f.seek(-amount, 2)
            f.truncate()
    def delete(self, name):
        check_filename(name)
        os.remove(self.path + name)
    def list_files(self):
        return "\n".join(os.listdir(self.path)).encode("utf-8")
    def push_line(self, name, data):
        check_filename(name)
        with open(self.path + name, "r+b") as f:
            f.seek(0, 2)
            if f.tell() == 0:
                f.write(data)
            else:
                f.seek(-1, 2)
                if f.read(1) != b"\n":
                    f.write(b"\n")
                f.write(data)
    def pop_ending_line(self, name):
        check_filename(name)
        d = []
        with open(self.path + name, "rb") as f:
            for line in f:
                d.append(line.strip(b"\r\n"))
        if len(d) > 0:
            if len(d[-1]) == 0:
                d.pop()
            data = d.pop()
            with open(self.path + name, "wb") as f:
                for i in d:
                    f.write(i)
                    f.write(b"\n")
        else:
            data = b""
        return data
    def pop_starting_line(self, name):
        check_filename(name)
        d = []
        with open(self.path + name, "rb") as f:
            for line in f:
                d.append(line.strip(b"\r\n"))
        if len(d) > 0:
            data = d.pop(0)
            with open(self.path + name, "wb") as f:
                for i in d:
                    f.write(i)
                    f.write(b"\n")
        else:
            data = b""
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
        key = data.get_user(username).get_key()
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
                    request_body = request[1:]
                    del request # Remove unneccesary memory usage
                    # Process parameters
                    if request_type in [0, 1, 2, 6, 7, 10, 11]:
                        # Text data only and set number of lines
                        request_fields = request_body.decode("utf-8").split("\n")
                    elif request_type in [3, 5, 9]:
                        # Name, Data (Optionally Multiline)
                        i = request_body.index(b"\n")
                        request_fields = [
                            request_body[:i].decode("utf-8"),
                            request_body[(i+1):]
                        ]
                    elif request_type == 4:
                        # Name, Start, Data
                        i = request_body.index(b"\n")
                        j = request_body.index(b"\n", i+1)
                        request_fields = [
                            request_body[:i].decode("utf-8"),
                            request_body[(i+1):j].decode("utf-8"),
                            request_body[(j+1):]
                        ]
                    elif request_type == 8:
                        # None
                        request_fields = []
                    else:
                        break
                except UnicodeDecodeError:
                    break
                except ValueError:
                    break
                except IndexError:
                    break
                # Process request
                response = None
                user = data.get_user(username)
                try:
                    if request_type == 0:
                        response = user.read_file(request_fields[0])
                    elif request_type == 1:
                        response = user.read_file_section(
                            request_fields[0],
                            int(request_fields[1]),
                            int(request_fields[2])
                        )
                    elif request_type == 2:
                        response = str(user.get_file_size(request_fields[0])).encode("utf-8")
                    elif request_type == 3:
                        user.write_file(request_fields[0], request_fields[1])
                        response = b""
                    elif request_type == 4:
                        user.write_file_section(
                            request_fields[0],
                            int(request_fields[1]),
                            request_fields[2]
                        )
                        response = b""
                    elif request_type == 5:
                        user.append(request_fields[0], request_fields[1])
                        response = b""
                    elif request_type == 6:
                        user.delete_file_end(
                            request_fields[0],
                            int(request_fields[1])
                        )
                        response = b""
                    elif request_type == 7:
                        user.delete(request_fields[0])
                        response = b""
                    elif request_type == 8:
                        response = user.list_files()
                    elif request_type == 9:
                        user.push_line(request_fields[0], request_fields[1])
                        response = b""
                    elif request_type == 10:
                        response = user.pop_ending_line(request_fields[0])
                    elif request_type == 11:
                        response = user.pop_starting_line(request_fields[0])
                    else:
                        break
                    response = encrypt_data(response, username)
                    conn.sendall(len(response).to_bytes(
                        2, byteorder="big"
                    ))
                    conn.sendall(response)
                except:
                    pass
finally:
    data.close()
    listener.close()
