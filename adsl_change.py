# coding=utf-8
# python2
import redis
import re
import os
import time

CONFIG_SERVER = 'redis://:redis7001@47.93.126.172:7001/0'
order_dict = {'vpsmokahr{}'.format(i): i for i in range(1, 200)}
order_dict['vpsbeijing'] = 0


class VpsMornitor:
    redisdb = redis.from_url(CONFIG_SERVER)

    @staticmethod
    def client_name():
        try:
            with open('/root/.bashrc', 'r') as f:
                client_S = ''.join(f.readlines()).split('CLIENT=')[-1]
                print(client_S.replace('\n', ''))
                return client_S.replace('\n', '')
        except Exception as e:
            print(type(e), str(e))
            return ''

    @staticmethod
    def get_ip():
        """:return ip:str None"""
        try:
            ifconfig = os.popen('ifconfig')
            ifconfig_S = ''.join(ifconfig.readlines())
            print(ifconfig_S)
            if 'ppp0' in ifconfig_S:
                _s = ifconfig_S.split('ppp0')[-1]
                _ip = re.search('inet[\s]*(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})', _s)
                if _ip:
                    ip = _ip.group(1)
                    return ip
        except Exception as e:
            print(type(e), str(e))

    @staticmethod
    def disconnect():
        """:return 'ok' None"""
        for i in range(3):
            os.system('adsl-stop')
            ifconfig = os.popen('ifconfig')
            if 'ppp0' not in ''.join(ifconfig.readlines()):
                print("disconnect ok")
                return 'ok'
        return False

    def gen_new_ip(self):
        """:return ip:str None"""
        for i in range(3):
            self.disconnect()
            try:
                os.system('adsl-start')
                return self.get_ip()
            except Exception as e:
                print(type(e), str(e))
                time.sleep(6)
        return

    def send_signal(self, cli_name):
        try:
            t = time.time()
            ts = time.strftime('%m-%d %H:%M:%S', time.localtime(t))
            if cli_name in order_dict:
                self.redisdb = redis.from_url(CONFIG_SERVER)
                proxy_key = 'proxy' + str(order_dict[cli_name])
                signal = 'good_' + ts
                self.redisdb.hset('vps_monitor', proxy_key, signal)
                print(proxy_key, 'send signal good')
                return True

        except Exception as e:
            print (type(e), str(e))

    def send_proxy(self, cli_name, ip):
        try:
            response = ''.join(os.popen('curl myip.ipip.net').readlines())
            if ip in response:
                print('ip curl ok: ')
            else:
                print('err: ', response)
                return
            if cli_name in order_dict:
                proxy_key = 'proxy' + str(order_dict[cli_name])
                proxy = 'http://' + ip + ':41122'
                self.redisdb = redis.from_url(CONFIG_SERVER)
                print ('will send: ', proxy_key, proxy)
                self.redisdb.hset('proxies', proxy_key, proxy)
                self.send_signal(cli_name)
                print(proxy_key, 'send proxy good')
                return True
            else:
                print('client name not right', cli_name)
        except Exception as e:
            print(type(e), str(e))

    def is_proxy_good(self, cli_name):
        if cli_name in order_dict:
            proxy_key = 'proxy' + str(order_dict[cli_name])
            try:
                self.redisdb = redis.from_url(CONFIG_SERVER)
                redobj = self.redisdb.hget('proxies', proxy_key)
                if redobj is None:
                    print(proxy_key, 'status None')
                    return False
                elif redobj == b'failed':
                    print(proxy_key, 'status failed')
                    return False
                elif redobj != b'failed':
                    print(proxy_key, 'status good')
                    return True
                else:
                    return False
            except Exception as e:
                print(type(e), str(e))
                return 'err'

    def loop(self):
        while True:
            t = time.time()
            ts = time.strftime('%m-%d %H:%M:%S', time.localtime(t))
            cli_name = self.client_name()
            if self.is_proxy_good(cli_name) is True:
                self.send_signal(cli_name)
            else:
                ip = self.gen_new_ip()
                time.sleep(6)
                self.send_proxy(cli_name, ip)
            print('-' * 30, ts,)
            time.sleep(1)


if __name__ == '__main__':
    time.sleep(1)
    vm = VpsMornitor()
    vm.loop()
