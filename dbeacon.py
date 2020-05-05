#!/usr/bin/python

import beacon
import struct
import uuid
import collections

INTERACTION_ID_DLR = 0x0002
INTERACTION_ID_WDW = 0x0003

MFG_ID_DISNEY = 0x0183

SHOWCONTROL_READY_FOR_REQUEST = 1
SHOWCONTROL_SUCCESS = 2
SHOWCONTROL_RUNNING = 3
SHOWCONTROL_RESETTING = 4
SHOWCONTROL_REQUEST_DATA_ONE = 5
SHOWCONTROL_REQUEST_DATA_ALL = 6
SHOWCONTROL_REQUEST_DENIED = 7
SHOWCONTROL_REQUEST_PENDING = 8
SHOWCONTROL_READY_TO_TRIGGER = 9
SHOWCONTROL_PREPARE_FOR_CONNECT = 16
SHOWCONTROL_TIMEOUT = 17
SHOWCONTROL_NEEDS_PLAYERS = 18

AFFILIATION_SCOUNDREL = 0
AFFILIATION_RESISTANCE = 1
AFFILIATION_FIRST_ORDER = 2

affiliation = [
    'Scoundrel',
    'Resistance',
    'First Order',
]

PERSONALITY_R_SERIES = 1
PERSONALITY_BB_SERIES = 2
PERSONALITY_BLUE = 3
PERSONALITY_GRAY = 4
PERSONALITY_RED = 5
PERSONALITY_ORANGE = 6
PERSONALITY_PURPLE = 7
PERSONALITY_BLACK = 8

personality = [
    None,
    'R-Series',
    'BB-Series',
    'Blue',
    'Gray',
    'Red',
    'Orange',
    'Purple',
    'Black',
]

DROID_DEPOT_ACTIVATE_PAIR = 1
DROID_DEPOT_ACTIVATE_GO = 2

def parse(mfd):
    ret = {}
    while len(mfd) > 1:
        hdr, mfd = mfd[:2], mfd[2:]
        id, length = struct.unpack('>BB', hdr)
        if length > len(mfd):
            break
        subdata, mfd = mfd[:length], mfd[length:]
        args = {'sub_id': id, 'sub_len': length, 'sub_data': None}
        if id == 0x03:
            for key in ['droid_id', 'rssi', 'bay', 'action78', 'battery_low', 'personalityChip', 'affiliation', 'paired']:
                args[key] = None
            if length >= 4:
                args['droid_id'], byte3, byte4, byte5 = struct.unpack('>BBBB', subdata[:4])
                args['personalityChip'] = byte5 | ((byte4 & 1) << 8)
                args['affiliation'] = (byte4 >> 2) & 0x7
                args['paired'] = (byte3 & 0x80) != 0
            if length >= 5:
                byte6, = struct.unpack('>B', subdata[4:5])
                args['bay'] = byte6 & 0xf
                args['action78'] = (byte6 & 0x10) != 0
                args['battery_low'] = (byte6 & 0x80) != 0
            if length >= 6:
                args['rssi'], = struct.unpack('>B', subdata[5:6])
                args['rssi'] = args['rssi'] - 256
        else:
            args['sub_data'] = subdata
        ret[id] = args
    return ret

