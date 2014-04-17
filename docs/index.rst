====
RAET
====
by SaltStack
============

.. rubric:: Reliable Asynchronous Event Transport Protocol

Contents:

.. toctree::
    :maxdepth: 1

    topics/introduction
    topics/installation

Motivation
==========

Modern large scale distributed application architectures where components are
distributed across the internet on multiple hosts and multiple CPU cores are
often based on a messaging or event bus that allows the various distributed
components to communicate asynchronously with each other. Typically the
messaging bus is some form of messaging queue service such as AMQP or ZeroMQ.
The message bus supports what is commonly referred to as a publish/subscribe
methodology for information exchange.

While there are many advantages to a full featured message queuing service, one
of the disadvantagesis the inability to manage performance at scale.

A message queuing service performs two distinct but complementary functions.

- The first is asynchronous transport of messages over the internet.

- The second is message queue management, that is, the identification,
  tracking, storage, and distribution of messages between publishers and
  subscribers via queues.

One of the advantages of a message queuing service for many applications is
that the service hides the complexities of queue management from the clients
behind an API. The disadvantage is that at scale where the volume of messages,
the timing of messages, and the associated demands on  memory, network, and cpu
capacity become critical, the client has little ability to tune the service for
performance. Often MQ services become bottlenecks for the distributed
application. The more complicated MQ services like AMQP tend to be unreliable
under load.

Separating the asynchrounous event over network transport function from the
message queue management allows independant tuning at scale of each function.

Moreover, most if not all of the MQ services that we are familiar with are
based on TCP/IP which due to the way it handles connection setup and teardown
as well as failed connections in order to support streams tends to add high
latency to the network communications and is not therefore not well suited for
the asynchronous nature of distibuted event driven application communications.

Because UDP/IP has lower latency and is connectionless, it scales better, but
it has the serious drawback that it is not reliable. What it needed is a tuned
transport protocol adds reliability to UDP/IP without sacrificing latency and
scalability. A transactioned protocol, is much more appropriate for providing
reliablity to asynchronous event transport than a streaming protocol.

In addition, because most MQ services are based on TCP/IP they tend to also use
HTTP and therefore TLS/SSL for secure communications. While using HTTP provides
easy integration with web based systems, it is problematic for high performant
systems and TLS is also problematic as a security system both from performance
and vulnerabilty aspects. Elliptic Curve Cryptography provides increases in
security with lower performance requires over other approaches. LibSodium
provides an open source Elliptic Curve Cryptographic library with support for
both authentication and encryption. The CurveCP protocol is based on LibSodium
and provides a handshake protocol for bootstrapping secure network exchanges of
information.

Finally, one of the best ways to manage and fine tune processor resources (cpu,
memory, network) in distrubted concurrent event driven applications is to use
something called micro-threads. A microthread is typically and in-language
feature that allows logical concurrency with no more overhead than a function
call. Micro threading uses cooperative multi-tasking instead of threads and/or
processes and avoids many of the complexities of resource contention, context
switching, and interprocess communications while providing much higher total
performance.

The main limitation of a micro-threaded application is that it is constrained
to one CPU core because it runs in one process. To enable full utilization of
all CPU cores, the application needs to be able to run at least one process per
CPU core. This requires on host inter-process communications. But instead of
one process per logical concurrent function which is the conventional approach
to multi-processing, A micro-threaded multi-process application has one
micro-thread per logical concurrent function and the total number of
micro-threads is distributed amoungst the minimum number of processes, no more
than the number of cpu cores. This optimizes the use of the cpu power while
minimizes the overhead of process context switching.

An example of a framework that uses this type of micro-threaded but
multi-process architecture is Erlang. Indeed, Erlang provided confirmation that
the approach to RAET could be viable. Unfortunately, the Erlang ecosystem is
somewhat limited and the language itself uses what one might describe as a very
unfortunate syntax. Since we have extensive background in Python we wanted to
leverage the richness of the Python ecosystem but still be able to develop
distributed applications on a micro-threaded multi-process capable framework.


RAET is designed to provide secure reliable scalable asynchronous message/event
transport over the internet in a micro-threaded multi-process application
framework that uses UDP for interhost communication and LibSodium for
authentication, encryption and the CurveCP handshake for secure bootstrap.

The queue management and micro-threaded application support is provided by
Ioflo. RAET is a complementary project to Ioflo in that RAET enables multiple
Ioflo applications to work together over a network as part of a distributed
application.

The primary use case and motivating problem that resulted in the development of
RAET was the need to enable SaltStack to scale better. SaltStack is a remote
execution and configuration management platform written in Python. SaltStack
uses ZeroMQ (0MQ) as is message bug or message queuing service. ZeroMQ is based
on

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

