'''HokuyoLX class code'''
import socket
import logging
import time
import numpy as np
from codecs import encode, decode
from .exceptions import HokuyoException, HokuyoStatusException
from .exceptions import HokuyoChecksumMismatch
from .statuses import activation_statuses, laser_states, tsync_statuses

class HokuyoLX(object):
    '''Class for working with Hokuyo laser rangefinders, specifically
    with the following models: UST-10LX, UST-20LX, UST-30LX'''

    addr = ('192.168.0.10', 10940) #: IP address and port of the scanner
    dmin = 20 #: Minimum measurable distance (in millimeters)
    dmax = 30000 #: Maximum measurable distance (in millimeters)
    ares = 1440 #: Angular resolution (number of partitions in 360 degrees)
    amin = 0 #: Minimum step number of the scanning area
    amax = 1080 #: Maximum step number of the scanning area
    aforw = 540 #: Step number of the front direction
    scan_freq = 40 #: Scanning frequency in Hz
    model = 'UST-10LX' #: Sensor model
    tzero = 0 #: Sensor start time
    tn = 0 #: Sensor timestamp overflow counter
    convert_time = True #: To convert timestamps to UNIX time or not?

    _sock = None #: TCP connection socket to the sensor
    _logger = None #: Logger instance for performing logging operations

    def __init__(self, activate=True, info=True, tsync=True, addr=None,
                 buf=512, timeout=5, time_tolerance=300, logger=None,
                 convert_time=True):
        '''Creates new object for communications with the sensor.

        Parameters
        ----------
        activate : bool, optional
            Switch sensor to the standby mode? (the default is True)
        info : bool, optional
            Update sensor information? (the default is True)
        tsync : bool, optional
            Perform time synchronization? (the default is True)
        addr : tuple, optional
            IP address and port of the sensor (the default is
            `('192.168.0.10', 10940)`)
        buf : int, optional
            Buffer size for recieving messages from the sensor
            (the default is 512)
        timeout : int, optional
            Timeout limit for connection with the sensor in seconds
            (the default is 5)
        time_tolerance : int, optinal
            Time tolerance before attempting time synchronization in
            milliseconds (the default is 300)
        logger : `logging._logger` instance, optional
            Logger instance, if none is provided new instance is created
        convert_time : bool
            Convert timestamps to UNIX time?
        '''
        super(HokuyoLX, self).__init__()
        if addr is not None:
            self.addr = addr
        self.buf = buf
        self.timeout = timeout
        self._logger = logging.getLogger('hokuyo') if logger is None else logger
        self.time_tolerance = time_tolerance
        self._connect_to_laser(False)
        if tsync:
            self.time_sync()
        if info:
            self.update_info()
        if activate:
            self.activate()

    #Low-level data converting and checking

    @staticmethod
    def _check_sum(msg, cc=None):
        '''Checks the checkusum inside the given message or if `cc` is provided
        checks it for the given message. Returns message without checksum byte
        '''
        if cc is None:
            cmsg, cc = msg[:-1], msg[-1:]
        else:
            cmsg = msg
        conv_msg = cmsg if isinstance(cmsg, bytes) else encode(cmsg, 'ascii')
        conv_sum = decode(cc, 'ascii') if isinstance(msg, bytes) else cc
        calc_sum = chr((sum(bytearray(conv_msg)) & 0x3f) + 0x30)
        if calc_sum != conv_sum:
            raise HokuyoChecksumMismatch(
                'For message %s sum mismatch: %s vs %s' %
                (decode(conv_msg, 'ascii'), calc_sum, cc))
        return cmsg

    @staticmethod
    def _convert2int(chars):
        '''Converts given byte chars to integer using 6 bit encoding'''
        return sum([(ord(char) - 0x30) << (6*(len(chars) - i - 1))
                    for i, char in enumerate(chars)])

    def _convert2ts(self, chars, convert=None):
        '''Converts sensor timestamp in the form of chars to
        the UNIX timestamp. If resulting timestamp differs from local timestamp
        to more than `self.time_tolerance` performs time syncronization or
        detects sensor timestamp overflow and adjiusts to it.'''
        ts = self._convert2int(self._check_sum(chars))
        if not (self.convert_time if convert is None else convert):
            return ts
        logging.debug('Sensor timestamp: %d', ts)
        t = self.tzero + ts + self._tn*(1 << 24)
        logging.debug('Converted timestamp: %d (t0: %d, tn: %d)',
            t, self.tzero, self._tn)
        dt = int(time.time()*1000) - t
        logging.debug('Delta t with local time: %d', dt)
        if abs(dt) > self.time_tolerance:
            diff = (1 << 24) - self.time_tolerance
            if dt > diff and self.tzero != 0:
                self._logger.warning('Timestamp overflow detected, '
                                    '%d -- %d' % (dt, diff))
                self._tn += 1
            else:
                self._logger.warning(
                    'Time difference %d is too big. Resyncing...',  dt)
                self.time_sync()
            return self._convert2ts(chars)
        return t

    #: Low level connection methods

    def _connect_to_laser(self, close=True):
        '''Connects to the sensor using parameters stored inide object'''
        if close:
            self.close()
        self._logger.info('Connecting to the laser')
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect(self.addr)
        except socket.timeout:
            raise HokuyoException('Failed to connect to the sensor')

    def _send_cmd(self, cmd, params='', string=''):
        '''Sends given command to the sensor'''
        if not (len(cmd) == 2 or (cmd[0] == '%' and len(cmd) == 3)):
            raise HokuyoException(
                'Command must be two chars string '
                'or three chars starting with %%, got %d chars' % len(cmd))
        self._logger.debug(
            'Sending command to the sensor; '
            'cmd: %s, params: %s, string: %s', cmd, params, string)
        req = cmd + params
        if string:
            req += ';' + string
        if self._sock is None:
            raise HokuyoException('Not connected to the laser')
        n = self._sock.send(encode(req, 'ascii') + b'\n')
        if len(req) + 1 != n:
            raise HokuyoException('Failed to send all data to the sensor')
        return req

    def _recv(self, header=None):
        '''Recieves data from the sensor and checks recieved data block
        using given header.'''
        self._logger.debug('Recieving data from sensor')
        if self._sock is None:
            raise HokuyoException('Not connected to the laser')
        try:
            while True:
                data = b''
                while not data.endswith(b'\n\n'):
                    data += self._sock.recv(self.buf)
                self._logger.debug('Recieved data: %s' % data)
                split_data = decode(data[:-2], 'ascii').split('\n')
                if header is not None and split_data[0] != header:
                    self._logger.warning(
                        'Discarded data due header mismatch: %s' % data)
                    continue
                break
        except socket.timeout:
            raise HokuyoException('Connection timeout')
        return split_data

    def _send_req(self, cmd, params='', string=''):
        '''Sends given command to the sensor and awaits response to it.'''
        self._logger.debug(
            'Performing request; cmd: %s, params: %s, string: %s',
            cmd, params, string)
        header = self._send_cmd(cmd, params, string)
        resp = self._recv(header)
        if resp.pop(0) != header:
            raise HokuyoException('Response header mismatch')
        q = resp.pop(0)
        status = self._check_sum(q)
        self._logger.debug('Got response with status %s', status)
        return status, resp

    #Processing and filtering scan data

    def get_angles(self, start=None, end=None, grouping=0):
        '''Returns array of angles for given `start`, `end` and `grouping`
        parameters and according to the sensor parameters stored inside object.

        Parameters
        ----------
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)

        Returns
        -------
        ndarray
            List of angles in radians

        Examples
        --------
        >>> laser.get_angles()
        array([-1.17809725, -1.17591558, -1.17373392, ...,  1.17373392,
            1.17591558,  1.17809725])
        '''
        start = self.amin if start is None else start
        end = self.amax if end is None else end
        grouping = 1 if grouping == 0 else grouping

        num = self.amax - self.amin + 1
        space = np.linspace(self.amin, self.amax, num) - self.aforw
        angles = 2*np.pi*space/self.ares
        # TODO remake grouping
        return angles[start:end+1:grouping]

    def _process_scan_data(self, data, with_intensity):
        '''Converts raw scan data into ndarray with neccecary shape'''
        raw_data = ''.join([self._check_sum(block) for block in data])
        if len(raw_data) % 3 != 0:
            raise HokuyoException('Wrong length of scan data')
        scan = np.array([
            self._convert2int(raw_data[3*i:3*i+3])
            for i in range(len(raw_data)//3)], np.uint32)
        if with_intensity:
            return scan.reshape((len(scan)//2, 2))
        return scan

    def _filter(self, scan, start=None, end=None, grouping=0,
                dmin=None, dmax=None, imin=None, imax=None):
        '''Filters scan measured for given parameters and filters it for
        given `dmin`, `dmax`, `imin` and `imax`. Note that `imin` and `imax`
        should be only used for scans with intensities'''
        angles = self.get_angles(start, end, grouping)
        if scan.ndim == 1:
            tpl = (angles, scan)
        elif scan.ndim == 2:
            tpl = (angles, scan[:, 0], scan[:, 1])
        else:
            raise HokuyoException('Unexpected scan dimensions')
        data = np.vstack(tpl).T
        dmin = self.dmin if dmin is None else dmin
        dmax = self.dmax if dmax is None else dmax
        data = data[(data[:, 1] >= dmin) & (data[:, 1] <= dmax)]
        if imin is not None:
            data = data[data[:, 2] >= imin]
        if imax is not None:
            data = data[data[:, 2] <= imax]
        return data

    #Control of sensor state

    def _force_standby(self):
        '''Forces standby state, if it unable to do it throws execption'''
        state, description = self.laser_state()
        if state in (3, 4, 5):
            self.standby()
        elif state == 2:
            self.tsync_exit()
        elif state != 0:
            raise HokuyoException('Unexpected laser state: %s' % description)

    def activate(self):
        '''Switches the sensor to the measurement state and starts
        the measurement process by lighting (activating) the laser.
        Valid in the standby state.

        Returns
        -------
        code : int
            Command status code
        description : str
            Command status description


        Examples
        --------
        >>> laser.laser_state()
        (0, 'Standby state')
        >>> status, description = laser.activate()
        >>> status
        0
        >>> description
        'Normal. The sensor is in measurement state and the laser was lighted.'
        >>> laser.laser_state()
        (3, 'Single scan state')
        '''
        self._logger.info('Activating sensor')
        status, _ = self._send_req('BM')
        if status not in activation_statuses:
            raise HokuyoStatusException(status)
        return int(status), activation_statuses[status]

    def standby(self):
        '''Stops the current measurement process and switches the sensor to the
        standby state. Valid in the measurement state or in the measurement and
        scan response state.

        Examples
        --------
        >>> laser.laser_state()
        (3, 'Single scan state')
        >>> laser.standby()
        >>> laser.laser_state()
        (0, 'Standby state')
        '''
        self._logger.info('Switching sensor to the standby state')
        status, _ = self._send_req('QT')
        if status != '00':
            raise HokuyoStatusException(status)

    def sleep(self):
        '''Switches the sensor to the sleep state.  When the sensor receives
        the sleep command, it stops the current measurement process,
        switches to the sleep state, turns off (deactivates) the laser and
        stops the motor. Valid in the standby state or in the
        measurement state.

        Examples
        --------
        >>> laser.laser_state()
        (0, 'Standby state')
        >>> laser.sleep()
        >>> laser.laser_state()
        (5, 'Sleep state')
        '''
        self._logger.info('Switching sensor to the sleep state')
        self._force_standby()
        status, _ = self._send_req('%SL')
        if status != '00':
            raise HokuyoStatusException(status)

    #Single measurments

    def _single_measurment(self, with_intensity, start, end, grouping):
        '''Generic function for taking single measurment.
        Valid only in the measurment state.'''
        start = self.amin if start is None else start
        end = self.amax if end is None else end
        params = '%0.4d%0.4d%0.2d' % (start, end, grouping)
        cmd = 'GE' if with_intensity else 'GD'
        status, data = self._send_req(cmd, params)
        if status != '00':
            raise HokuyoStatusException(status)
        timestamp = self._convert2ts(data.pop(0))
        scan = self._process_scan_data(data, with_intensity)
        return timestamp, scan

    def get_dist(self, start=None, end=None, grouping=0):
        '''Measure distances for the given parameters

        Parameters
        ----------
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)

        Returns
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured distances
        '''
        return self._single_measurment(False, start, end, grouping)

    def get_intens(self, start=None, end=None, grouping=0):
        '''Measure distances and intensities for the given parameters

        Parameters
        ----------
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)

        Returns
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured distances and intensities
        '''
        return self._single_measurment(True, start, end, grouping)

    def get_filtered_dist(self, start=None, end=None, grouping=0,
                          dmin=None, dmax=None):
        '''Measure distances for the given parameters and perform basic
        filtering. Returns array with angles and distances.

        Parameters
        ----------
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)
        dmin : int, optional
            Minimal distance for filtering (the default is None,
            which implies `self.dmin`)
        dmax : int,  optional
            Maximum distance for filtering (the default is None,
            which implies `self.dmax`)

        Returns
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured distances and angles
        '''
        ts, scan = self.get_dist(start, end, grouping)
        return ts, self._filter(scan, start, end, grouping, dmin, dmax)

    def get_filtered_intens(self, start=None, end=None, grouping=0,
                            dmin=None, dmax=None, imin=None, imax=None):
        '''Measure distances and intensities for the given parameters and
        perform basic filtering. Returns array with angles, distances and
        intensities.

        Parameters
        ----------
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)
        dmin : int, optional
            Minimum distance for filtering (the default is None,
            which implies `self.dmin`)
        dmax : int,  optional
            Maximum distance for filtering (the default is None,
            which implies `self.dmax`)
        imin : int, optional
            Minimum intensity for filtering (the default is None,
            which disables minimum intensity filter)
        imax : int,  optional
            Maximum distance for filtering (the default is None,
            which disables maximum intensity filter)

        Returns
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured angles, distances and intensities
        '''
        ts, scan = self.get_intens(start, end, grouping)
        return ts, self._filter(scan, start, end, grouping,
                                dmin, dmax, imin, imax)

    #Continous measurments

    def _iter_meas(self, with_intensity, scans, start, end, grouping, skips):
        '''Generic generator for taking continous measurment. If `scan` is
        equal to 0 infinite number of scans will be taken until laser is
        switched to the standby state.'''
        self._logger.info('Initializing continous measurment')
        start = self.amin if start is None else start
        end = self.amax if end is None else end
        params = '%0.4d%0.4d%0.2d%0.1d%0.2d' % (start, end, grouping,
                                                skips, scans)
        cmd = 'ME' if with_intensity else 'MD'
        status, _ = self._send_req(cmd, params)
        if status != '00':
            raise HokuyoStatusException(status)
        self._logger.info('Starting scan response cycle')
        while True:
            data = self._recv()
            self._logger.debug('Recieved data in the scan response cycle: %s' %
                              data)
            header = data.pop(0)
            # TODO add string part check for header
            req = cmd + params[:-2]
            if not header.startswith(req):
                raise HokuyoException('Header mismatch in the scan '
                                      'response message')
            pending = int(header[len(req):len(req) + 2])

            status = self._check_sum(data.pop(0))
            if status == '0M':
                self._logger.warning('Unstable scanner condition')
                continue
            elif status != '99':
                raise HokuyoStatusException(status)
            timestamp = self._convert2ts(data.pop(0))

            scan = self._process_scan_data(data, with_intensity)
            self._logger.info('Got new scan, yielding...')
            yield (scan, timestamp, pending)

            if pending == 0 and scans != 0:
                self._logger.info('Last scan recieved, exiting generator')
                break

    def iter_dist(self, scans=0, start=None, end=None, grouping=0, skips=0):
        '''Generator for taking continous measurment of distances. If `scan` is
        equal to 0 infinite number of scans will be taken until laser is
        switched to the standby state.

        Parameters
        ----------
        scans : int, optional
            Number of scans to perform (the default is 0, which means infinite
            number of scans)
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)
        skips : int, optional
            Number of scans to skip (the default is 0, 0 means all scans
            will be yielded, 1 - every second, 2 - every third, etc.)

        Yields
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured distances
        '''
        return self._iter_meas(False, scans, start, end, grouping, skips)

    def iter_intens(self, scans=0, start=None, end=None, grouping=0, skips=0):
        '''Generator for taking continous measurment of distances and
        intensities. If `scan` is equal to 0 infinite number of scans will be
        taken until laser is switched to the standby state.

        Parameters
        ----------
        scans : int, optional
            Number of scans to perform (the default is 0, which means infinite
            number of scans)
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)
        skips : int, optional
            Number of scans to skip (the default is 0, 0 means all scans
            will be yielded, 1 - every second, 2 - every third, etc.)

        Yields
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured distances and intensities
        '''
        return self._iter_meas(True, scans, start, end, grouping, skips)

    def iter_filtered_dist(self, scans=0, start=None, end=None, grouping=0,
                           skips=0, dmin=None, dmax=None):
        '''Generator for taking continous measurment of distances with
        additional filtering. If `scan` is equal to 0 infinite number of scans
        will be taken until laser is switched to the standby state.

        Parameters
        ----------
        with_intensity : bool
            Measure with intensities or only distances
        scans : int, optional
            Number of scans to perform (the default is 0, which means infinite
            number of scans)
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)
        skips : int, optional
            Number of scans to skip (the default is 0, 0 means all scans
            will be yielded, 1 - every second, 2 - every third, etc.)
        dmin : int, optional
            Minimal distance for filtering (the default is None,
            which implies `self.dmin`)
        dmax : int,  optional
            Maximum distance for filtering (the default is None,
            which implies `self.dmax`)

        Yields
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured angles and distances
        '''
        gen = self.iter_dist(scans, start, end, grouping, skips)
        for scan, timestamp, pending in gen:
            scan = self._filter(scan, start, end, grouping, dmin, dmax)
            yield (scan, timestamp, pending)

    def iter_filtered_intens(self, scans=0, start=None, end=None, grouping=0,
                             skips=0, dmin=None, dmax=None,
                             imin=None, imax=None):
        '''Generator for taking continous measurment of distances and
        intensities with additional filtering. If `scan` is equal to 0 infinite
        number of scans will be taken until laser is switched to the standby
        state.

        Parameters
        ----------
        with_intensity : bool
            Measure with intensities or only distances
        scans : int, optional
            Number of scans to perform (the default is 0, which means infinite
            number of scans)
        start : int, optional
            Position of the starting step (the default is None,
            which implies `self.amin`)
        end : int, optional
            Position of the ending step (the default is None,
            which implies `self.amax`)
        grouping : int, optional
            Number of grouped steps (the default is 0, which regarded as 1)
        skips : int, optional
            Number of scans to skip (the default is 0, 0 means all scans
            will be yielded, 1 - every second, 2 - every third, etc.)
        dmin : int, optional
            Minimal distance for filtering (the default is None,
            which implies `self.dmin`)
        dmax : int,  optional
            Maximum distance for filtering (the default is None,
            which implies `self.dmax`)
        imin : int, optional
            Minimum intensity for filtering (the default is None,
            which disables minimum intensity filter)
        imax : int,  optional
            Maximum distance for filtering (the default is None,
            which disables maximum intensity filter)

        Yields
        -------
        timestamp : int
            Timestamp of the measurment
        scan : ndarray
            Array with measured angles, distances and intensities
        '''
        gen = self.iter_intens(scans, start, end, grouping, skips)
        for scan, timestamp, pending in gen:
            scan = self._filter(scan, start, end, grouping,
                                dmin, dmax, imin, imax)
            yield (scan, timestamp, pending)

    #Time synchronization methods

    def _tsync_cmd(self, code):
        ''' Sends time synchronization command with the given code

        Parameters
        ----------
        code : int
            Time synchronization command, one of: 0, 1, 2

        Returns
        -------
        status : str
            Status code of the executed command
        description : str
            Status description of the executed command
        '''
        status, data = self._send_req('TM', str(code))
        if status not in tsync_statuses:
            raise HokuyoStatusException(status)
        if data:
            return status, tsync_statuses[status], data[0]
        else:
            return status, tsync_statuses[status]

    def tsync_enter(self):
        '''Transition from standby state to time synchronization state.'''
        self._logger.info('Entering time sync mode')
        return self._tsync_cmd(0)

    def tsync_get(self):
        '''Get time value for time synchronization'''
        resp = self._tsync_cmd(1)
        if resp[0] != '00':
            raise HokuyoException(
                'Failed to get sensor time: %s (%s)' %
                (resp[1], resp[0]))
        return self._convert2ts(resp[2], False)

    def tsync_exit(self):
        '''Transition from time synchronization state to standby state.'''
        self._logger.info('Exiting time sync mode')
        return self._tsync_cmd(2)

    def time_sync(self, N=10, dt=0.1):
        '''Performs time synchronization by doing `tsync_get`requests each `dt`
        seconds N times. After that it finds mean time shift, saving it into
        `self.tzero`. This value also can be interpreted as the time when
        the sensor was turned in.

        Parameters
        ----------
        N : int, optional
            Number of times to request time from the sensor (the default is 10)
        dt : float, optional
            Time between time requests (the default is 0.1)
        '''
        self._logger.info('Starting time synchronization.')
        self._force_standby()
        code, description = self.tsync_enter()
        if code != '00':
            self._logger.info(
                'Failed to enter time sync mode: %s (%s)' %
                (description, code))

        self._logger.info('Collecting timestamps...')
        tzero_list = []
        for _ in range(N):
            tzero_list.append(time.time()*1000 - self.tsync_get())
            time.sleep(dt)
        self.tzero = int(np.mean(np.rint(np.array(tzero_list))))
        self._tn = 0

        self._logger.info('Time sync done, t0: %d ms' % self.tzero)

        code, description = self.tsync_exit()
        if code != '00':
            self._logger.info(
                'Failed to exit time sync mode: %s (%s)' %
                (description, code))

    #Sensor information

    def _process_info_line(self, line):
        '''Processes one line in response on info request and returns processed
        key and value from with line

        Parameters
        ----------
        line : str
            Line of format '<key>:<value>;<checksum>'

        Returns
        -------
        key : str
            Information key
        value : str, int
            Imformation value (converted to int if doable)
        '''
        key, value = self._check_sum(line[:-2], line[-1:]).split(':')
        return key, int(value) if value.isdigit() else value

    def _get_info(self, cmd):
        '''Generic method for recieving and decoding sensor information,
        accepts the following commands: II, VV and PP'''
        status, data = self._send_req(cmd)
        if status != '00':
            raise HokuyoStatusException(status)
        return dict(self._process_info_line(line) for line in data if line)

    def sensor_state(self):
        '''Obtains status information of the sensor.
        This command is valid during any sensor state.'''
        self._logger.info('Retrieving sensor state')
        return self._get_info('II')

    def version(self):
        '''Obtains manufacturing (version) information of the sensor.
        This command is valid during any sensor state.'''
        self._logger.info('Retrieving manufacturing information of the sensor')
        return self._get_info('VV')

    def sensor_parameters(self):
        '''Obtains sensor internal parameters information.
        The `sensor_parameters` command is valid during any sensor state except
        during the time synchronization state.'''
        self._logger.info('Retrieving sensor internal parameters')
        return self._get_info('PP')

    def laser_state(self):
        '''Return the current sensor state. It is valid during any sensor state.

        Returns
        -------
        int
            Sensor state code
        str
            Sensor state description
        '''
        status, data = self._send_req('%ST')
        if status != '00':
            raise HokuyoStatusException(status)
        state = data[0]
        if state not in laser_states:
            raise HokuyoException('Unknown laser state code: %s' % state)
        return int(state), laser_states[state]

    def update_info(self):
        '''Updates sensor information stored inside object using
        `sensor_parameters` method.'''
        self._logger.info('Updating sensor information')
        params = self.sensor_parameters()
        for key in ['dmin', 'dmax', 'ares', 'amin', 'amax', ]:
            if key.upper() in params:
                self.__dict__[key] = params[key.upper()]
        sfreq = params['SCAN']
        self.scan_freq = sfreq//60 if sfreq % 60 == 0 else sfreq/60
        self.aforw = params['AFRT']
        self.model = params['MODL']

    #Service methods

    def reset(self):
        '''This command forces the sensor to switch to the standby state
        and performs the following tasks:

        1. Turns off (deactivates) the laser.
        2. Sets the motor rotational speed (scanning speed) to the default
           initialization value.
        3. Sets the serial transmission speed (bit rate) to the default
           initialization value.
        4. Sets the internal sensor timer to zero.
        5. Sets the measurement sensitivity to the default (normal) value.

        However, when the sensor is in the abnormal condition state,
        the `reset` command is not received.
        '''
        self._logger.info('Performing sensor reset')
        status, _ = self._send_req('RS')
        if status != '00':
            raise HokuyoStatusException(status)
        self._logger.info('Finished reset')

    def partial_reset(self):
        '''This command forces the sensor to switch to the standby state
        and performs the following tasks:

        1. Turns off (deactivates) the laser.
        2. Sets the internal sensor timer to zero.
        3. Sets the measurement sensitivity to the default (normal) value.

        This is similar to the `reset` command, except the motor rotational
        (scanning) speed and the serial transmission speed are not changed.
        When the sensor is in the abnormal condition state, the `partial_reset`
        command is not received.
        '''
        self._logger.info('Performing partial sensor reset')
        status, _ = self._send_req('RT')
        if status != '00':
            raise HokuyoStatusException(status)
        self._logger.info('Finished partial reset')

    def reboot(self):
        '''This command reboots the sensor and performs the following tasks:

        1. Waits for 1 second, during this time the host system disconnects
           from the sensor.
        2. The sensor stops all communications.
        3. Turns off (deactivates) the laser.
        4. Sets the motor rotational speed (scanning speed) to the default
           initialization value.
        5. Sets the serial transmission speed (bit rate) to the default
           initialization value.
        6. Sets the internal sensor timer to zero.
        7. Sets the measurement sensitivity to the default (normal) value.
        8. Initializes other internal parameters, and waits until the
           scanning speed is stable.
        9. Switches to standby state.

        `reboot` is the only state transition command that can be received
        during abnormal condition state
        '''
        self._logger.info('Reboot: sending first reboot command')
        status, _ = self._send_req('RB')
        if status != '01':
            raise HokuyoException('Reboot failed on first step '
                                  'recieved status %s not 01' % status)

        self._logger.info('Reboot: done first step, sending '
                         'second reboot command')
        status, _ = self._send_req('RB')
        if status != '00':
            raise HokuyoException('Reboot failed on second step '
                                  'recieved status %s not 00' % status)
        self._logger.info('Reboot: second step successful')

    def close(self):
        '''Disconnects from the sensor closing TCP socket'''
        if self._sock is None:
            self._logger.info('Close: socket already closed')
            return
        self._logger.info('Close: closing connection to sensor')
        self._sock.close()
        self._sock = None
