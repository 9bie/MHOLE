# coding:utf-8
# 搬运模块
import socket
import select

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
    copyright from <PythonProxy.py>
    '''
    def __init__(self,port,timeout=60):
        self.s = socket.socket()
        self.s.bind(("0.0.0.0",port))
        self.s.listen(10)
        self.timeout = timeout
        self.client_buffer=''
        self.BUFLEN = 8192
        self.VERSION = 'Python Proxy/0.1.1 modified from bakabie'
        self.HTTPVER = 'HTTP/1.1'
    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(self.BUFLEN).decode()
            if not self.client_buffer:
                return None,None,None
            end = self.client_buffer.find('\n')
            print(end)
            if end != -1:
                break
        print('%s' % self.client_buffer[:end])  # debug
        data = (self.client_buffer[:end + 1]).split()
        self.client_buffer = self.client_buffer[end + 1:]
        return data
    def _connect_target(self, host):
        i = host.find(':')
        if i!=-1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family)
        self.target.connect(address)
    def _read_write(self):
        time_out_max = self.timeout/3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(self.BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break
    def method_CONNECT(self):
        self._connect_target(self.path)
        self.client.send((self.HTTPVER + ' 200 Connection established\n' +
                         'Proxy-agent: %s\n\n' % self.VERSION).encode())
        self.client_buffer = ''
        self._read_write()
    def method_others(self):
        self.path = self.path[7:]
        i = self.path.find('/')
        host = self.path[:i]
        path = self.path[i:]
        self._connect_target(host)
        self.target.send(('%s %s %s\n'%(self.method, path, self.protocol)+self.client_buffer).encode("utf-8"))
        self.client_buffer = ''
        self._read_write()
    def __real_start(self):
        while True:
            self.client,self.address = self.s.accept()
            self.method, self.path, self.protocol = self.get_base_header()

            if self.method == 'CONNECT':
                print("CONNECT")
                self.method_CONNECT()
            elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                                 'DELETE', 'TRACE'):
                print("OHTER")
                self.method_others()
            self.client.close()
            self.target.close()
    def start(self,thread=False):
        if thread:
            threading.Thread(target=self.__real_start,args=()).start()
        else:
            self.__real_start()
if __name__ =="__main__":
    a= httproxy(8082)
    a.start()
