#!/usr/bin/env python

# ndbdiff.py -- X3D Type Hierarchy Comparison Tool
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
    print 'Usage:',sys.argv[0],'[options] node-db-file-1 node-db-file-2'
    print '-h | --help                     Print this message and exit.'
    print '-a | --all                      Print all differences, also unimportant like source file.'
    sys.exit(exitCode)

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'ha',
                                   ['help','all'])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    nodes = []
    printAll = False

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-a', '--all'):
            printAll = True

    if len(args) != 2:
        error('you must specify two node database files')

    f1 = args[0]
    f2 = args[1]

    print '---', f1
    print '+++', f2
    print

    ndb1 = nodedb.load(f1)
    ndb2 = nodedb.load(f2)
    result = ndb1.diff(ndb2, printAll)
    for i in result:
        print i

if __name__ == '__main__':
    main()
