#!/usr/bin/python3

import struct
import collections

def parse_cmd(data, cmd, cmds):
    if cmd in cmds:
        a = cmds[cmd]
        args = {'cmd': a[0]}
        result = collections.namedtuple('nm', a[1])
        if a[2]:
            sz = struct.calcsize(a[2])
            data, remainder = data[:sz], data[sz:]
            new_args = result._asdict(result._make(struct.unpack(a[2], data)))
            if a[3] is not None:
                a[3](new_args, remainder)
            args.update(new_args)
        else:
            remainder = data
    else:
        print(cmd, 'not in', cmds)
        args = {'cmd': cmd, 'data': data}
        remainder = bytearray()
    data[:] = remainder
    return args

def motor_fixup(args, data):
    args['reverse'] = (args['id'] & 0x80) != 0
    args['id'] &= ~0x80

cycle_led_cmds = {
    0x01: ('LED Mono Ramp', 'id ramp_time end_value', '>BHB', None),
    0x02: ('LED Mono Flash', 'id high_period low_period flashes high_value low_value', '>BHHBBB', None),
    0x03: ('LED Mono Pulse', 'id ramp_time cycles high_value low_value', '>BHBBB', None),
    0x04: ('LED RGB Ramp', 'id ramp_time r g b', '>BHBBB', None),
    0x05: ('LED RGB Flash', 'id high_period low_period flashes sr sg sb er eg eb', '>BHHBBBBBBB', None),
    0x06: ('LED RGB Pulse', 'id ramp_time cycles vr vg vb dr dg db', '>BHBBBBBBB', None),
}

def cycle_led_sub(args, data):
    new_args = parse_cmd(data, args['cmd'], cycle_led_cmds)
    args.clear()
    args.update(new_args)

def fixup_rotate_head1(args, data):
    args['reverse'] = (args['flags'] & 0x80) != 0
    del args['flags']

def fixup_rotate_head2(args, data):
    args['value'] = 255
    args['ramp_time'] = 0
    fixup_rotate_head1(args, data)

def fixup_fwdrev(args, data):
    args['reverse'] = (args['flags'] & 0x80) != 0
    if (args['flags'] & 0x01) == 0:
        args['value'] = 'default'
    del args['flags']

custom_cmds = {
    0x44: {
        0x00: ('Serial Write', 'reg value', '>BB', None),
        0x01: ('Center R2 Head', 'value start_timer', '>BB', None),
        0x02: ('Rotate R2 Head1', 'flags value ramp_time delay', '>BBHH', fixup_rotate_head1),
        0x03: ('Rotate R2 Head2', 'flags delay', '>BB', fixup_rotate_head2),
        0x04: ('BB8 Rotate', 'flags value ramp_time delay', '>BBHH', fixup_rotate_head1),
        0x05: ('Drive Fwd/Rev', 'flags value ramp_time delay', '>BBHH', fixup_fwdrev),
    }
}

def custom_cmd(args, data):
    if args['custom_id'] in custom_cmds:
        new_args = parse_cmd(data, args['cmd'], custom_cmds[args['custom_id']])
    else:
        new_args = {'custom_id': args['custom_id'], 'data': data.copy()}
        data[:] = bytearray()
    args.clear()
    args.update(new_args)

droid_cmds = {
    0x01: ('ID', '', None, None),
    0x02: ('Mono LED', 'id brightness', '>BB', None),
    0x03: ('RGB LED', 'id r g b', '>BBBB', None),
    0x04: ('Cycle LED', 'cmd', '>B', cycle_led_cmds),
    0x05: ('Motor', 'id value ramp_time', '>BBH', motor_fixup),
    0x06: ('No action', '', None, None),
    0x0c: ('Script', 'entry action', '>BB', None),
    0x0d: ('Delay', 'delay', '>H', None),
    0x0f: ('Custom', 'custom_id cmd', '>BB', custom_cmd),
}

