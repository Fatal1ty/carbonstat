# -*- coding: utf8 -*-

import os
import time
import logging
from socket import socket, AF_INET, SOCK_DGRAM, error as SocketEror


class MetricTimer(object):
    def __init__(self, metric):
        self.metric = metric
        self.start()

    def start(self):
        self.started_at = time.time()

    def stop(self):
        self.metric.add_ex(time.time() - self.started_at)


class Metric(object):
    """
    simple_metric = Metric('foo')
    for i in range(10):
        foo(i)
        simple_metric.add(1)  # increment simple metric value
    print(metric.simple_value)  # 10

    extended_metric = Metric('bar')
    with extended_metric as timer:
        for i in range(10):
            timer.start()
            bar(i)
            timer.stop()
    print(metric.min, metric.max, metric.avg)
    # here metric.avg is sum of [t(bar(0)), ..., t(bar(9))] / 10
    #      metric.min is min of [t(bar(0)), ..., t(bar(9))]
    #      metric.max is max of [t(bar(0)), ..., t(bar(9))]

    with extended_metric as timer:
        bar(10)
        timer.stop()  # starting time is time when we entered in context manager
    """
    def __init__(self, name):
        self.name = name
        self.simple_value = None
        self.simple_timestamp = None
        self.min, self.max = float('inf'), float('-inf')
        self.sum, self.len = 0, 0
        self.timestamp = None

    def __enter__(self):
        """Начало измерения времени метрики"""
        return MetricTimer(self)

    def __exit__(self, *args, **kwargs):
        """Окончание измерения времени метрики"""
        pass

    def add(self, value):
        """Добавление value к существующему значению в метрике"""
        try:
            self.simple_value += value
        except TypeError:
            self.simple_value = value
        self.simple_timestamp = time.time()

    def add_ex(self, value):
        """
        Расширенное добавление значения к метрике

        Для добавляемых таким образом значений можно получить min, avg, max.
        """
        self.sum += value
        self.len += 1
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value
        self.timestamp = time.time()

    @property
    def avg(self):
        return self.sum / float(self.len)


class CarbonMetric(Metric):
    def __init__(self, name, namespace):
        super(CarbonMetric, self).__init__(name)
        self.ns = namespace
        self.name = name

    def __str__(self):
        name = '%s.%s' % (self.ns, self.name) if self.ns else self.name
        ret = ''
        if self.simple_value is not None:
            ret += '{} {} {}\n'.format(name, self.simple_value,
                                       self.simple_timestamp)
        if self.len:
            ret += '\n'.join(['{}.{} {} {}'.format(name,
                                                   value_name,
                                                   getattr(self, value_name),
                                                   self.timestamp)
                              for value_name in ['min', 'avg', 'max']]) + '\n'
        return ret


class CarbonStat(object):
    """
    stat = CarbonStat(host='127.0.0.1', port=2003)

    for i in range(10):
        foo(i)
        stat['simple'].add(1)  # increment simple metric value
    print(stat['simple'].simple_value)  # 10

    with stat['extended'] as timer:
        for i in range(10):
            timer.start()
            bar(i)
            timer.stop()
    print(stat['extended'].min, stat['extended'].max, stat['extended'].avg)
    # here stat['extended'].avg is sum of [t(bar(0)), ..., t(bar(9))] / 10
    #      stat['extended'].min is min of [t(bar(0)), ..., t(bar(9))]
    #      stat['extended'].max is max of [t(bar(0)), ..., t(bar(9))]

    with stat['extended'] as timer:
        bar(10)
        timer.stop()  # starting time is time when we entered in context manager

    stat.send()  # send packet to Carbon
    """
    def __init__(self, host='127.0.0.1', port=2003, namespace=''):
        """Открывает UDP сокет на удаленный хост и ждет"""
        self.heartbeat = 0
        self.host = host
        self.port = port
        self.ns = namespace
        self.metrics = {}
        self.socket = None

    def __getitem__(self, name):
        return self.metrics.setdefault(name, CarbonMetric(name, self.ns))

    def send(self):
        """Посылает метрики на хост группой и очищает группу"""
        if not self.socket:
            try:
                self.socket = socket(AF_INET, SOCK_DGRAM)
            except SocketEror as e:
                logging.warning('Could not open socket: %s', str(e))
                return
        self.heartbeat += 1
        self.heartbeat %= 2 ** 32
        heartbeat = (self.heartbeat - 1) % 2 ** 32
        metrics, self.metrics = self.metrics, {}
        header = 'heartbeat {} {}\n'.format(heartbeat, time.time())
        if self.ns:
            header = '{}.{}'.format(self.ns, header)
        packet = header + ''.join([str(m) for m in metrics.values()])
        try:
            self.socket.sendto(packet, (self.host, self.port))
        except SocketEror as e:
            logging.error('Could not send packet: %s', str(e))
            self.metrics.update(metrics)
            self.socket = None


host = os.environ.get('CARBON_HOST')
port = int(os.environ.get('CARBON_PORT', '2003'))
if host:
    stat = CarbonStat(host=host, port=port, namespace='ns')
else:
    stat = None