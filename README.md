Oliver
=====

Oliver automatically adds things to your grocery list when you run out. You
just scan the item's barcode on its way into the trash.

Hardware
-----

I run Oliver on a [Raspberry Pi][raspberry-pi] under [Raspbian][raspbian]. I use
[this barcode scanner][scanner-amazon].


Software
-----

To install Oliver, run the included `install.py` as root on the target system. It
will walk you through the process of setting up any API accounts you'll need, and
then it'll install the software.

install script works for raspberrypi installed under Raspbian using Python 2.7 

Getting Help
-----
Submit Issues: [Issues][oliver-issues]
[raspberry-pi]: http://www.raspberrypi.org/
[raspbian]: http://www.raspbian.org/
[scanner-amazon]: http://www.amazon.com/gp/product/B0085707Z8/ref=oh_details_o03_s00_i03?ie=UTF8&psc=1
[oliver-issues]: https://github.com/nixamas/oliver/issues
