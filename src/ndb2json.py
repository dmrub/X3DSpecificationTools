#!/usr/bin/env python

# ndb2json.py -- X3D Type Hierarchy to JSON Converter
#
# Author: Dmitri Rubinstein <rubinstein@cs.uni-saarland.de>
#
# Copyright (C) 2008 Saarland University
# Copyright (C) 2009, 2010, 2011, 2012 German Research Center for
# Artificial Intelligence (DFKI)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import getopt
import nodedb

def usage(exitCode = 0):
    print 'Usage:',sys.argv[0],'[options] <node-db-file>'
    print '-h | --help                     Print this message and exit.'
    sys.exit(exitCode)

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h',
                                   ['help'])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    nodes = []

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()

    if len(args) != 1:
        error('you must specify node database file')

    f = args[0]
    print >>sys.stderr, 'NodeDB file:', f

    ndb = nodedb.load(f)
    print nodedb.toJSON(ndb)

if __name__ == '__main__':
    main()
