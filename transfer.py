# coding:utf-8
# 搬运模块
import socket
import select
import threading
import time
class tcp2tcp(object):
    def __init__(self,local_port,remote_host,remote_port,reconn=0):
        '''

        :param local_port: 本地监听端口
        :param remote_host: 远程主机地址
        :param remote_port: 远程主机端口
        :param reconn: 最大重连次数，设置为0则一直重连，每次间隔30s
        '''
        self.s_client = socket.socket()
        self.server = socket.socket()
        self.server.bind(("0.0.0.0", local_port))
        self.server.listen(10)
        self.isloop = False
        self.flag = False
        self.conn= []
        i = 0
        while True:
            i+=1
            if self.__connect(remote_host,remote_port):
                break
            elif i == reconn and reconn != 0:
                print("到达最大重连次数还未成功。断开连接")
            time.sleep(30)

    def __connect(self,remote_host,remote_port):
        try:
            socket =self.s_client.connect((remote_host, remote_port))
            return socket
        except:
            print("连接失败")
            return
    def __select(self,conn1,conn2):
        pass
    def start(self):
        if self.isloop:
            print("线程正在运行中。")
            return
        self.isloop = True
        while True:
            if self.flag :
                break
            conn,addr = self.server.accept()
            self.conn.append(conn)
