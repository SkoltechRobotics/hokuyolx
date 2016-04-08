'''Exceptions used in hokuyolx module'''
from .statuses import reply_statuses

class HokuyoException(Exception):
    '''Basic exception class for Hokuyo laser scanners'''
    pass


class HokuyoStatusException(HokuyoException):
    '''Exception class which represents unexpected reply status errors inside
    Hokuyo communication protocol'''

    code = None

    def __init__(self, code):
        super(HokuyoStatusException, self).__init__()
        self.code = code

    def get_status(self):
        '''Returns status description

        Returns
        -------
        str
            Status description
        '''
        return reply_statuses.get(self.code, 'UnknownStatus')

    def __str__(self):
        return '%s (%s)' % (self.get_status(), self.code)


class HokuyoChecksumMismatch(HokuyoException):
    '''Exception class which represents checksum mismatch errors inside Hokuyo
    communication protocol'''
    pass
