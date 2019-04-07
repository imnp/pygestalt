## Introduction

We believe that anyone should be able to build their own custom digital fabrication tools. Why? Because our tools shape our perspective, and it's high time we shaped them back. [Read about our philosophy here.](pages/philosophy.md)

pyGestalt helps you construct and configure control systems for your own automated machines, ranging from simple to crazy. Just two examples: [a plotter that writes love letters](https://vimeo.com/12068389), and a [Jacquard loom for weaving friendship bracelets](https://vimeo.com/70206561) ([including a web-based control system](http://www.friendshiploom.com)). 

We've observed that for most machine builders, the control system is the hardest element to take from 0 -> 1. Mechanics can start with humble hardware-store beginnings and be improved later. Moving your multi-axis machine in a coordinated manner, perhaps with a custom tool-head or sensors, is tougher to get off the ground.

The core idea driving pyGestalt is that you should be able to import and manipulate hardware as simply as you do a software library. Suppose you want to move your fancy automated cake decorator:


{% highlight python %}
import cakebot
myCakeBot = cakebot.virtualMachine()
myCakeBot.move(x=1, y=2, z=3)
{% endhighlight %}

pyGestalt extends this concept of modularity much further; your cakebot might be controlled by a collection of actuators and sensors, each of which is represented as a Python module. Later, you might decide to build a fleet of cakebots that take orders over the internet. pyGestalt helps you span the entire stack of machine design:
* build your own modular machine control elements
* connect control elements together into complete machine systems
* work with arrays of machines
* write browser-based user interfaces

## Getting Started
- [Tutorials](pages/tutorials.md)
- [Reference](pages/reference.md)
- [Philosophy](pages/philosophy.md)
- [Reading List](pages/readinglist.md)
