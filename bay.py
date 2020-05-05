#!/usr/bin/python3

import gatt
import struct
import signal
import binascii
import sys
import os
import fcntl
import datetime
import gi.repository
import dbeacon
import dbus
from PyQt5 import QtCore
import dbus.mainloop.pyqt5

class IODriver(object):
    def __init__(self, line_callback):
        self.buffer = ''
        self.line_callback = line_callback
        flags = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
        flags |= os.O_NONBLOCK
        fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flags)
        gi.repository.GLib.io_add_watch(sys.stdin, gi.repository.GLib.IO_IN, self.io_callback)

    def io_callback(self, fd, condition):
        chunk = fd.read()
        for char in chunk:
            self.buffer += char
            if char == '\n':
                self.line_callback(self.buffer)
                self.buffer = ''

        return True

def register_ad_cb():
    print('Advertisement registered')

def register_ad_error_cb(error):
    print('Failed to register advertisement: ' + str(error))

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object('org.bluez', '/'),
                               'org.freedesktop.DBus.ObjectManager')
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if 'org.bluez.LEAdvertisingManager1' in props and 'org.bluez.GattManager1' in props:
            return o
    return None

class AnyDeviceManager(gatt.DeviceManager):
    def __init__(self, adapter_name):
        super().__init__(adapter_name)
        self.connect_signals()
        self.addr = None

    def device_discovered(self, device):
        super().device_discovered(device)
        if device.alias() != 'DROID':
            return

        mfd = device._properties.Get('org.bluez.Device1', 'ManufacturerData')
        if dbeacon.MFG_ID_DISNEY not in mfd:
            return

        dbeacons = dbeacon.parse(bytes(mfd[dbeacon.MFG_ID_DISNEY]))
        if 0x03 not in dbeacons or dbeacons[0x03]['droid_id'] != 0x44:
            return

        affiliation = dbeacon.affiliation[dbeacons[0x03]['affiliation']]
        personality = dbeacon.personality[dbeacons[0x03]['personalityChip']]
        desc = f'{device.alias()} [{device.mac_address}] {affiliation}/{personality}'
        now = datetime.datetime.now()
        print(f'[{now:%H:%M:%S}] Discovered [{device.mac_address}] {device.alias()}', dbeacons[3])
        self.addr = bytearray.fromhex(''.join(device.mac_address.split(':')))

    def line_entered(self, line):
        if line[0] == '1':
            if self.addr is not None:
                print(f'pair {self.addr}')
                self.adv.add_droid_depot_activate(self.addr, dbeacon.DROID_DEPOT_ACTIVATE_PAIR, 0)
        elif line[0] == '2':
            if self.addr is not None:
                print(f'activate {self.addr}')
                self.adv.add_droid_depot_activate(self.addr, dbeacon.DROID_DEPOT_ACTIVATE_GO, 2)
        else:
            print('removed')
            self.adv.remove_droid_depot_activate()

    def connect_signals(self):
        self._interface_added_signal = self._bus.add_signal_receiver(
            self._interfaces_added,
            dbus_interface='org.freedesktop.DBus.ObjectManager',
            signal_name='InterfacesAdded')
        self._properties_changed_signal = self._bus.add_signal_receiver(
            self._properties_changed,
            dbus_interface=dbus.PROPERTIES_IFACE,
            signal_name='PropertiesChanged',
            arg0='org.bluez.Device1',
            path_keyword='path')

signal.signal(signal.SIGINT, signal.SIG_DFL)

dbus.mainloop.pyqt5.DBusQtMainLoop(set_as_default=True)
app = QtCore.QCoreApplication(sys.argv)

adapter_name = os.path.basename(find_adapter(dbus.SystemBus()))
manager = AnyDeviceManager(adapter_name=adapter_name)

adv = dbeacon.dBeacon(manager, 0)
#adv.add_droid_location(2, 2, -90, 1)
#adv.add_droid_depot_activate(bytearray.fromhex('d5a8b5ba307a'), 2, 0)
adv.add_droid_depot_bay(5, -90)
adv.register(register_ad_cb, register_ad_error_cb)
manager.adv = adv

manager.start_discovery()

d = IODriver(manager.line_entered)

app.exec_()

