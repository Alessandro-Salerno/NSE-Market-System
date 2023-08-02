class MComSendException(Exception):
    def __init__(self, message_size: int, header_size: int, sent_bytes: int, *args: object) -> None:
        super().__init__(f'Could only send {sent_bytes} byte(s) of {message_size + header_size} byte(s) with header of size {header_size} byte(s)')
        self.message_size = message_size
        self.header_size = header_size
        self.total_size = message_size + header_size
        self.sent_bytes = sent_bytes
