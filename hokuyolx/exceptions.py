'''Exceptions used in hokuyolx module'''

class HokuyoException(Exception):
    '''Basic exception class for Hokuyo laser scanners'''
    pass


class HokuyoStatusException(HokuyoException):
    '''Exception class which represents unexpected reply status errors inside
    Hokuyo communication protocol'''
    _statuses = {
        '0L': 'AbnormalState',
        '0M': 'Unstable',
        '0E': 'CommandNotDefined',
        '0F': 'CommandNotSupported',
        '10': 'Denied',
        '0G': 'UserStringLong',
        '0H': 'CommandShort',
        '0D': 'CommandLong',
    }
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
        return self._statuses.get(self.code, 'UnknownStatus')

    def __str__(self):
        return '%s (%s)' % (self.get_status(), self.code)


class HokuyoChecksumMismatch(HokuyoException):
    '''Exception class which represents checksum mismatch errors inside Hokuyo
    communication protocol'''
    pass
