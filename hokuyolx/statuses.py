'''Various statuses, their codes and descriptions used in the hokuyolx'''

#: Reply statuses for `activate()` command
activation_statuses = {
    '00': 'Normal. The sensor is in measurement state and the laser '
          'was lighted.',
    '01': 'The laser was not lighted due to unstable or abnormal condition.',
    '02': 'The sensor is already in measurement state and '
          'the laser is already lighted.',
}

#: Laser states
laser_states = {
    '000': 'Standby state',
    '100': 'From standby to unstable state',
    '001': 'Booting state',
    '002': 'Time adjustment state',
    '102': 'From time adjustment to unstable state',
    '003': 'Single scan state',
    '103': 'From single scan to unstable state',
    '004': 'Multi scan state',
    '104': 'From multi scan to unstable state',
    '005': 'Sleep state',
    '006': 'Waking-up state (Recovering from sleep state)',
    '900': 'Error detected state',
}

#: Tyme synchronization commands statuses
tsync_statuses = {
    '00': 'Normal',
    '01': 'Invalid parameter (control code).',
    '02': 'TM0 request was received and the sensor already is in time '
          'synchronization state.',
    '03': 'TM2 request was received and the sensor already left the time '
          'synchronization state.',
    '04': 'TM1 request was received and the sensor is not in time '
          'synchronization state.',
}

#: Other reply statuses, usually meaning some sort of exception
reply_statuses = {
    '0L': 'AbnormalState',
    '0M': 'Unstable',
    '0E': 'CommandNotDefined',
    '0F': 'CommandNotSupported',
    '10': 'Denied',
    '0G': 'UserStringLong',
    '0H': 'CommandShort',
    '0D': 'CommandLong',
}