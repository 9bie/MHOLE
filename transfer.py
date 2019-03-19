# coding:utf-8
# 搬运模块
import socket
import select
import struct
import threading
import queue
import time
# class plugin:
#     def __init__(self,func1,func2,func3,func4):
#         """
#         插件基类
#         :param func1: 客户进入处理函数
#         :param func2: 客户消息到达处理函数
#         :param func3: 客户退出处理函数
#         :param func4: 错误处理函数
#         """
#         self.func1 = func1
#         self.func2 = func2
#         self.func3 = func3
#         self.func4 = func4
#     def event(self,event_number,msg=None,conn1=None,conn2=None):
#         '''
#         :param event_number: 类似TCP状态码
#         :param msg: recv
#         :param conn1: send conn
#         :param conn2: recv conn
#         :return:
#         '''
#         pass
class tcp2tcp(object):
    def __init__(self,local_port,remote_host,remote_port,reconn=-1):
        '''

        :param local_port: 本地监听端口
        :param remote_host: 远程主机地址
        :param remote_port: 远程主机端口
        :param reconn: 最大重连次数，设置为0则一直重连，每次间隔3s,-1则为不重连
        '''

        self.server = socket.socket()
        self.server.bind(("0.0.0.0", local_port))
        self.server.listen(10)
        self.isloop = False
        self.flag = False
        self.conn= []
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.reconn = reconn
        self.struct=[]#[[远端套接字，本地套接字，活动中,插件],....]
        self.queue = {}
        self.outputs = []
        self.inputs=[]
    def load_plugin(self,object):
        self.mode = object
    def stop(self):
        self.flag = True
        print("线程已经停止了")
    def __set_get(self,arg1,arg2=None):
        '''
        设置或者查询
        :param arg1: 如果只有这个字段，则默认是查询
        :param arg2: 设置这个字段，则是添加包,第二个务必为本地套接字
        :return: struct的子结构体
        '''
        if not arg2:
            for i in self.struct:
                if arg1 in i:
                    return i,i[0] if arg1 is i[1] else i[1]
                else:
                    return None,None
            return None, None
        else:
            package = [arg1,arg2,True,None]
            self.struct.append(package)
            self.queue[arg1] = queue.Queue()
            self.queue[arg2] = queue.Queue()
            return package,None

    def __connect(self,remote_host,remote_port):
        try:
            s_client = socket.socket()
            s_client.connect((remote_host, remote_port))
            print("连接成功")
            return s_client
        except:
            print("连接失败")
            return None
    def __memclear(self):
        for i in self.struct:
            if self.queue[i[0]].empty() and self.queue[i[1]].empty() and i[2] is False:
                self.struct.remove(i)
                if i[0] in self.inputs:
                    self.inputs.remove(i[0])
                elif i[1] in self.inputs:
                    self.inputs.remove(i[1])
                elif i[0] in self.outputs:
                    self.outputs.remove(i[0])
                elif i[1] in self.outputs:
                    self.outputs.remove(i[1])
            # for i in self.outputs:
            #     pass
    def __disconnect(self,conn):
        print("用户退出", conn)
        conn.close()
        if conn in self.inputs:
            self.inputs.remove(conn)
        elif conn in self.outputs:
            self.outputs.remove(conn)

        package, s2 = self.__set_get(conn)
        if not package:
            return
        package[2] = False
    def __handle(self):
        self.inputs.append( self.server)

        while True:
            if self.flag:
                return

            # print(self.inputs,self.outputs)
            self.__memclear()
            r,w,e = select.select(self.inputs,self.outputs,self.inputs)
            # 读线程
            for s in r:
                if s is self.server:
                    # 新用户进入
                    conn,addr = self.server.accept()

                    # 为新用户绑定远端套接字
                    i = 0
                    flag=True
                    while True:
                        i += 1
                        cli = self.__connect(self.remote_host, self.remote_port)
                        if cli:
                            break
                        elif i == self.reconn and self.reconn != 0 or self.reconn == -1:
                            print("到达最大重连次数还未成功。断开连接.")
                            conn.close()
                            flag = False
                            break
                        time.sleep(3)
                    if flag:
                        # 如果绑定远端套接字成功则加入处理列表
                        self.inputs.append(conn)
                        # 远端套接字也要作为收管道进行handle
                        self.inputs.append(cli)
                        self.__set_get(cli,conn)
                else:
                    # 说明是老用户进入

                    try:
                        recv = s.recv(20480)
                    except:
                        self.__disconnect(s)
                        continue

                    if not recv or len(recv) <0:
                        # 没消息了
                        self.__disconnect(s)
                        continue
                    else:
                        self.queue[s].put(recv)
                        self.outputs.append(s)
            # 写线程
            for s in w:
                package,s2 = self.__set_get(s)
                if not package:
                    self.__disconnect(s)
                    continue
                try:
                    send_data = self.queue[s].get_nowait()
                except queue.Empty:
                    self.__disconnect(s)
                    continue
                else:
                    s2.sendall(send_data)
                    if package[2] is False:
                        self.__disconnect(s)
                    else:
                        self.outputs.remove(s)
            for s in e:
                print("有错误。")
                self.__disconnect(s)
                continue

    def start(self,thread=False):
        if self.isloop:
            print("线程正在运行中。")
            return None
        self.isloop = True
        if thread:
            threading.Thread(target=self.__handle,args=()).start()
        else:
            self.__handle()
