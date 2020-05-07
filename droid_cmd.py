import robot_cmd
import struct

custom_id = 0x44

SERIAL_VOLUME = 0x0e
SERIAL_SOUND = 0x10
SERIAL_SOUND_FLASH = 0x11
SERIAL_LED_ON = 0x48
SERIAL_LED_OFF = 0x49

class droid_cmd_buffer(robot_cmd.robot_cmd_buffer):
    def serial_reg_write(self, reg, value):
        '''
        Perform a serial register write to the GeneralPlus chip

        reg 0x10: Play sound. 0-6
        reg 0x11: R2 special action. 10-11

        :param int reg: Write register 0-255
        :param int value: Write value 0-255
        '''
        self.custom(custom_id, 0x00, struct.pack('>BB', reg, value))

    def r2_center_head(self, value, start_timer):
        '''
        Center the R2 unit head

        :param int value: Motor speed to use when centering. 0-255
        :param bool start_timer: Insert a 3s delay before executing the
        next script command. Has no effect outside of command scripts.
        '''
        self.custom(custom_id, 0x01, struct.pack('>BB', value, start_timer))

    def r2_rotate_head1(self, value, ramp_time, delay):
        '''
        Rotate R2 unit head

        :param int value: Motor value to use for head rotation. -255-255
        :param int ramp_time: Time period over which to ramp to new motor value. 0-65535
        :param int delay: Delay before executing next command script instruction. 0-65535
        '''
        if value < 0:
            flags = 0x80
            value = -value
        else:
            flags = 0x00
        self.custom(custom_id, 0x02, struct.pack('>BBHH', flags, value, ramp_time, delay))

    def r2_rotate_head2(self, forward, delay):
        '''
        Rotate R2 unit head

        This version always uses 255 or -255 for motor speed. The ramp time is always 0.

        :param bool forward: Determines the head rotation direction.
        :param int delay: Delay before executing next command script instruction. 0-65535
        '''
        flags = 0x00 if forward else 0x80
        self.custom(custom_id, 0x03, struct.pack('>BB', flags, delay))

    def bb8_rotate(self, value, ramp_time, delay):
        '''
        Rotate R2 unit

        :param int value: Motor value to use for rotation. -255-255
        :param int ramp_time: Time period over which to ramp to new motor value. 0-65535
        :param int delay: Delay before executing next command script instruction. 0-65535
        '''
        if value < 0:
            flags = 0x80
            value = -value
        else:
            flags = 0x00
        self.custom(custom_id, 0x04, struct.pack('>BBHH', flags, value, ramp_time, delay))

    def bb8_fwd_rev(self, value, ramp_time, delay):
        '''
        Move R2 unit forward or back

        :param int value: Motor value to use for movement. -255-255
        :param int ramp_time: Time period over which to ramp to new motor value. 0-65535
        :param int delay: Delay before executing next command script instruction. 0-65535
        '''
        if value < 0:
            flags |= 0x80
            value = -value
        else:
            flags = 0x00
        self.custom(custom_id, 0x05, struct.pack('>BBHH', flags, value, ramp_time, delay))

    def bb8_fwd_rev_default(self, forward, ramp_time, delay):
        '''
        Move R2 unit forward or back

        This version uses a default value for motor speed, +/- 220.

        :param bool foward: True to move forward. False to reverse.
        :param int ramp_time: Time period over which to ramp to new motor value. 0-65535
        :param int delay: Delay before executing next command script instruction. 0-65535
        '''
        flags = 0x01 if forward else 0x81
        self.custom(custom_id, 0x05, struct.pack('>BBHH', flags, 0x00, ramp_time, delay))

