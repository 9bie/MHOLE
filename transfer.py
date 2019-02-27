# coding:utf-8
# 搬运模块
import socket
import select

import threading
import queue
import time
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
        self.struct=[]#[[远端套接字，本地套接字，活动中],....]
        self.queue = {}
        self.outputs = []
        self.inputs=[]
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
                    return i
        else:
            package = [arg1,arg2,True]
            self.struct.append(package)
            self.queue[arg1] = queue.Queue()
            self.queue[arg2] = queue.Queue()
            return package

    def __connect(self,remote_host,remote_port):
        try:
            s_client = socket.socket()
            s_client.connect((remote_host, remote_port))
            print("连接成功")
            return s_client
        except:
            print("连接失败")
            return None
    def __disconnect(self,package):
        print("用户退出")
        package[0].close()
        package[1].close()
        del self.queue[package[0]]
        del self.queue[package[1]]
        if package[0] in self.inputs:
            self.inputs.remove(package[0])
        elif package[1] in self.inputs:
            self.inputs.remove(package[1])
        elif package[0] in self.outputs:
            self.outputs.remove(package[0])
        elif package[1] in self.outputs:
            self.outputs.remove(package[1])
        self.struct.remove(package)
    def __handle(self):
        self.inputs.append( self.server)

        while True:
            if self.flag:
                return
            print(self.inputs,self.outputs)
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
                    package = self.__set_get(s)
                    try:
                        recv = s.recv(20480)
                    except:
                        self.__disconnect(package)

                    if not recv:
                        # 没消息了
                        self.__disconnect(package)

                    else:
                        self.queue[s].put(recv)
                        if s not in self.outputs:
                            self.outputs.append(s)
            # 写线程
            for s in w:
                package = self.__set_get(s)
                try:
                    send_data = self.queue[s].get_nowait()
                except queue.Empty:
                    self.__disconnect(package)
                else:
                    if s is package[0]:
                        package[1].sendall(send_data)
                    else:
                        package[0].sendall(send_data)
                    self.outputs.remove(s)
            for s in e:
                print("有错误。")
                package=self.__set_get(s)
                self.__disconnect(package)

    def start(self,thread=False):
        if self.isloop:
            print("线程正在运行中。")
            return None
        self.isloop = True
        if thread:
            threading.Thread(target=self.__handle,args=()).start()
        else:
            self.__handle()


if __name__ =="__main__":
    a= tcp2tcp(801,"127.0.0.1",5000)
    a.start()
