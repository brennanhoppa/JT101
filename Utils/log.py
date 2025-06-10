def log(msg, queue):
    queue.put(str(msg))