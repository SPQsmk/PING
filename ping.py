import os, sys, socket, struct, select, time
import numpy as np
 
ICMP_ECHO_REQUEST = 8 # Seems to be the same on Solaris.
 
 
def checksum(source_string):
    _sum = 0
    count_to = len(source_string)
    count = 0

    while count < count_to:
        this_val = source_string[count + 1]*256 + source_string[count]
        _sum = _sum + this_val
        # берется последние 4 байта
        _sum = _sum & 0xffffffff
        count = count + 2
 
    _sum = (_sum >> 16) + (_sum & 0xffff)
    _sum = _sum + (_sum >> 16)
    answer = ~_sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
 
    return answer
 
 
def receive_one_ping(my_socket, _id, timeout):
    time_left = timeout
    while True:
        started_select = time.time()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = (time.time() - started_select)
        if not what_ready[0]: # Timeout
            return
 
        time_received = time.time()
        rec_packet, addr = my_socket.recvfrom(1024)
        icmp_header = rec_packet[20:28]
        type, code, check_sum, packet_id, sequence = struct.unpack(
            "bbHHh", icmp_header
        )
        if packet_id == _id:
            bytes_in_double = struct.calcsize("d")
            time_sent = struct.unpack("d", rec_packet[28:28 + bytes_in_double])[0]
            return time_received - time_sent
 
        time_left = time_left - how_long_in_select
        if time_left <= 0:
            return
 
 
def send_one_ping(my_socket, dest_addr, ID):
    # IP адрес сервера
    dest_addr  =  socket.gethostbyname(dest_addr)
 
    my_checksum = 0
 
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    bytes_in_double = struct.calcsize("d")
    data = (192 - bytes_in_double) * "Q"
    data = struct.pack("d", time.time()) + data.encode('ASCII')
 
    my_checksum = checksum(header + data)
 
    header = struct.pack(
        "bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1
    )
    packet = header + data
    my_socket.sendto(packet, (dest_addr, 1)) # 1 - port
 
 
def do_one(dest_addr, timeout):
    icmp = socket.getprotobyname("ICMP")
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    except socket.error as err:
        errno, msg = err.errno, err.strerror
        if errno == 1:
            msg = msg + (
                " - Note that ICMP messages can only be sent from processes"
                " running as root."
            )
            raise socket.error(msg)
        raise
 
    # берем последние два байта
    my_id = os.getpid() & 0xFFFF
 
    send_one_ping(my_socket, dest_addr, my_id)
    delay = receive_one_ping(my_socket, my_id, timeout)
 
    my_socket.close()
    return delay
 
 
def verbose_ping(dest_addr, timeout = 2, count = 4):
    attempts_array = []
    host = socket.gethostbyname(dest_addr)
    success_count = 0

    print(f'Exchange packages with {dest_addr} [{host}]:')
    for i in range(count):
        print(f'ping {host}...', end=' ')
        try:
            delay  =  do_one(dest_addr, timeout)
        except socket.gaierror as e:
            print(f'failed. (socket error: {str(e)})')
            break
 
        if delay is None:
            print(f'failed. (timeout within {timeout} sec.)')
        else:
            delay  =  delay * 1000
            attempts_array.append(delay)
            success_count += 1
            print(f'get ping in %0.4fms' % delay)
    print()
    print(f'Ping statistics of {host}:')
    print(f'    packages: set = {count}, get = {success_count}, lost = {count - success_count}')
    print(f'    ({(count - success_count) * 100:.0f}% lost)')
 
 
if __name__ == '__main__':
    verbose_ping("yandex.ru")