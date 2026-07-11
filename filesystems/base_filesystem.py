class BaseFileSystem:
    def __init__(self, disk):
        self.disk = disk

    def create_file(self, name, size_bytes):
        raise NotImplementedError

    def write_file(self, name, data):
        raise NotImplementedError

    def read_file(self, name):
        raise NotImplementedError

    def delete_file(self, name):
        raise NotImplementedError

    def list_files(self):
        raise NotImplementedError

    def info(self):
        raise NotImplementedError

    def close(self):
        self.disk.close()