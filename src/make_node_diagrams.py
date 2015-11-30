#!/usr/bin/env python

# make_node_diagrams.py -- Convert each node in X3D Type Hierarchy to Graphviz'
#                          dot format and create output image with the dot tool
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
import cPickle as pickle
import os.path
import subprocess
from ndb2dot import DotExporter

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

def usage(exitCode = 0):
    print 'Usage:',sys.argv[0],'[options] <node-db-file>'
    print '-h | --help                     Print this message and exit.'
    print '-n | --node-types list          Output hierarchy of specified node types (list is separated by commas)'
    print '-f | --format name              Output image format supported by dot tool (bmp, gif, png, jpeg, pdf, ...)'
    print '-d | --output-directory name    Directory where to create dot files'
    sys.exit(exitCode)

def runCommand(command, env=None):
    """returns triple (returncode, stdout, stderr)"""
    myenv = {}
    for k, v in env.items():
        myenv[str(k)] = str(v)
    env = myenv
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         env=env,
                         universal_newlines=False,
                         shell=True)
    out = p.stdout.read()
    p.stdout.close()
    err = p.stderr.read()
    p.stderr.close()
    status = p.wait()

    return (status, out, err)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hf:n:d:',
                                   ['help', 'format=', 'node-types=', 'output-directory='])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    format = 'png'
    outputDir = '.'
    
    nodes = []

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-f', '--format'):
            format = a
        elif o in ('-n', '--node-types'):
            nodes.extend(a.split(','))
        elif o in ('-d', '--output-directory'):
            outputDir = a

    if len(args) != 1:
        error('you must specify node database file')

    f = args[0]
    print >>sys.stderr, 'NodeDB file:', f

    fd = open(f, 'r')
    nodeDB = pickle.load(fd)
    fd.close()

    nodeDB.updateHierarchy()

    if len(nodes) == 0:
        nodes = nodeDB.getNodeList()
    else:
        nodes = [nodeDB.getNode(node) for node in nodes]
    
    for node in nodes:
        if not node:
            continue
        dotFileName = os.path.join(outputDir, node.getType()+'.dot')
        outFileName = os.path.join(outputDir, node.getType()+'.'+format)
        print 'Generating %s' % dotFileName
        fd = open(dotFileName, 'w')
        de = DotExporter(nodeDB, [node.getType()])
        de.export(fd)
        fd.close()

        print 'Creating %s' % outFileName
        status, out, err = runCommand(
            'dot "-T%s" "%s" -o "%s"' % (format, dotFileName, outFileName),
            os.environ)

        if status != 0:
            error('Could not run dot tool : stdout = %s\n stderr = %s\n' % (out, err))

if __name__ == '__main__':
    main()