class dBeacon(beacon.Advertisement):
    def __init__(self, manager, index):
        beacon.Advertisement.__init__(self, manager, index, 'peripheral')
        self.interactionId = INTERACTION_ID_DLR
        self.has_interactionId = set()
        self.add_discoverable(True)
        self.add_discoverable_to(1000)
        self.include_tx_power = True
        self.advdata = collections.OrderedDict()
        self.advdataraw = b''
        self.power = -59

    def set_power(self, power):
        if power != self.power:
            self.power = power
            self.refresh_advadata()

    def set_interactionId(self, interactionId):
        if interactionId != self.interactionId:
            self.interactionId = interactionId
            dirty = False
            for key, value in self.advdata.items():
                if key in self.has_interactionId:
                    value = value[0] + struct.pack('>H', interactionId) + value[3:]
                    self.advdata[key] = value
                    dirty = True
            if dirty:
                self.refresh_advdata()

    def refresh_advdata(self):
        self.advdataraw = b''
        for data in self.advdata.values():
            self.advdataraw += data
        power = (256 + self.power) & 0xff
        self.add_manufacturer_data(MFG_ID_DISNEY, struct.pack('<22sB', self.advdataraw, power))
        self.refresh()

    def add_subtype(self, subtype, subdata):
        print(f'{subtype}={subdata}')
        data = struct.pack('<BB', subtype, len(subdata)) + subdata
        length = len(data) + len(self.advdataraw)
        if subtype in self.advdata:
            length -= len(self.advdata[subtype])
        if length > 22:
            raise Exception('Data too large')
        self.advdata[subtype] = data
        self.refresh_advdata()

    def remove_subtype(self, subtype):
        if subtype in self.advdata:
            del self.advdata[subtype]
            self.refresh_advdata()

    def remove_all(self):
        if self.advdata:
            self.advdata = collections.OrderedDict()
            self.refresh_advdata()

    def add_droid(self, affiliation, personalityChip, paired=True):
        '''
        Droid advertisement

        Sent by each droid. Receiving droids play reaction sequence based
        on sending droid's affiliation and receiving droid's installed
        personality chip. Unpaired droids are ignored. Droids respond to another
        droid every 117.6s, but only if they have not seen a droid location
        beacon in 2hr.

        :param int affiliation: Droid affiliation. 0-2.
        :param int personalityChip: Installed personality chip. 1-8.
        :param bool paired: True if droid has finished pairing sequence
        '''
        byte3 = 0x01
        if paired:
            byte3 |= 0x80
        byte4 = (4 << 5) | (affiliation << 2) | ((personalityChip >> 8) & 1)
        byte5 = personalityChip & 0xff

        self.add_subtype(0x03, struct.pack('<BBBB', 0x44, byte3, byte4, byte5))

    def add_droid_extended(self, affiliation, personalityChip, paired, battery_low, action78, bay, rssi):
        '''
        Extended droid advertisement

        Sent by droids in test mode or that are not paired and received a
        droid depot bay beacon.

        :param int affiliation: Droid affiliation. 0-2.
        :param int personalityChip: Installed personality chip. 1-8.
        :param bool paired: True if droid has finished pairing sequence
        :param bool battery_low: True if droid battery is low
        :param bool action78: True if action78
        :param int bay: Bay number received from droid depot bay beacon. 0-15
        '''
        byte3 = 0x01
        if paired:
            byte3 |= 0x80
        byte4 = (4 << 5) | (affiliation << 2) | ((personalityChip >> 8) & 1)
        byte5 = personalityChip & 0xff
        byte6 = bay & 0xf
        if battery_low:
            byte6 |= 0x80
        if action78:
            byte6 |= 0x10
        return self.add_subtype(0x03, struct.pack('<BBBBBB', 0x44, byte3, byte4, byte5, byte6, rssi))

    def remove_droid(self):
        self.remove_subtype(0x03)

    def add_droid_location(self, location, minInterval=0, expectedRssi=0, accept=0):
        '''
        Droid location beacon

        Sent by locations within the park. Droids react to these beacons based
        on the location number and the receiving droid's personality chip.
        Note that regardless of the minimum interval beacon, droids wait a
        minimum of 1m between location beacon responses.

        :param int location: 1-7. Runs associated interaction script.
        :param int minInterval: Minimum interval between droid rection. 0-255
        :param int expectedRssi: Minimum expect RSSI value for this beacon, -128-127.
        :param int accept: Ignored by droids if not 0 or 1. 0-255.
        '''
        expectedRssi = (256 + expectedRssi) & 0xff
        return self.add_subtype(0x0a, struct.pack("<BBBB", location, minInterval, expectedRssi, accept))

    def remove_droid_location(self):
        self.remove_subtype(0x0a)

    def add_droid_depot_bay(self, bay, expectedRssi):
        '''
        Droid Depot robot bay beacon

        :param int bay: Bay identifier for this beacon, 0-255.
        :param int expectedRssi: Minimum expect RSSI value for this beacon, -128-127.
        '''
        expectedRssi = (256 + expectedRssi) & 0xff
        return self.add_subtype(0xbd, struct.pack('<BB', bay, expectedRssi))

    def remove_droid_depot_bay(self):
        self.remove_subtype(0xbd)

    def add_droid_depot_activate(self, gapAddr, action, delay):
        '''
        Droid Depot activator beacon

        :param bytearray gapAddr: 6-byte Bluetooth addresso of the droid to active
        :param int action: Activation action type, 1 or 2.
        :param int delay: default delay / 100 for interaction script delay command.
        '''
        return self.add_subtype(0xbc, struct.pack('<6sBB', gapAddr, action, delay))

    def remove_droid_depot_activate(self):
        self.remove_subtype(0xbc)

    def add_showcontrol(self, down, inUse, status, guestId):
        byte0 = (down << 7) | (inUse << 6) | ((status & 0xf) << 2)
        self.has_interactionId.add(0x05)
        return self.add_subtype(0x05, struct.pack('>HB8s', self.interactionId, byte0, guestId))

    def remove_showcontrol(self):
        self.remove_subtype(0x05)

    def add_gameadvanced(self, waypointId, expectedRssi):
        expectedRssi = (256 + expectedRssi) & 0xff
        self.has_interactionId.add(0x10)
        return self.add_subtype(0x10, struct.pack(">HBB", self.interactionId, waypointId, expectedRssi))

    def remove_gameadvanced(self):
        self.remove_subtype(0x10)

    def add_arbitrary_tw(self, gameInProgress, gameSequence, hackCountThis, influenceGlobalFaction1, influenceGlobalFaction2, influenceThisFaction1, influenceThisFaction2, skimmerActive):
        byte0 = (gameInProgress << 7) | (skimmerActive << 6) | (gameSequence & 0x3f)
        influenceThisFaction1 = int(round(influenceThisFaction1 * 255.0))
        influenceThisFaction2 = int(round(influenceThisFaction2 * 255.0))
        influenceGlobalFaction1 = int(round(influenceGlobalFaction1 * 255.0))
        influenceGlobalFaction2 = int(round(influenceGlobalFaction2 * 255.0))
        return self.add_arbitrary(struct.pack('<xBBBBBB', byte0, influenceThisFaction1, influenceThisFaction2, influenceGlobalFaction1, influenceGlobalFaction2, hackCountThis))

    def add_arbitrary_audio(self, sequenceID, elapsedTime):
        return self.add_arbitrary(struct.pack('<xBB4x', elapsedTime, sequenceID))

    def add_arbitrary(self, arbdata):
        # arbdata can be up to 7 bytes, but is *left* padded with zero bytes to 7 bytes
        # after being received
        self.has_interactionId.add(0x06)
        return self.add_subtype(0x06, struct.pack(">H", self.interactionId) + arbdata)

    def remove_arbitrary(self):
        self.remove_subtype(0x06)


