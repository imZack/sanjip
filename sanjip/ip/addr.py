#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sh
import netifaces
import ipcalc
import copy
import logging

# https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-net

# Used python modules:
# setuptools
#   https://pypi.python.org/pypi/setuptools
#
# ipcalc.py
#   https://github.com/tehmaze/ipcalc/
#
# sh.py
#   https://pypi.python.org/pypi/sh


_logger = logging.getLogger("sanji.ethernet.ip.addr")


def interfaces():
    """List all interfaces.

    Returns:
        A list of interface names. For example:

        ["eth0", "eth1", "wlan0"]

    Raises:
        FIXME
    """
    # ifaces=$(ip a show | grep -Eo "[0-9]: wlan[0-9]" | sed "s/.*wlan//g")
    # ifaces=$(ip a show | grep -Eo '[0-9]: eth[0-9]' | awk '{print $2}')
    try:
        ifaces = netifaces.interfaces()
        ifaces = [x for x in ifaces if not
                  (x.startswith("lo") or x.startswith("mon."))]
        return ifaces
    except Exception as e:
        _logger.info("Cannot get interfaces: %s" % e)
        raise e


def ifaddresses(iface):
    """Retrieve the detail information for an interface.

    Args:
        iface: interface name.

    Returns:
        A dict format data will be return. For example:

        {"mac": "",
         "link": 1,
         "inet": [{
             "ip": "",
             "netmask": "",
             "subnet": "",
             "broadcast": ""}]}

    Raises:
        ValueError: You must specify a valid interface name.
    """
    full = netifaces.ifaddresses(iface)

    info = {}
    try:
        info["mac"] = full[netifaces.AF_LINK][0]['addr']
    except Exception:
        info["mac"] = ""

    try:
        info["link"] = open("/sys/class/net/%s/operstate" % iface).read()
        if "down" == info["link"][:-1]:
            info["link"] = False
        else:
            info["link"] = open("/sys/class/net/%s/carrier" % iface).read()
            info["link"] = True if int(info["link"][:-1]) == 1 else False
    except Exception:
        info["link"] = False

    info["inet"] = []
    if netifaces.AF_INET not in full:
        return info

    for ip in full[netifaces.AF_INET]:
        item = copy.deepcopy(ip)
        if "addr" in item:
            item["ip"] = item.pop("addr")
            net = ipcalc.Network("%s/%s" % (item["ip"], item["netmask"]))
            item["subnet"] = str(net.network())
        info["inet"].append(item)

    return info


def ifupdown(iface, up):
    """Set an interface to up or down status.

    Args:
        iface: interface name.
        up: status for the interface, True for up and False for down.

    Raises:
        ValueError
    """
    if not up:
        dhclient(iface, False)
    try:
        sh.ip("link", "set", iface, "up" if up else "down")
    except Exception:
        raise ValueError("Cannot update the link status for \"%s\"."
                         % iface)


def dhclient(iface, enable, script=None):
    # Enable/0Disable the dhcp client and flush interface
    # dhclient -pf /var/run/dhclient-<iface>.pid <iface>
    # dhclient -r -pf /var/run/dhclient-<iface>.pid <iface>
    pid_file = "/var/run/dhclient-{}.pid".format(iface)
    try:
        sh.dhclient("-r", "-pf", pid_file, iface)
    except Exception as e:
        _logger.info("Failed to stop dhclient: %s" % e)
        pass

    conf_file = "/etc/dhcp/dhclient-{}.conf".format(iface)
    conf_data = """#MOXA configuration file for ISC dhclient for debian
option rfc3442-classless-static-routes code 121 = array of unsigned integer 8;
send host-name = gethostname();
request subnet-mask, broadcast-address, time-offset, routers,
        domain-name, domain-name-servers, domain-search, host-name,
        dhcp6.name-servers, dhcp6.domain-search,
        netbios-name-servers, netbios-scope, interface-mtu,
        rfc3442-classless-static-routes, ntp-servers;
option dhcp-client-identifier {};
"""  # noqa
    with open(conf_file, "w") as f:
        f.write(conf_data.format(ifaddresses(iface)["mac"]))

    if enable:
        if script:
            sh.dhclient(
                "-pf", pid_file, "-nw", "-cf", conf_file, "-sf", script, iface)
        else:
            sh.dhclient(
                "-pf", pid_file, "-nw", "-cf", conf_file, iface)


def ifconfig(iface, dhcpc, ip="", netmask="24", gateway="", script=None):
    """Set the interface to static IP or dynamic IP (by dhcpclient).

    Args:
        iface: interface name.
        dhcpc: True for using dynamic IP and False for static.
        ip: IP address for static IP
        netmask:
        gateway:

    Raises:
        ValueError
    """
    # TODO(aeluin) catch the exception?
    # Check if interface exist
    try:
        sh.ip("addr", "show", iface)
    except sh.ErrorReturnCode_1:
        raise ValueError("Device \"%s\" does not exist." % iface)
    except Exception:
        raise ValueError("Unknown error for \"%s\"." % iface)

    # Disable the dhcp client and flush interface
    dhclient(iface, False)

    try:
        sh.ip("-4", "addr", "flush", "label", iface)
    except Exception:
        raise ValueError("Unknown error for \"%s\"." % iface)

    if dhcpc:
        dhclient(iface, True, script)
    else:
        if ip:
            net = ipcalc.Network("%s/%s" % (ip, netmask))
            sh.ip("addr", "add", "%s/%s" % (ip, net.netmask()), "broadcast",
                  net.broadcast(), "dev", iface)


if __name__ == "__main__":
    print interfaces()

    # ifconfig("eth0", True)
    # dhclient("eth0", False)
    # time.sleep(10)
    # ifconfig("eth1", False, "192.168.31.36")
    eth0 = ifaddresses("eth0")
    print eth0
    print "link: %d" % eth0["link"]
    for ip in eth0["inet"]:
        print "ip: %s" % ip["ip"]
        print "netmask: %s" % ip["netmask"]
        if "subnet" in ip:
            print "subnet: %s" % ip["subnet"]

    '''
    ifupdown("eth1", True)
    # ifconfig("eth1", True)
    ifconfig("eth1", False, "192.168.31.39")

    eth1 = ifaddresses("eth1")
    print "link: %d" % eth1["link"]
    for ip in eth1["inet"]:
        print "ip: %s" % ip["ip"]
        print "netmask: %s" % ip["netmask"]
        if "subnet" in ip:
            print "subnet: %s" % ip["subnet"]
    '''
