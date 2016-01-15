# -*- coding: utf8 -*-

import os
import time
import logging
from functools import wraps
from socket import socket, AF_INET, SOCK_DGRAM, error as SocketEror


log = logging.getLogger(name='carbonstat')


class MetricTimer(object):
    def __init__(self, metric):
        self.metric = metric
        self.start()

    def start(self):
        """Start measuring execution time"""
        self.running = True
        self.start_time = time.time()

    def stop(self):
        """Stop timer and save execution time"""
        if self.running:
            self.metric.add_ex(time.time() - self.start_time)
            self.running = False
        else:
            raise Exception('Timer is not running')

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.running:
            self.stop()


class Metric(object):
    """
    simple_metric = Metric('foo')
    for i in range(10):
        foo(i)
        simple_metric.add(1)  # increment simple metric value
    print(metric.simple_value)  # 10

    extended_metric = Metric('bar')
    with extended_metric.timer() as timer:
        for i in range(10):
            timer.start()
            bar(i)
            timer.stop()
    print(metric.min, metric.max, metric.avg)
    # here metric.avg is sum of [t(bar(0)), ..., t(bar(9))] / 10
    #      metric.min is min of [t(bar(0)), ..., t(bar(9))]
    #      metric.max is max of [t(bar(0)), ..., t(bar(9))]

    with extended_metric.timer():
        bar(10)
        # stopping the timer with exit
    """
    def __init__(self, name):
        self.name = name
        self.simple_value = None
        self.simple_timestamp = None
        self.min, self.max = float('inf'), float('-inf')
        self.sum, self.len = 0, 0
        self.timestamp = None
        self.accumulate = False
        self.extended = False

    def add(self, value):
        """Add a value to a simple value stored in metric"""
        try:
            self.simple_value += value
        except TypeError:
            self.simple_value = value
        self.simple_timestamp = time.time()

    def incr(self, amount=1):
        """Increment a simple value stored in metric"""
        self.add(amount)

    def decr(self, amount=1):
        """Decrement a simple value stored in metric"""
        self.add(-amount)

    def set(self, value):
        """Set a value to a simple value stored in metric"""
        self.simple_value = value
        self.simple_timestamp = time.time()

    def add_ex(self, value):
        """
        Add a value to "set" of values stored in metric

        For this "set" of values we can calculate min., max., avg. values.
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

    def timer(self):
        """Get timer for measuring execution time inside context manager"""
        self.extended = True
        return MetricTimer(self)


class CarbonMetric(Metric):
    def __init__(self, name, namespace):
        super(CarbonMetric, self).__init__(name)
        self.ns = namespace
        self.name = name

    def __str__(self):
        name = '%s.%s' % (self.ns, self.name) if self.ns else self.name
        ret = ''
        if self.simple_value is not None:
            ret += '%s %s %f\n' % (name, self.simple_value,
                                   self.simple_timestamp)
        if self.len:
            ret += '\n'.join(['%s.%s %s %s' % (name, value_name,
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

    with stat.timer('extended') as timer:
        for i in range(10):
            timer.start()
            bar(i)
            timer.stop()
    print(stat['extended'].min, stat['extended'].max, stat['extended'].avg)
    # here stat['extended'].avg is sum of [t(bar(0)), ..., t(bar(9))] / 10
    #      stat['extended'].min is min of [t(bar(0)), ..., t(bar(9))]
    #      stat['extended'].max is max of [t(bar(0)), ..., t(bar(9))]

    with stat.timer('extended'):
        bar(10)
        # stopping the timer with exit

    stat.send()  # send packet to Carbon
    """
    def __init__(self, host='127.0.0.1', port=2003, namespace=''):
        self.host = host
        self.port = port
        self.ns = namespace
        self.metrics = {}
        self.__socket = None
        self.__heartbeat = -1
        self.__sending = False

    def __getitem__(self, name):
        """Get metric object with name `name`"""
        return self.metrics.setdefault(name, CarbonMetric(name, self.ns))

    @property
    def socket(self):
        if not self.__socket:
            try:
                self.__socket = socket(AF_INET, SOCK_DGRAM)
            except SocketEror as e:
                log.error('Could not create socket: %s', str(e))
                raise

        return self.__socket

    @property
    def heartbeat(self):
        self.__heartbeat = (self.__heartbeat + 1) % 2 ** 32
        return self.__heartbeat

    def set_namespace(self, namespace):
        """Set new namespace"""
        self.ns = namespace

    def timer(self, metric_name):
        """
        Get timer for measuring execution time inside context manager

        with stat.timer('foo') as timer:
            for a in range(10):
                timer.start()
                # some your code
                timer.stop()

        stat.send()  # send info about execution of your code 10 times
        """
        return self[metric_name].timer()

    def timeit(self, metric_name):
        """
        Decorator for measuring execution time of your function

        @stat.timeit('foo')
        def foo(a):
            sleep(a)

        for a in range(10):
            foo(a)

        stat.send()  # send info about execution of `foo` function 10 times
        """
        def decorator(function):
            @wraps(function)
            def wrapped(*args, **kwargs):
                with self.timer(metric_name):
                    return function(*args, **kwargs)
            return wrapped
        return decorator

    def make_header(self):
        header = 'heartbeat {} {}\n'.format(self.heartbeat, time.time())
        if self.ns:
            header = '{}.{}'.format(self.ns, header)
        return header

    def send(self):
        """Send group of collected metrics and clear the group"""
        if self.__sending:
            return
        else:
            self.__sending = True

        metrics, self.metrics = self.metrics, {}

        packet = self.make_header()
        for metric in metrics.values():
            if metric.accumulate:
                if not metric.extended:
                    self[metric.name].add(metric.simple_value)
                else:
                    self.metrics[metric.name] = metric
                self[metric.name].accumulate = True
            packet += str(metric)

        try:
            self.socket.sendto(packet, (self.host, self.port))
        except SocketEror as e:
            log.debug('Packet:\n%s', packet)
            log.error('Could not send packet to Carbon %s: %s', self.host, str(e))
            self.metrics.update(metrics)
        finally:
            self.__sending = False


host = os.environ.get('CARBON_HOST', '127.0.0.1')
port = int(os.environ.get('CARBON_PORT', '2003'))
namespace = os.environ.get('CARBON_NAMESPACE', 'carbonstat')
stat = CarbonStat(host=host, port=port, namespace=namespace)
