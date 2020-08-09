import asyncio
import logging
import sys
import select
import math
import json
import calendar
import time
from datetime import datetime, timedelta
import datetime
from net_socket.signal_killer import GracefulInterruptHandler

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class AsyncServer:
    
    def convert(self, list):
        return tuple(i for i in list)
    
    
    def convert_hex2decimal(self, packet_bytes, readable_sock):
        """
        In the packet, the hexadecimal value is converted to a decimal value, structured in json format, and returned.
        
        packet           TCP Stream packet from IIot Gateway
        readable_sock       client socket object
        
        packet specification
        stx is the starting code, the hex value matching STX in the ascii code table
        utc time is the time when the sensor value is received from the iiot gate
        equipment id means the id of the equipment and is predefined in the database.
        sensor code is means the sensor's type like as tempeatur, pressure, voltage,...
        precision means the accuracy of sensor value, decimal point.
        The sensor value means the sensor value installed in the facility.
        """
        status = 'ER'
        modbus_dict = {'equipment_id': '', 'meta': {'ip': '',
                                                             'port': '',
                                                             'time':'' ,
                                                             'sensor_cd':'' ,
                                                             'fun_cd':'' ,
                                                             'sensor_value': '',
                                                             'precision':''
                                                             }}
        try:
            byte_tuple = self.convert(list(packet_bytes))
            print(byte_tuple)
            
            if byte_tuple[0] == 2 and (byte_tuple[16] == 3 or byte_tuple[18] == 3):
                group = chr(byte_tuple[5]) + chr(byte_tuple[6])
                group_code = int('0x{:02x}'.format(byte_tuple[7]) + '{:02x}'.format(byte_tuple[8]), 16)
                group_code = '{0:04d}'.format(group_code)
    
                sensor_code = int('0x{:02x}'.format(byte_tuple[9]) + '{:02x}'.format(byte_tuple[10]), 16)
                sensor_code = '{0:04d}'.format(sensor_code)

                if sensor_code == '0007' or sensor_code == '0008':
                    """
                    Pressure Exception Controll
                    """
                    logging.debug('pressure:' + str(sensor_code))
                    pv = '0x{:02x}'.format(byte_tuple[13]) + '{:02x}'.format(byte_tuple[14]) + '{:02x}'.format(
                        byte_tuple[15]) + '{:02x}'.format(byte_tuple[16])
                    precision = int('0x{:02x}'.format(byte_tuple[17]), 16)
                else:
                    pv = '0x{:02x}'.format(byte_tuple[13]) + '{:02x}'.format(byte_tuple[14])
                    precision = int('0x{:02x}'.format(byte_tuple[15]), 16)
                sensor_value = int(pv, 16)
                
                
                d = datetime.datetime.utcnow()+ timedelta(hours=9)
                unixtime = calendar.timegm(d.utctimetuple())
                str_hex_utc_time = str(d)
                
                host, port = readable_sock.getpeername()
                modbus_dict = {'equipment_id': group+group_code, 'meta': {'ip': host,
                                                                    'port': port,
                                                                    'time': str_hex_utc_time,
                                                                    'sensor_cd': sensor_code,
                                                                    'fun_cd': 'PV',
                                                                    'sensor_value': sensor_value,
                                                                    'precision': precision
                                                                    }}
    
                status = 'OK'
            else:
                status = 'ER'
        except Exception as e:
            logging.exception(str(e))
        logging.debug(status + str(packet_bytes) + str(modbus_dict))
        return status, str(packet_bytes), modbus_dict
    
    
    async def get_client(self, event_manger, server_sock, msg_size,redis_con, mq_channel):
        """
        It create client socket with server sockt
        event_manger        It has asyncio event loop
        server_socket       Socket corresponding to the client socket
        msg_size            It means the packet size to be acquired at a time from the client socket.
        msg_queue           It means the queue containing the message transmitted from the gateway.
        """
        with GracefulInterruptHandler() as h:
            while True:
                if not h.interrupted:
                    client, _ = await event_manger.sock_accept(server_sock)
                    event_manger.create_task(self.manage_client(event_manger,  client, msg_size, redis_con,mq_channel))
                else:
                    client.close()
                    server_sock.close()
                    sys.exit(0)

    @asyncio.coroutine
    def do_work(self, envelope, body):
        yield from asyncio.sleep(int(body))
        print("consumer {} recved {} ({})".format(envelope.consumer_tag, body, envelope.delivery_tag))

    @asyncio.coroutine
    def callback(self, body, envelope, properties):
        loop = asyncio.get_event_loop()
        loop.create_task(self.do_work(envelope, body))
        
    async def manage_client(self, event_manger, client, msg_size, redis_con, mq_channel):
        
            
        """
            It receives modbus data from iiot gateway using client socket.
            event_manger        It has asyncio event loop
            client              It is a client socket that works with multiple iiot gateways.
            msg_size            It means the packet size to be acquired at a time from the client socket.
            msg_queue           It means the queue containing the message transmitted from the gateway.
        """
        facilities_dict = {}
        facilities_info = json.loads(redis_con.get('facilities_info').decode())
        equipment_keys = facilities_info.keys()
        for equipment_key in equipment_keys:
            facilities_dict[equipment_key]={}
            for sensor_id in  facilities_info[equipment_key].keys():
                sensor_desc = facilities_info[equipment_key][sensor_id]
                if sensor_desc not in facilities_dict[equipment_key].keys():
                    facilities_dict[equipment_key][sensor_desc]=0.0
        with GracefulInterruptHandler() as h:
            while True:
                if not h.interrupted:
                    try:
                        packet = (await event_manger.sock_recv(client, msg_size))
                        if packet:
                            try:
                                logging.debug('try convert')
                                status, packet, modbus_udp = self.convert_hex2decimal(packet, client)
                                if status == 'OK':
                                    str_modbus_udp = str(modbus_udp)
                                    logging.debug('Queue put:' + str_modbus_udp)
                                    equipment_id = modbus_udp['equipment_id']
                                    sensor_code = modbus_udp['meta']['sensor_cd']
                                    redis_sensor_info = json.loads(redis_con.get('facilities_info'))
                                    if equipment_id in redis_sensor_info.keys():
                                        sensor_desc = redis_sensor_info[equipment_id][sensor_code]
                                        routing_key = modbus_udp['equipment_id']
                                        facilities_dict[equipment_key]['time']=modbus_udp['meta']['time']
                                        facilities_dict[equipment_key][sensor_desc] = modbus_udp['meta']['sensor_value']
                                        logging.debug(routing_key + ','+ sensor_desc + ', update')
                                        logging.debug(str(facilities_dict))
                                        mq_channel.basic_publish(exchange='facility', routing_key=routing_key, body=json.dumps(facilities_dict))
                                    else:
                                        acq_message = status + packet + 'no exist key\r\n'
                                        client.sendall(acq_message.encode())
                                        continue
                                acq_message = status + packet + '\r\n'
                                client.sendall(acq_message.encode())
                            except Exception as e:
                                client.sendall(packet.encode())
                                logging.exception('message error:' + str(e))
                        else:
                            client.close()
                    except Exception as e:
                        logging.exception('manage client exception:' + str(e))
                        break
                else:
                    client.close()
                    sys.exit(0)
                

    async def apply_sensor_name(self, db_con, message):
        equipment_id = message['equipment_id']
        sensor_code = message['meta']['sensor_cd']
        redis_sensor_info = json.loads(db_con.get('facilities_info'))
        sensor_desc = redis_sensor_info[equipment_id][sensor_code]
        message['meta']['sensor_desc'] = sensor_desc
        return message
    
    
    def modbus_mqtt_publish(self, msg_queue, redis_con, mq_channel, u_test=False):
       while True:
           time.sleep(0.01)
           if msg_queue.qsize() > 0:
            if u_test == True:
                print('Test Mode')
            msg_json = msg_queue.get()
            if u_test == True:
                return msg_json
            else:
                try:
                    msg_json = self.apply_sensor_name(db_con=redis_con, message=msg_json)
                    routing_key = msg_json['equipment_id']
                    # msg_body = str(msg_json['meta'])
                    msg_body = json.dumps(msg_json['meta'])
                    logging.debug('equipment_id:'+routing_key)
                    logging.debug('mqtt publish:' + str(msg_body))
                    # mq_channel.basic_publish(exchange='', routing_key=routing_key, body=msg_body)
                except Exception as e:
                    print(e)



