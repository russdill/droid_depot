import struct 

class cmd_buffer:
    def __init__(self):
        self.buf = b''

    def pop(self):
        '''
        Return the current command buffer and clear it.

        :return: The current command buffer
        :rtype: bytearray
        '''
        ret = self.buf
        self.buf = b''
        return ret

    def cmd(self, id, data=b'', sub_cmd=0x00):
        '''
        Encode a single command.

        The command is encoded and added to the current command buffer.

        :param int id: The command id, 0-255
        :param bytearray data: The command data
        :param int sub_cmd: The sub-command (0 or 0x42)
        '''
        if len(data) > 0x1f:
            raise Exception('Command data too large')
        self.buf += struct.pack('>BBBB', (len(data)+3) | 0x20, sub_cmd, id, len(data) | 0x40) + data

    def cmd_script(self, id, data=b''):
        '''
        Add command script element.

        Store a command in the currently open command script. (See script_open).

        :param int id: The command id, 0-255
        :param bytearray data: The command data
        '''
        self.cmd(id, data, sub_cmd=0x42)

    def empty(self):
        return len(self.buf) == 0

class robot_cmd_buffer(cmd_buffer):
    def id(self):
        '''
        Request ID

        Returns the ID of the robot/firmware in a GATT notify event. Return
        data format is unknown but is fixed in the firmware.
        '''
        self.cmd(0x01)

    def led_mono(self, idx, value):
        '''
        Set a mono LED to a specific value.

        :param int idx: The ID of the mono LED, 1-127. A value of 0 sets all mono LEDs
        :param int value: The brightness value of the LED, 0-255
        '''
        self.cmd(0x02, struct.pack('>BB', idx, value))

    def led_rgb(self, idx, rgb_value):
        '''
        Set an RGB LED to a specific value.

        :param int idx: The ID of the RGB LED, 1-127. A value of 0 sets all RGB LEDs
        :param tuple value: An RGB (r, g, b) brightness tuple of the LED, 0-255
        '''
        self.cmd(0x03, struct.pack('>BBBB', idx, rgb_value[0], rgb_value[1], rgb_value[2]))

    def led_mono_ramp(self, idx, end_value, ramp_time):
        '''
        Ramp a mono LED to a specific value

        :param int idx: The ID of the mono LED, 1-127. A value of 0 ramps all mono LEDs
        :param int end_value: The desired brightness of the LED, 0-255
        :param int ramp_time: The time over which to ramp the value, 0-65535
        '''
        self.cmd(0x04, struct.pack('>BBHB', 0x01, idx, ramp_time, end_value))

    def led_mono_flash(self, idx, high_value, low_value, flashes, high_period, low_period):
        '''
        Flash a mono LED a number of cycles

        :param int idx: The ID of the mono LED, 1-127. A value of 0 flashes all mono LEDs
        :param int high_value: The on brightness value, 0-255
        :param int low_value: The off brightness value, 0-255
        :param int flashes: The number of on/off cycles 0-255
        :param int high_period: The per flash on period, 0-65535
        :param int low_period: The per flash off period, 0-65535
        '''
        self.cmd(0x04, struct.pack('>BBHHBBB', 0x02, idx, high_period, low_period, flashes, high_value, low_value))

    def led_mono_pulse(self, idx, high_value, low_value, cycles, ramp_time):
        '''
        Pulse a mono LED a number times

        :param int idx: The ID of the mono LED, 1-127. A value of 0 pulses all mono LEDs
        :param int high_value: The high brightness value, 0-255
        :param int low_value: The low brightness value, 0-255
        :param int cycles: The number of times to pulse the LED either up or down. An odd number will leave the LED high. 0-255
        :param int ramp_time: The amount of delay to ramp from low to high or high to low. 0-65535
        '''
        self.cmd(0x04, struct.pack('>BBHBBB', 0x03, idx, ramp_time, cycles, high_value, low_value))

    def led_rgb_ramp(self, idx, rgb_end_value, ramp_time):
        '''
        Ramp an RGB LED to a specific value

        :param int idx: The ID of the RGB LED, 1-127. A value of 0 ramps all RGB LEDs
        :param tuple end_value: An RGB (r, g, b) brightness tuple of the LED, 0-255
        :param int ramp_time: The time over which to ramp the value, 0-65535
        '''
        self.cmd(0x04, struct.pack('>BBHBBB', 0x04, idx, ramp_time, rgb_end_value[0], rgb_end_value[1], rgb_end_value[2]))

    def led_rgb_flash(self, idx, rgb_high_value, rgb_low_value, flashes, high_period, low_period):
        '''
        Pulse an RGB LED a number times

        :param int idx: The ID of the RGB LED, 1-127. A value of 0 pulses all RGB LEDs
        :param tuple high_value: An RGB (r, g, b) on brightness tuple of the LED, 0-255
        :param tuple low_value: An RGB (r, g, b) off brightness tuple of the LED, 0-255
        :param int cycles: The number of times to pulse the LED either up or down. An odd number will leave the LED high. 0-255
        :param int ramp_time: The amount of delay to ramp from low to high or high to low. 0-65535
        '''
        self.cmd(0x04, struct.pack('>BBHHBBBBBBB', 0x05, idx, high_period, low_period, flashes,
                rgb_high_value[0], rgb_high_value[1], rgb_high_value[2],
                rgb_low_value[1], rgb_low_value[1], rgb_low_value[2]))

    def led_rgb_pulse(self, idx, rgb_high_value, rgb_low_value, cycles, ramp_time):
        '''
        Pulse an RGB LED a number times

        :param int idx: The ID of the RGB LED, 1-127. A value of 0 pulses all RGB LEDs
        :param tuple high_value: An RGB (r, g, b) high brightness tuple of the LED, 0-255
        :param tuple low_value: An RGB (r, g, b) low brightness tuple of the LED, 0-255
        :param int cycles: The number of times to pulse the LED either up or down. An odd number will leave the LED high. 0-255
        :param int ramp_time: The amount of delay to ramp from low to high or high to low. 0-65535
        '''
        self.cmd(0x04, struct.pack('>BBHBBBBBBB', 0x06, idx, ramp_time, cycles,
                rgb_high_value[0], rgb_high_value[1], rgb_high_value[2],
                rgb_low_value[0], rgb_low_value[1], rgb_low_value[2]))

    def motor(self, idx, value, ramp_time):
        '''
        Set motor speed

        :param int value: The desired speed of the motor. -255-255.
        :param int ramp_time: The time over which to ramp up/down to the desired speed. 0-65535.
        '''
        if value < 0:
            value = -value
            idx |= 0x80
        self.cmd(0x05, struct.pack('>BBH', idx, value, ramp_time))

    def nop(self, idx):
        '''
        Do nothing

        Possibly unimplemented command on BB8/R2
        '''
        self.cmd(0x06)

    def script_open(self, idx):
        '''
        Start a new command script

        Starts a new command script in memory on the robot. Commands sent will
        be stored to the command script in memory. Starting a new command
        script while another command script is open will cause the original
        command script to be first stored. See cmd_script for addding commands
        to the currently open command script.

        Note that the robot contains a pre-programmed set of command scripts
        in identifiers 1-19. Those cannot be overwritten.

        :param int idx: Identifier of the command script, 20-127
        '''
        self.cmd(0x0c, struct.pack('>BB', idx, 0x00))

    def script_finish(self):
        '''
        Store a command script

        Stores the currently in memory command script to flash memory.
        '''
        self.cmd(0x0c, struct.pack('>BB', 0x00, 0x01))

    def script_run(self, idx):
        '''
        Run a command script

        :param int idx: Identified or the command script, 1-127
        '''
        self.cmd(0x0c, struct.pack('>BB', idx, 0x02))

    def delay(self, delay):
        '''
        Insert a delay in a command script

        Note: Has no effect outside of command script usage.

        :param int delay: The length of delay before executing the next command
        script instruction. 1-65535. A value of 0 will use a special in memory
        delay which defaults to zero unless set by a 0xbc beacon.
        '''
        self.cmd(0x0d, struct.pack('>H', delay))

    def custom(self, id, cmd, bytes):
        '''
        Execute a robot specific command

        :param int id: The robot identifier this command is valid for. 0-255
        :param int cmd: The sub-command id. 0-255
        :param bytearray bytes: The sub-command data
        '''
        self.cmd(0x0f, struct.pack('>BB', id, cmd) + bytes)

