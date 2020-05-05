#!/usr/bin/python

import dbus
import dbus.exceptions
import dbus.service

import array

DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'


class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class InvalidValueLengthException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.InvalidValueLength'


class FailedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.Failed'

def empty_reply_handler():
    pass

def empty_error_handler(error):
    pass

class Advertisement(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/advertisement'

    def __init__(self, manager, index, advertising_type):
        self.path = self.PATH_BASE + str(index)
        self.manager = manager
        self.ad_type = advertising_type
        self.adapter_object = manager._bus.get_object('org.bluez', '/org/bluez/' + manager.adapter_name)
        self.ad_manager = dbus.Interface(self.adapter_object, 'org.bluez.LEAdvertisingManager1')
        self.service_uuids = None
        self.discoverable = None
        self.discoverable_to = None
        self.manufacturer_data = None
        self.solicit_uuids = None
        self.service_data = None
        self.data = None
        self.include_tx_power = None
        self.rh = None
        self.eh = None
        self.running = False
        dbus.service.Object.__init__(self, manager._bus, self.path)

    def refresh(self):
    	if self.running:
             self.ad_manager.UnregisterAdvertisement(self.get_path())
             self.ad_manager.RegisterAdvertisement(self.get_path(), {}, reply_handler=self.rh, error_handler=self.eh)

    def register(self, reply_handler=empty_reply_handler, error_handler=empty_error_handler):
        self.manager._adapter_properties.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))
        self.rh = reply_handler
        self.eh = error_handler
        self.running = True
        self.ad_manager.RegisterAdvertisement(self.get_path(), {}, reply_handler=self.rh, error_handler=self.eh)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        if self.service_uuids is not None:
            properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                                    signature='s')
        if self.solicit_uuids is not None:
            properties['SolicitUUIDs'] = dbus.Array(self.solicit_uuids,
                                                    signature='s')
        if self.manufacturer_data is not None:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data, signature='qv')

        if self.discoverable is not None:
            properties['Discoverable'] = dbus.Boolean(self.discoverable)

        if self.discoverable_to is not None:
            properties['DiscoverableTimeout'] = dbus.UInt16(self.discoverable_to)

        if self.service_data is not None:
            properties['ServiceData'] = dbus.Dictionary(self.service_data,
                                                        signature='sv')
        if self.data is not None:
            properties['Data'] = dbus.Dictionary(self.data, signature='yv')

        includes = []
        if self.include_tx_power is not None:
            includes.append('tx-power')
        if includes and False:
            properties['Includes'] = dbus.Array(includes, signature='s')

        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid):
        if not self.service_uuids:
            self.service_uuids = []
        self.service_uuids.append(uuid)

    def add_solicit_uuid(self, uuid):
        if not self.solicit_uuids:
            self.solicit_uuids = []
        self.solicit_uuids.append(uuid)

    def add_manufacturer_data(self, manuf_code, data):
        if not self.manufacturer_data:
            self.manufacturer_data = dbus.Dictionary({}, signature='qv')
        self.manufacturer_data[manuf_code] = dbus.Array(data, signature='y')

    def add_discoverable(self, state):
        self.discoverable = state

    def add_discoverable_to(self, timeout=100):
        self.discoverable_to = timeout

    def add_service_data(self, uuid, data):
        if not self.service_data:
            self.service_data = dbus.Dictionary({}, signature='sv')
        self.service_data[uuid] = dbus.Array(data, signature='y')

    def add_data(self, type, data):
        if not self.data:
            self.data = dbus.Dictionary({}, signature='yv')
        self.data[type] = dbus.Array(data, signature='y')

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        print('GetAll')
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        print('returning props')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released!' % self.path)
