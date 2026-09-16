import os
import time
from pathlib import Path

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
        data = ""
        for n in read_list:
            with open(read + n) as f:
                data += n
                data += "\n"
                data += f.read().strip()
                data += "\n"
        for n in read_list:
            passed = time.time() - int(n)
            if passed > (DAY * 2):
                os.remove(read + n)
        return data
    def get_upcoming_events(self):
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
                    if remaining > 0 and remaining < DAY * 7:
                        data += str(a)
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
        d[index * 2 + 1] = "true" if done else "false"
        with open(self.path + "todo", "wb") as f:
            for line in d:
                f.write(line)
                f.write(b"\n")
    def push_notification(self, name):
        unread = os.path.join(os.path.join(
            self.path + "notifications", "unread"
        ), "")
        timestamp = time.time()
        lst = os.listdir(unread)
        while str(timestamp) in lst:
            timestamp += 1
        timestamp = str(timestamp)
        with open(unread + timestamp, "wb") as f:
            f.write(name)


class DataManager:
    def __init__(self):
        if not os.path.exists(DATA_DIR):
            os.mkdir(DATA_DIR)
        elif not os.path.isfile(DATA_DIR):
            raise Exception(
                f"A file named {DATA_DIR} conflicts with the data directory!"
            )
    def get_user(self, name):
        return UserHandle(os.path.join(DATA_DIR, name))
    def close(self):
        pass

data = DataManager()

try:
    pass
finally:
    data.close()