def parse(b):
    c, b = b[:3], b[3:]
    entry_type, entry_len, sum = struct.unpack('<BBB', c)
    if entry_type != 1:
        raise Exception('Unexpected entry type:', entry_type)

    c, b = b[:1], b[1:]
    entry_id, = struct.unpack('<B', c)

    cmds = []

    while len(b) >= 2:
        c, b = b[:2], b[2:]
        cmd, l = struct.unpack('<BB', c)
        present = (l & 0x40) != 0
        l &= 0x1f

        if not present:
            break

        cmd_data, b = b[:l], b[l:]
        args = parse_cmd(cmd_data, cmd, droid_cmds)
        cmds.append(args)

    return cmds

entries = {
    1: '015700010f444401a0010f44440010040f44440300140f48440200820028014a0f4844020000002800280f44440380140f48440280820028015e0f48440280ff0028012c0f48440200ff0050026c0f444401ff01054402000028',
    2: '016b00020f444401a0010f44440010030f4844028088000000a00f4844020084005001900f4844028084005001900f4844020084005000f00f4844020000002800280f44440380140f4844028082002802f80f4844028000002800280f44440300140f4444018201054402000028',
    3: '015500030f444401a0010f44440010020f44440300140f4844020082000402260f4844020000002800280d42012c0f44440380140f4844028082002805140f4844028000002800280d42012c0f444401dc01054402000014',
    4: '015700040f444401a0010f44440010000f44440300140f4844020082000001900f48440280dc003c03200f48440200d2003c02bc0f48440280fa003c028a0f4844028000002800280f44440300140f4444018201054402000000',
    5: '015700050f444401a0010f44440010010f44440300140f4844020082002801680f48440280e6002801f40f4844028000002800280f48440200e6002801f40f4844020000002800280f44440380140f4444018201054402000000',
    6: '018f00060f444401a0010f44440010060f44440300140f4844020082002801900f4844020000001400140d42010e0f44440380140f48440280820028044c0f4844028000001400140d42010e0f44440300140f48440200820028028a0f4844020000001400140f44440380140f4844028082000001900f4844028000001400140f44440300140f4444018201054402000000',
    7: '015b00070f444401a0010f44440010050f44440300140f4844020087001400b40f48440280a0002801900f48440200a0002801900f48440280a0002801ae0f48440200a0002801900f44440380140f484402808700140118054402000028',
    8: '014d00080d4200000f44440300140f484402008200280bb80f44440380140f4844028082000013880f44440300140f4844020082000013880f44440380140f44440182010544020000000f4444001007',
    9: '014500090f44440010040f48440400b400c802580f48440480b4019003200f48440400b4019003200f48440480b4019003200f48440400b401900190054400000032054401000032',
    10: '0131000a0f44440010030f48440400b400c8012c0f48440480b4019002580f484404008c01540640054400000032054401000032',
    11: '0131000b0f44440010020f48440400b400c801900f4844048082019008fc0f48440400aa019002bc054400000032054401000032',
    12: '013b000c0f44440010000f48440400a000a0012c0f48440480b4019002580f48440400b4019002580f48440480a001900258054400000032054401000032',
    13: '013b000d0f44440010010f484404006e007803200f484404807800f0044c0f484404007800f0044c0f484404806e00f00320054400000032054401000032',
    14: '0131000e0f44440010060f4844040064006402bc0f484404806900c803e80f484404006400c802bc054400000000054401000000',
    15: '0145000f0f44440010050f48440400a0006401900f48440480be019002580f48440400be019002580f48440480be019003200f48440400b401900258054400000032054401000032',
    16: '017300100d4200000f484404005a002803200544000000500544010000500d4208fc0f484404805a002805140544000000500544010000500d4208fc0f484404005a002805140544000000500544010000500d4208fc0f484404805a002809c40544000000500544010000500d4205780f4444001007',
    17: '010b00110d4200640f4444001007',
    18: '010b00120d4207d00f4444001007',
    19: '012b00130544002000000544012000000f48440501dc019000fa0f484405000002ee00fa0f48440501dc01900000',
}

for id, entry in entries.items():
    print('Entry', id)
    cmds = parse(bytearray.fromhex(entry))
    for cmd in cmds:
        print(cmd)
