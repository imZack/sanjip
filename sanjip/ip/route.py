#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sh


def add(dest, dev="", src="", nexthop=None):
    """
    Add a routing rule

    Args:
        dest: destination for the routing rule, "default" for default route
            ex. "192.168.4.0/24" or "default"
        dev: routing device, could be empty
            ex. "wwan0", "eth0"
        src: source for the routing rule, fill "gateway" if dest is "default"
            ex. "192.168.4.127", "192.168.4.254"
        nexthop: nexthop info. for load balance
            [
                {
                    "via": "10.94.87.78",
                    "dev": "wwan0",
                    "weight": 1
                },
                {
                    "via": "10.144.7.254",
                    "dev": "eth0",
                    "weight": 1
                }
            ]
    """
    if "default" == dest:
        if nexthop:
            param = ["route", "add", dest]
            for nh in nexthop:
                param.append("nexthop")
                for k, v in nh.iteritems():
                    param.extend([k, v])
            sh.ip(*param)
        elif dev:
            sh.ip("route", "add", dest, "dev", dev, "via", src)
        else:
            sh.ip("route", "add", dest, "via", src)
    elif "" == src:
        sh.ip("route", "add", dest, "dev", dev)
    else:
        sh.ip(
            "route", "add", dest, "dev", dev, "proto", "kernel", "scope",
            "link", "src", src)


def delete(network="default"):
    """
    Delete a routing rule
    """
    try:
        sh.ip("route", "del", network)
    except sh.ErrorReturnCode_2:
        pass


def show():
    """
    List routing rules

    Returns:
        A list of dict of each routing rule.

        [
            ...,
            {
                "dest": "192.168.4.0/24",
                "dev": "eth1",
                "src": "192.168.4.254"
            },
            {
                "default": "10.94.87.78",
                "dev": "wwan0",
                "weight": 1,
                "priority": 1
            },
            {
                "default": "10.144.7.254",
                "dev": "eth0",
                "weight": 1,
                "priority": 2
            }
        ]
    """
    rules = []

    """
    ip route show

    default
        nexthop via 10.94.87.78  dev wwan0 weight 1
        nexthop via 10.144.7.254  dev eth0 weight 1
    10.94.87.76/30 dev wwan0  proto kernel  scope link  src 10.94.87.77
    10.144.4.0/22 dev eth0  proto kernel  scope link  src 10.144.4.80
    192.168.4.0/24 dev eth1  proto kernel  scope link  src 192.168.4.127
    """
    routes = sh.ip("route", "show")

    nexthop_priority = 1
    for route in routes:
        rule = {}
        spec = route.split()
        if "default" in route:
            if "via" in spec:
                rule["default"] = spec[spec.index("via")+1]
            if "dev" in spec:
                rule["dev"] = spec[spec.index("dev")+1]
        elif "nexthop" in route:
            rule["default"] = spec[spec.index("via")+1]
            rule["dev"] = spec[spec.index("dev")+1]
            rule["weight"] = int(spec[spec.index("weight")+1])
            rule["priority"] = nexthop_priority
            nexthop_priority += 1
        else:
            rule["dest"] = spec[0]
            if "dev" in spec:
                rule["dev"] = spec[spec.index("dev")+1]
            if "src" in spec:
                src_idx = spec.index("src")
            elif "via" in spec:
                src_idx = spec.index("via")
            else:
                src_idx = -1
            if -1 != src_idx:
                rule["src"] = spec[src_idx+1]

        # empty dict
        if len(rule) == 0:
            continue

        rules.append(rule)

    return rules