class httproxy(object):
    '''
    copyright from <PythonProxy.py> modified by bakabie
    '''
    def __init__(self,port,timeout=60):
        self.s = socket.socket()
        self.s.bind(("0.0.0.0",port))
        self.s.listen(10)
        self.timeout = timeout

        self.BUFLEN = 8192
        self.VERSION = 'Python Proxy/0.1.1 modified by bakabie'
        self.HTTPVER = 'HTTP/1.1'
    def __get_base_header(self,client):
        client_buffer=""
        while 1:
            client_buffer += client.recv(self.BUFLEN).decode()
            end = client_buffer.find('\n')
            if end != -1:
                break
        print('%s' % client_buffer[:end])  # debug
        data = (client_buffer[:end + 1]).split()
        client_buffer = client_buffer[end + 1:]
        data.append(client_buffer)

        return data

    def _read_write(self,client,target):
        time_out_max = self.timeout / 3
        socs = [client, target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(self.BUFLEN)
                    if in_ is client:
                        out = target
                    else:
                        out = client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break
    def _connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i + 1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        target = socket.socket(soc_family)
        target.connect(address)
        return target
    def __handle(self,client,address):
        method,path,protocol,client_buffer =self.__get_base_header(client)
        if method == 'CONNECT':
            target = self._connect_target(path)
            client.send((self.HTTPVER + ' 200 Connection established\n' +
                        'Proxy-agent: %s\n\n' % self.VERSION).encode())
            self._read_write(client=client,target=target)
            client.close()
            target.close()
        elif method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            path = path[7:]
            i = path.find('/')
            host = path[:i]
            path2 = path[i:]
            target = self._connect_target(host)
            target.send(('%s %s %s\n' % (method, path2, protocol) +
                        client_buffer).encode())
            self._read_write(client=client,target=target)
            client.close()
            target.close()

    def __real_start(self):
        while True:
                conn,address = self.s.accept()
                threading.Thread(target=self.__handle,args=(conn,address)).start()
    def start(self,thread=False):
        if thread:
            threading.Thread(target=self.__real_start)
        else:
            self.__real_start()
class myHoleServer(object):
    def __init__(self,remote_address,username,passwd):
        pass
    def register_identify(self,host):
        """
        register the domain to handle,while remote server receive the\
        http packet,they whill transfer it to you or other according to this identifier.

        :param host: identifier
        :return:
        """
    def start(self,service=False):
        """

        :param service:
        :return:
        """
        pass
class myHoleClient(object):
    def __init__(self,port):
        pass
    def start(self,service=False):
        pass
class socks5proxy(object):
    def __init__(self,port,username="",password=""):
        self.SOCKS_VERSION = 5
        self.s = socket.socket()
        self.s.bind(("0.0.0.0", port))
        self.s.listen(10)
class http2socks5(object):
    def __init__(self,httproxy_host,httproxy_port,local_socks5_port):
        pass
    def start(self,thread=False):
        pass
class socks2http(object):
    def __init__(self,socks5_host,socks5_port,local_http_port,socks5_username=None,socks5_passwd=None):
        pass
    def start(self,thread=False):
        pass
class httproxy2udp(object):
    def __init__(self,remote_server,port,timeout=60):
        self.remote_server = remote_server
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fake_dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fake_dns.bind(("0.0.0.0",53))
        self.s = socket.socket()
        self.s.bind(("0.0.0.0",port))
        self.s.listen(10)
        self.timeout = timeout
        # self.stack_index = {}# 0 没读 1 读了
        self.data_stacks = {}
        self.BUFLEN = 8192
        self.VERSION = 'Python Proxy on dns 53 udp version/0.1.1 modified by bakabie'
        self.HTTPVER = 'HTTP/1.1'
        threading.Thread(target=self._sweeper_).start()
        threading.Thread(target=self.fake_dns).start()
    def __get_base_header(self,client):
        client_buffer=""
        while 1:
            client_buffer += client.recv(self.BUFLEN).decode()
            end = client_buffer.find('\n')
            if end != -1:
                break
        print('%s' % client_buffer[:end])  # debug
        data = (client_buffer[:end + 1]).split()
        client_buffer = client_buffer[end + 1:]
        data.append(client_buffer)

        return data
    def _sweeper_(self):
        while True:
            for i in self.data_stacks.keys():
                if int(time.time())-int(i)>=self.timeout
            time.sleep(self.timeout)
    def _fake_dns_server(self):
        while True:
            data, addr = s.recvfrom(20480)
            if not data:
                continue

            data=data.encode()
            packet = data[data.find("!#strt#!"):data.find("~#end#~")+7]# 愚蠢而又低效率的方案
            if not packet:
                continue
            timestamp = packet[packet.find("!#strt#!")-8:packet.find("!timestamp$")]
            if not timestamp:
                continue
            data = packet[packet.find("$trued#!")-8:packet.find("~#end#~")]
            if int(timestamp)-int(time.time()) > self.timeout:
                continue
                # 超时丢弃
            if timestamp not in self.data_stacks:
                self.data_stacks[timestamp] = data
                

    def _read_write(self,client,target):
        time_out_max = self.timeout / 3
        socs = [client, target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(self.BUFLEN)
                    if in_ is client:
                        out = target
                    else:
                        out = client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break
    def _get_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i + 1:])
            host = host[:i]
        else:
            port = 80
        return (host,port)
    def __handle(self,client,address):
        method,path,protocol,client_buffer =self.__get_base_header(client)
        if method == 'CONNECT':
            target = self._get_target(path)
            client.send((self.HTTPVER + ' 200 Connection established\n' +
                        'Proxy-agent: %s\n\n' % self.VERSION).encode())
            self._read_write(client=client,target=target)
            client.close()
            
        elif method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            path = path[7:]
            i = path.find('/')
            host = path[:i]
            path2 = path[i:]
            target = self._connect_target(host)
            target.send(('%s %s %s\n' % (method, path2, protocol) +
                        client_buffer).encode())
            self._read_write(client=client,target=target)
            client.close()
            target.close()

    def __real_start(self):
        while True:
                conn,address = self.s.accept()
                threading.Thread(target=self.__handle,args=(conn,address)).start()
    def start(self,thread=False):
        if thread:
            threading.Thread(target=self.__real_start)
        else:
            self.__real_start()
if __name__ =="__main__":
    text="""
    ########################MY HOLE#########################
    # WHAT 'S THIS?  JUST A SOCKETS/WEB TOOLKIT FOR MYSELF #
    # HOW TO USE IT?                                       #
    # <MHOLE.PY> -M [MOD] -B [LOCAL PORT]                  #
    #           -R [REMOTEADDRESS:PORT] -N [RECONNECT NUM] #
    # YOU CAN USE THESE MOD:                               #
    # TCP2TCP:  A SOCKET TRANSFER TOOLKIE. SET LOCAL PORT  #
    #         AND REMOTE PORT ABD RECONNECT NUMBER. ANY    #
    #         DATE PASS HERE WILL TRANSFER TO OTHER WAT.   #
    #        OF COUSE,THIS CAN USE TO  SOLE PLCAING AGENCY #
    # HTTPROXY: A SIMPLE HTTP PROXY FROM <PYTHONPROXY.PY>  #
    ########################################################
    """
    print(text)
