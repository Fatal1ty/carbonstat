carbonstat
==========

.. image:: https://img.shields.io/pypi/v/carbonstat.svg
   :target: https://pypi.python.org/pypi/carbonstat

.. image:: https://img.shields.io/pypi/pyversions/carbonstat.svg
   :target: https://pypi.python.org/pypi/carbonstat

.. image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://raw.githubusercontent.com/Fatal1ty/carbonstat/master/LICENSE

Metrics collection agent for `Carbon`_. It allow you to collect some
metrics about your code and measure execution time.

Installation
------------

Install via pip:

::

        pip install carbonstat

Basic usage
-----------

You can just import ``carbonstat.stat`` instance and play with it:

.. code:: python

        from carbonstat import stat

        def foo():
            print 'Hello, world!'

        foo()
        foo()

        stat['foo.count'].add(2)  # save `foo.count` metric as execution counter

        stat.send()  # send packet to Carbon with `foo.count` metric value

All packets are sent via udp to *127.0.0.1:2003* by default. You can
change default destination address via environment variables
``$CARBOH_HOST`` and ``$CARBON_PORT``.

You can combine multiple metrics in one ``CarbonStat`` instance too:

.. code:: python

        def foo():
            print 'Hello from foo!'

        def bar():
            print 'Hello from bar!'

        foo()
        foo()
        bar()

        stat['foo.count'].add(2)
        stat['bar.count'].add(1)

        stat.send()  # send packet to Carbon with two metrics

Advanced usage
--------------

You can measure execution time of code blocks with convenient context
manager:

.. code:: python

        stat = CarbonStat(host=192.168.0.1, port=2003)

        def foo(sec):
            sleep(sec)
            print 'Hello after %d seconds!' % sec

        with stat.timer('foo.time') as timer:
            timer.start()  # measure first
            foo(3)
            timer.stop()

            timer.start()  # measure again
            foo(5)
            timer.stop()

        stat.send()  # send packet:
        #               heartbeat    0 timespamp
        #               foo.time.min 3 timestamp
        #               foo.time.avg 4 timestamp
        #               foo.time.max 5 timestamp

Or you can do it simpler:

.. code:: python

        def foo(sec):
            sleep(sec)
            print 'Hello after %d seconds!' % sec

        with stat.timer('foo.time'):
            foo(3)
        with stat.timer('foo.time'):
            foo(5)

        stat.send()  # send packet like above

You can even decorate your function and measure it’s execution time
while calling it:

.. code:: python

        @stat.timeit('foo.time')
        def foo(sec):
            sleep(sec)
            print 'Hello after %d seconds!' % sec

        foo(3)
        foo(5)

        stat.send()  # send packet like above

Extra
-----

In some cases you may need to save the value of any metric after sending
the packet to Carbon. You can do it by setting ``accumulate`` attribute
to ``True``:

\`\`\`

.. _Carbon: https://github.com/graphite-project/carbon