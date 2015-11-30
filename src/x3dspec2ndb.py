#!/usr/bin/env python

# x3dspec2ndb.py -- Extract Nodes Information from X3D Specification
#
# Authors: Dmitri Rubinstein <rubinstein@cs.uni-saarland.de>,
#          Boris Broenner <borisbroenner@googlemail.com>
#
# Partially based on extract-nodes tool from libx3d-0.1 by Alexis Wilke.
# Copyright (C) 2005  Made to Order Software, Corp.
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
import os
import os.path
import getopt
import glob
import re
from nodedb import *
import cPickle as pickle

DEBUG_MODE = False

def debug(msg):
    global DEBUG_MODE
    if DEBUG_MODE:
        print >>sys.stderr, msg

def error(msg, exitCode = 1, exit = True):
    sys.stderr.write('Error: ')
    sys.stderr.write(msg)
    sys.stderr.write('\n')
    if exit:
        sys.exit(exitCode)

class ParsingException(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'ParsingException: '+str(self.message)

class FieldParsingException(ParsingException):

    def __init__(self, message, nodeClass, specFile, fieldSpec):
        ParsingException.__init__(self, message)
        self.nodeClass = nodeClass
        self.specFile = specFile
        self.fieldSpec = fieldSpec

    def __str__(self):
        msg = 'FieldParsingException: %s.' % self.message
        if self.nodeClass:
            msg += ' node: %s,' % self.nodeClass
        msg += (' specFile: "%s", fieldSpec: "%s"' % \
                (self.specFile.strip(), self.fieldSpec.strip()))
        return msg

class NodeParsingException(ParsingException):

    def __init__(self, message, nodeClass, specFile, nodeSpec):
        ParsingException.__init__(self, message)
        self.nodeClass = nodeClass
        self.specFile = specFile
        self.nodeSpec = nodeSpec

    def __str__(self):
        msg = 'NodeParsingException: '+str(self.message)+'.'
        if self.nodeClass:
            msg += ' node: %s, ' % self.nodeClass
        return msg+(' specFile: "%s", nodeSpec: "%s"' % (self.specFile.strip(),
                                                         self.nodeSpec.strip()))


FONT_PATTERN = re.compile(r"""<[pP][rR][eE]\s+class\s*=\s*(?:"node"|'node'|node)\s*>""")

COMPONENT_NAME_PATTERN = re.compile(r'''The name of this component is (?:&quot;|")(.*)(?:&quot;|")''')

#NODE_TAG_START = re.compile(r"""<[pP][rR][eE]\s+class\s*=\s*(?:"node"|'node'|node)\s*>""")

NODE_TAG_START = re.compile(r"""<[pP][rR][eE](?:\s+class\s*=\s*(?:"(\w+)"|'(\w+)'|(\w+)))?\s*>""")
NODE_TAG_END = re.compile(r'</[pP][rR][eE]>')

NODE_PATTERN = re.compile(r"""<[pP][rR][eE]\s+class\s*=\s*(?:"node"|'node'|node)\s*>([^<]*)</[pP][rR][eE]>""")

SPEC_PATTERN = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::\s*([^{]+))?\{(.*)\}',
                          re.DOTALL)
#SPEC_PATTERN = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::\s*([^{]+))?\{([^}]*)\}',
#                          re.DOTALL)

SPEC_PATTERN_START = re.compile(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::\s*([^{]+))?\{')

ATTR_PATTERN = re.compile(r'attribute\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(.*)', re.DOTALL)

FIELD_PATTERN = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*(?:in|out|in\s*,\s*out|)\s*\])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(.*)', re.DOTALL)

# Annotation: @name or @name(key=value,key=value,...)
# start: group1: name in @name
ANNOTATION_PATTERN_START = re.compile(r'\s*@([a-zA-Z_][a-zA-Z0-9_]*)')
# value: group1: values in (string)
ANNOTATION_VALUES_PATTERN = re.compile(r'\s*\((.*?)\)')
# keyvalue pattern: group1: key, group2: value
ANNOTATION_VALUE_PATTERN = re.compile(r'\s*([a-zA-Z0-9_]*)')
ANNOTATION_NEXTVALUE_PATTERN = re.compile(r'\s*,\s*([a-zA-Z0-9_]*)')

#INT [+-]?(0[xX][0-9a-fA-F]+|\d+)
#FLOAT [+-]?((?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?)
#NUMBER ([+-]?(?:0[xX][0-9a-fA-F]+|(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?))

# Note: we match only allowed number chars, not the correct numbers
NUMBER = r'[\+\-xX0-9a-fA-F.]+'

MF_PATTERN = re.compile('(\[([^]]*)\])') # will not work for [ "..]..", ".."]

SFBOOL_PATTERN = re.compile('(TRUE|FALSE)')
NUM1_PATTERN = re.compile('(%s)' % NUMBER)
NUM2_PATTERN = re.compile('(%s\s+%s)' % (NUMBER, NUMBER))
NUM3_PATTERN = re.compile('(%s\s+%s\s+%s)' % (NUMBER, NUMBER, NUMBER))
NUM4_PATTERN = re.compile('(%s\s+%s\s+%s\s+%s)' % \
                          (NUMBER, NUMBER, NUMBER, NUMBER))
NUM16_PATTERN = re.compile('(%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s\s+%s)' % \
                           (NUMBER, NUMBER, NUMBER, NUMBER,
                            NUMBER, NUMBER, NUMBER, NUMBER,
                            NUMBER, NUMBER, NUMBER, NUMBER,
                            NUMBER, NUMBER, NUMBER, NUMBER))

SFNODE_PATTERN = re.compile('(NULL)')
SFSTRING_PATTERN = re.compile(r'''("(?:[^"\\]|\\[\\"]?)*")''')

# attribute representation

class Attribute:

    def __init__(self, name, value):
        self.name = name
        self.value = value

# parse functions return None or tuple (value, rest)

def fixNum(valueInfoComment):
    valueInfoComment = valueInfoComment.replace('pi/12', '0.26179938779914941')
    valueInfoComment = valueInfoComment.replace('pi/2', '1.5707963267948966')
    valueInfoComment = valueInfoComment.replace('pi/4', '0.78539816339744828')
    valueInfoComment = valueInfoComment.replace('pi', '3.1415926535897931')
    return valueInfoComment

def parse_SFBool(valueInfoComment):
    m = SFBOOL_PATTERN.match(valueInfoComment)
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFBool(valueInfoComment):
    m = SFBOOL_PATTERN.match(valueInfoComment)
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFNum1(valueInfoComment):
    m = NUM1_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFNum1(valueInfoComment):
    m = NUM1_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFNum2(valueInfoComment):
    m = NUM2_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFNum2(valueInfoComment):
    m = NUM2_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFNum3(valueInfoComment):
    m = NUM3_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFNum3(valueInfoComment):
    m = NUM3_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFNum4(valueInfoComment):
    m = NUM4_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFNum4(valueInfoComment):
    m = NUM4_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFNum16(valueInfoComment):
    m = NUM16_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFNum16(valueInfoComment):
    m = NUM16_PATTERN.match(fixNum(valueInfoComment))
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFString(valueInfoComment):
    m = SFSTRING_PATTERN.match(valueInfoComment)
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFString(valueInfoComment):
    m = SFSTRING_PATTERN.match(valueInfoComment)
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_SFNode(valueInfoComment):
    m = SFNODE_PATTERN.match(valueInfoComment)
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

def parse_MFNode(valueInfoComment):
    m = SFNODE_PATTERN.match(valueInfoComment)
    debug("m %s" % (m,))
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    m = MF_PATTERN.match(valueInfoComment)
    if m:
        value = m.group(1).strip()
        rest = valueInfoComment[m.end():].strip()
        debug("MATCH %s %s" % (value, rest))
        return (value, rest)
    return None

FIELD_INFOS = [('SFBool', parse_SFBool, False),
               ('MFBool', parse_MFBool, True),
               ('SFColor', parse_SFNum3, False),
               ('MFColor', parse_MFNum3, True),
               ('SFColorRGBA', parse_SFNum4, False),
               ('MFColorRGBA', parse_MFNum4, True),
               ('SFDouble', parse_SFNum1, False),
               ('MFDouble', parse_MFNum1, True),
               ('SFFloat', parse_SFNum1, False),
               ('MFFloat', parse_MFNum1, True),
               ('SFImage', parse_SFNum3, False),
               ('MFImage', parse_MFNum3, True),
               ('SFInt32', parse_SFNum1, False),
               ('MFInt32', parse_MFNum1, True),
               ('SFNode', parse_SFNode, False),
               ('MFNode', parse_MFNode, True),
               ('SFRotation', parse_SFNum4, False),
               ('MFRotation', parse_MFNum4,  True),
               ('SFString', parse_SFString, False),
               ('MFString', parse_MFString, True),
               ('SFTime', parse_SFNum1, False),
               ('MFTime', parse_MFNum1, True),
               ('SFVec2d', parse_SFNum2, False),
               ('MFVec2d', parse_MFNum2,  True),
               ('SFVec2f', parse_SFNum2, False),
               ('MFVec2f', parse_MFNum2, True),
               ('SFVec3d', parse_SFNum3, False),
               ('MFVec3d', parse_MFNum3, True),
               ('SFVec3f', parse_SFNum3, False),
               ('MFVec3f', parse_MFNum3, True),
               ('SFVec4d', parse_SFNum4, False),
               ('MFVec4d', parse_MFNum4, True),
               ('SFVec4f', parse_SFNum4, False),
               ('MFVec4f', parse_MFNum4, True),
               ('SFMatrix4d', parse_SFNum16, False),
               ('MFMatrix4d', parse_MFNum16, True),
               ('SFMatrix4f', parse_SFNum16, False),
               ('MFMatrix4f', parse_MFNum16, True)
]

FIELD_NAME_PATTERN = re.compile('|'.join([n[0] for n in FIELD_INFOS]+['attribute\s+']))


##########################################################################
# X3DSpecParser
##########################################################################

class X3DSpecParser:

    def __init__(self):
        self.nodeSpec = None
        self.nodeDB = NodeDB()
        self.specFile = None
        self.componentName = None
        self.currentNode = None
        self.collectedErrors = []

    def parsingError(self, e):
        self.collectedErrors.append(e)

    def parseAnnotations(self, comment):
        debug('')
        debug('parseAnnotations(\"' + comment + '\")')

        # check if comment has an annotation syntax :
        # @annot_name (value,value,value,...) @annot2_name...
        annotations = Annotations()

        m = ANNOTATION_PATTERN_START.search(comment)
        searchStr = comment

        while m:
            annotationName = m.group(1)
            debug('annotationName %s' % annotationName)
            debug('search string: %s' % searchStr)

            valList = []

            nameEnd = m.end()
            searchStr = searchStr[nameEnd:]

            # scan through values
            # the (value,...) list is optional!
            m = ANNOTATION_VALUES_PATTERN.match(searchStr)
            if m:
                searchStr = searchStr[m.start(1):] # start inside parentheses
                m = ANNOTATION_VALUE_PATTERN.match(searchStr)
                while m:
                    valList.append(m.group(1))

                    searchStr = searchStr[m.end():]
                    debug("annotation (%s)" % m.group(1))
                    debug("new search str: %s" % (searchStr))
                    m = ANNOTATION_NEXTVALUE_PATTERN.match(searchStr)

                searchStr = searchStr[1:]

            debug("valList = %s" % valList)

            annotations.setAnnotation(Annotation(annotationName, valList))

            m = ANNOTATION_PATTERN_START.search(searchStr)

        return annotations

    def parseField(self, fieldSpec):
        debug("parseField(%s)" % repr(fieldSpec)) #???DEBUG

        commentStart = fieldSpec.find('#')
        if commentStart != -1:
            finalComment = fieldSpec[commentStart+1:].strip()
            fieldSpec = fieldSpec[:commentStart]
            debug("NEW FSPEC %s" % repr(fieldSpec))
        else:
            finalComment = ''
        debug("finalComment %s" % (repr(finalComment),))

        m = ATTR_PATTERN.match(fieldSpec.strip())
        if m:
            valueInfoComment = m.group(2)

            value, info = None, None

            result = parse_SFBool(valueInfoComment)
            if result is not None:
                value, info = result
                if value == 'TRUE':
                    value = True
                else:
                    value = False
            else:
                result = parse_SFNum1(valueInfoComment)
                if result is not None:
                    value, info = result
                    try:
                        value = int(value)
                    except ValueError:
                        value = float(value)
                else:
                    result = parse_SFString(valueInfoComment)
                    if result is not None:
                        value, info = result
                        # remove quotes
                        value = value.strip()
                        assert value[0] == '"' and value[-1] == '"'
                        value = value[1:-1]
                        # unescape escaped characters
                        value = value.replace('\\\\', '\\').replace('\\"', '"')
                    else:
                        raise FieldParsingException(
                            'Invalid attribute specification',
                            self.currentNode.getType(),
                            self.currentNode.getSpecFile(),
                            fieldSpec)

            return Attribute(m.group(1), value)

        m = FIELD_PATTERN.match(fieldSpec.strip())
        if m:
            type = m.group(1)
            accessType = convertAccessTypeNameToId(m.group(2))
            name = m.group(3)
            valueInfoComment = m.group(4)

            valuePatFunc = None
            for f in FIELD_INFOS:
                if f[0] == type:
                    debug("SEL %s" % str(f))
                    valuePatFunc = f[1]
                    break

            value = None
            vvt = None
            info = None

            debug("type=%s, accessType=%s, name=%s, valueInfoComment=%s" % \
                  (repr(type),repr(accessType),repr(name),
                   repr(valueInfoComment)))

            if accessType in (INITIALIZE_ONLY, INPUT_OUTPUT):
                if valuePatFunc:
                    result = valuePatFunc(valueInfoComment)
                    if result is not None:
                        value, info = result

                        # for MFColor, MFColorRGBA, and MFVec3f
                        # it is possible that
                        # field specifications incorrectly specify [NULL] as
                        # a default value instead of [].
                        # (problem located in Color, ColorRGBA, and Coordinate
                        #  nodes: ISO-IEC-FDIS-19775-1.2)

                        if type in ('MFColor', 'MFColorRGBA', 'MFVec3f') \
                               and value == '[NULL]':
                            value = '[]'

                    else:
                        debug("NO MATCH")

                        # for SFNode it is possible that
                        # fields specification incorrectly provides [] as
                        # a value instead of NULL.
                        # (problem located in IndexedFaceSet node:
                        # ISO-IEC-FDIS-19775-1.2)

                        if type == 'SFNode':
                            # check for [] and fix it when found
                            m = MF_PATTERN.match(valueInfoComment)
                            if m:
                                if len(m.group(2).strip()) == 0:
                                    value ='NULL'
                                    info = valueInfoComment[m.end():].strip()
                                    # this is actually a spec error
                                    debug('MATCH NULL -> Spec error')
                                    nodeClass = self.currentNode.getType()
                                    specFile = self.currentNode.getSpecFile()

                                    self.parsingError(
                                        FieldParsingException(
                                        'SFNode field declaration provides invalid default value []',
                                        nodeClass,
                                        specFile,
                                        fieldSpec))
                        else:
                            nodeClass = self.currentNode.getType()
                            specFile = self.currentNode.getSpecFile()
                            self.parsingError(
                                FieldParsingException(
                                "no or incorrect default value",
                                nodeClass,
                                specFile,
                                fieldSpec))
                            debug("SCE %s" % (self.collectedErrors,))#???DEBUG
                            value, info = None, None
            else:

                # for MFNode it is possible that for INPUT_ONLY / OUTPUT_ONLY
                # fields specification incorrectly provides a value.
                # (problem located in Layout component: ISO-IEC-FDIS-19775-1.2)

                if type == 'MFNode':
                    # check for [] [something] and fix it when found
                    m = MF_PATTERN.match(valueInfoComment)
                    if m:
                        if len(m.group(2).strip()) == 0:
                            newValueInfoComment = valueInfoComment[m.end():].strip()
                            if MF_PATTERN.match(newValueInfoComment):
                                valueInfoComment = newValueInfoComment

                                # this is actually a spec error
                                nodeClass = self.currentNode.getType()
                                specFile = self.currentNode.getSpecFile()

                                e = FieldParsingException('MFNode inputOnly/outputOnly field declaration provide a default value', nodeClass, specFile, fieldSpec)
                                self.collectedErrors.append(e)

                info = valueInfoComment

            if info and type in ('SFNode', 'MFNode'):
                m = MF_PATTERN.match(info)
                if m:
                    vvt = re.split('\||,', m.group(2))
                    vvt = [s.strip() for s in vvt]
                    info = info[m.end():].strip()

            if finalComment:
                if info:
                    debug("CONCAT %s %s" % (repr(info), repr(finalComment)))
                    info += finalComment
                else:
                    info = finalComment

            if info:
                info = info.replace('\n', ' ').replace('\t', ' ')

            # When the info comment is empty, use None as info value
            if not info:
                info = None
                annotations = None
            else:
                annotations = self.parseAnnotations(info)
                info = None

            debug("annotations %s" % (repr(annotations),))
            debug("info %s" % (repr(info),))
            debug("-----")
            debug("")

            debug("f = %s" % repr(Field(type, accessType, name, value, vvt, annotations, info)))
            return Field(type, accessType, name, value, vvt, annotations, info)
        else:
            raise FieldParsingException('Invalid field specification',
                                        self.currentNode.getType(),
                                        self.currentNode.getSpecFile(),
                                        fieldSpec)

    def parseFields(self, fieldsSpec):
        i = 0
        startPos = -1
        endPos = -1
        fields = []
        while i < len(fieldsSpec):
            startPos = endPos
            # find field start
            m = FIELD_NAME_PATTERN.search(fieldsSpec, i)
            if m:
                endPos = m.start()
                i = m.end()
                if startPos != -1:
                    try:
                        fields.append(self.parseField(fieldsSpec[startPos:endPos]))
                    except FieldParsingException, e:
                        self.collectedErrors.append(e)
            else:
                try:
                    fields.append(self.parseField(fieldsSpec[startPos:]))
                except FieldParsingException, e:
                    self.collectedErrors.append(e)
                break
        return fields

    def getNodeDB(self):
        return self.nodeDB

    def replace(self, old, new):
        if self.nodeSpec:
            tmp = self.nodeSpec.replace(old, new)
            if tmp != self.nodeSpec:
                self.nodeSpec = tmp
                return True
        return False

    def sub(self, pattern, sub):
        if self.nodeSpec:
            self.nodeSpec = re.sub(pattern, sub, self.nodeSpec)

    def getNodeSpec(self):
        return self.nodeSpec

    def ignoreNodeSpec(self):
        self.nodeSpec = None

    def parse(self, data, specFile=None):
        i = 0
        self.specFile = specFile

        # try to recognize name of the component
        m = COMPONENT_NAME_PATTERN.search(data)
        if m:
            componentName = m.group(1)
        else:
            error('Could not recognize component defined in file : %s' % specFile,
                  exit=False)
            componentName = os.path.basename(specFile)
            bn = componentName.lower()
            if bn.endswith('.html'):
                componentName = componentName[:-5]
            elif bn.endswith('.htm'):
                componentName = componentName[:-4]
                
        self.componentName = componentName

        # find and process all node declarations
        while i < len(data):
            # find tag start
            m = NODE_TAG_START.search(data, i)
            if m:
                preClassName = m.group(1) or m.group(2) or m.group(3)
                ignoreTag = (preClassName not in (None,'','node'))
                
                startPos = m.end()
                i = startPos
                # find tag end
                m = NODE_TAG_END.search(data, startPos)
                if m:
                    endPos = m.start()
                    i = m.end()
                    nodeSpec = data[startPos:endPos]
                else:
                    nodeSpec = data[startPos:]

                if ignoreTag:
                    continue
                    
                self.nodeSpec = nodeSpec
                self.fixRawNodeSpec()
                try:
                    self.processNodeSpec()
                except ParsingException, e:
                    self.collectedErrors.append(e)
                if self.nodeSpec is not None and '#' in self.nodeSpec: #???DEBUG
                    debug("# in node spec: <%s>" % self.nodeSpec)
                #print self.nodeSpec
            else:
                break

    def scanNodeSpec(self, data, startPos):
        """Returns tuple (nodeSpec, endPos)"""

        # skip comment line(s)
        insideComment = False
        for i in xrange(startPos, len(data)):
            if data[i] == '\n':
                insideComment = False
            elif data[i] == '#':
                insideComment = True
            elif not data[i].isspace() and not insideComment:
                startPos = i
                break

        m = SPEC_PATTERN_START.search(data, startPos)
        if m:
            nodeClass = m.group(1)
            superTypes = m.group(2)

            i = m.end()
            while (i < len(data)):
                if data[i] == '}':
                    i+=1
                    break
                if data[i] == '#':
                    endOfLine = data.find('\n', i)
                    if endOfLine != -1:
                        i = endOfLine+1
                        continue
                    else:
                        i = len(data)
                        break
                i+=1
            endPos = i

            nodeSpec = data[m.start():endPos]

            return (nodeSpec, endPos)
        else:
            return ('', len(data))

    def parseFromText(self, data, specFile=None):
        i = 0
        self.specFile = specFile

        # try to recognize name of the component
        componentName = os.path.basename(os.path.splitext(specFile)[0])

        self.componentName = componentName

        # find and process all node declarations
        while i < len(data):
            self.nodeSpec, i = self.scanNodeSpec(data, i)

            if len(self.nodeSpec):
                self.fixRawNodeSpec()
                try:
                    self.processNodeSpec()
                except ParsingException, e:
                    self.collectedErrors.append(e)
                if self.nodeSpec is not None and '#' in self.nodeSpec: #???DEBUG
                    debug("# in node spec: <%s>" % self.nodeSpec)


    def finishParsing(self):
        self.nodeDB.updateHierarchy()

    def processNodeSpec(self):
        if not self.nodeSpec:
            return
        
        # parse name
        m = SPEC_PATTERN.match(self.nodeSpec)
        nodeClass = None
        if m:
            nodeClass = m.group(1)
            superTypes = m.group(2)
            nodeBody = m.group(3).strip()

            debug("Node %s" % nodeClass)
            
            # remove spaces from parent classes list and split it
            if superTypes:
                superTypes = superTypes.replace(' ', '').split(',')
            else:
                superTypes = []
            
            node = Node(nodeClass)
            node.setSpecFile(self.specFile)
            node.setComponentName(self.componentName)
            node.setSuperTypes(superTypes)
            if nodeClass.startswith('X3D'):
                node.setAbstract(True)

            # setup current node ref before fields are parsed
            self.currentNode = node

            fields = self.parseFields(nodeBody)

            for f in fields:
                if isinstance(f, Attribute):
                    node.setAttribute(f.name, f.value)
                else:
                    node.addField(f)

            try:
                self.nodeDB.addNode(node)
            except NodeDBException, e:
                raise NodeParsingException(
                    'Could not add node to the databse : %s' % e,
                    nodeClass, self.specFile, self.nodeSpec)
        else:
            raise NodeParsingException('Invalid node specification',
                                       nodeClass, self.specFile, self.nodeSpec)

    def fixRawNodeSpec(self):
        # text fixing rules (HTML tags, unsupported characters, etc.)

        nodeSpec = self.getNodeSpec()
        tokens = nodeSpec.split()
        if tokens:
            nodeName = tokens[0]
        else:
            nodeName = None
        
        self.sub('<[^>]*>', '')  # internal HTML tags
        self.replace('&#8734;','inf')
        self.replace('&#960;','pi')
        self.replace('&infin;', 'inf')
        self.replace('&minus;','-')
        self.replace('&plus;','+')
        self.replace('&quot;','"')
        self.replace('&pi;','pi')
        self.replace('&lt;','<')
        self.replace('\xe2\x88\x9e','inf')
        self.replace('\xe2\x88\x92','-')
        self.replace('\xcf\x80','pi')

        self.replace('\r', '') # CRs

        # special node and field fixing rules
        changed = self.replace('SFBoolean', 'SFBool   ')
        if changed:
            self.parsingError(NodeParsingException(
                'Replaced SFBoolean with SFBool',
                nodeName, self.specFile,
                self.getNodeSpec()))

        changed = self.replace('X3DURLObject', 'X3DUrlObject')
        if changed:
            self.parsingError(NodeParsingException(
                'Replaced X3DURLObject with X3DUrlObject',
                nodeName, self.specFile,
                self.getNodeSpec()))

        self.sub('\s*#\sAnd.*', '')
        self.sub('\s*fieldType\s\[.*', '')
        self.sub('\s*MF<type>.*','')
        self.sub('\s*\[S\|M\]F<type>.*','')
        
        if nodeName == 'X3DViewpointNode':
            self.sub('\s*SFVec3f/d.*','')
        elif nodeName.startswith('P['):
            self.ignoreNodeSpec()
            return
        elif nodeName == 'TextureProperties':
            if '{' not in nodeSpec:
                self.sub('X3DNode', 'X3DNode {')
        elif nodeName == 'X3DPrototypeInstance':
            changed = self.replace('metdata', 'metadata')
            if changed:
                self.parsingError(NodeParsingException(
                    'Replaced metdata with metadata',
                    nodeName, self.specFile,
                    self.getNodeSpec()))
        elif nodeName == 'Text':
            changed = self.replace('X3FontSyleNode', 'X3DFontStyleNode')
            if changed:
                self.parsingError(NodeParsingException(
                    'Replaced X3FontSyleNode with X3DFontStyleNode',
                    nodeName, self.specFile,
                    self.getNodeSpec()))

            changed = self.replace('X3FontStyleNode', 'X3DFontStyleNode')
            if changed:
                self.parsingError(NodeParsingException(
                    'Replaced X3FontStyleNode with X3DFontStyleNode',
                    nodeName, self.specFile,
                    self.getNodeSpec()))

        changed = self.replace('[LINEAR]', '["LINEAR"]')
        if changed:
            self.parsingError(NodeParsingException(
                'Replaced [LINEAR] with ["LINEAR"]',
                nodeName, self.specFile,
                self.getNodeSpec()))

        #self.replace('["standAlone" "networkReader" "networkWriter"]',
        #                   '# ["standAlone" "networkReader" "networkWriter"]')
        #self.replace('["LINEAR"|"EXPONENTIAL"]',
        #                    '# ["LINEAR"|"EXPONENTIAL"]')
        #self.replace('["EXAMINE" "ANY"]', '# ["EXAMINE" "ANY"]')
        #self.replace('["EXAMINE","ANY"]', '# ["EXAMINE","ANY"]')
        #self.replace('[0,inf) [0,inf) [0,inf) or -1 -1 -1',
        #                    '# POS_INF POS_INF POS_INF or -1 -1 -1')

        #self.replace('[0,inf) or -1 -1 -1', '# POS_INF or -1 -1 -1')
        #self.replace('[-1,1] or (-inf,inf)', '# [-1,1] or INF_RANGE')
        #self.replace('(-inf,inf)|[-1,1]', '# (-inf,inf)|[-1,1]')
        #self.sub('\[see\s+25\.2\.3\]', '# see 25.2.3')
        #self.replace('(0,inf)', '# (0,inf)')
        #self.replace('[1,inf)', '# [1,inf)')
        #self.replace('(-inf,inf)', '# (-inf,inf)')
        #self.replace('[-inf,inf)', '# [-inf,inf)')
        #self.replace('[0,1]', '# [0,1]')
        #self.replace('[0,78]', '# [0,78]')
        #self.replace('[0,255]', '# [0,255]')
        #self.replace('[0,65535]', '# [0,65535]')
        #self.replace('[0,65355]', '# [0,65355]')
        #self.replace('[0,inf)', '# [0,inf)')
        #self.replace('[-1,inf)', '# [-1,inf)')
        #self.replace('[0,pi/2]', '# [0,pi/2]')
        #self.replace('[0,pi]', '# [0,pi]')
        #self.replace('(0,pi)', '# (0,pi)')
        #self.replace('[urn]', '# URN')

        # fix renamed sequences
        self.replace('INF_RANGE', '(-inf,inf)')
        self.replace('POS_INF', '[0,inf)')

        self.replace('pi/4', '0.78539816339744828')
        self.replace('pi/2', '1.5707963267948966')
        self.replace('pi/12', '0.26179938779914941')


def usage(exitCode = 0):
    print 'Usage:',sys.argv[0],'[options] <path-to-x3d-spec>'
    print '-h | --help                     Print this message and exit.'
    print '-p | --pickle                   Output node database in pickle format'
    print '-e | --errors                   Print all parsing errors to stderr'
    print '-t | --text                     Input is not a X3D spec in HTML format,'
    print '                                but a text file with a X3D-style node'
    print '                                specifications'
    sys.exit(exitCode)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hpetd',
                                   ['help', 'pickle', 'errors', 'text',
                                    'debug'])
    except getopt.GetoptError, e:
        error(str(e), exit = False)
        usage(1)

    pickleNodeDB = False
    printErrors = False
    textSpec = False
    global DEBUG_MODE
    
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o in ('-p', '--pickle'):
            pickleNodeDB = True
        elif o in ('-e', '--errors'):
            printErrors = True
        elif o in ('-t', '--text'):
            textSpec = True
        elif o in ('-d', '--debug'):
            DEBUG_MODE = True

    if len(args) != 1:
        error('you must specify path to X3D specification')

    pathToSpec = args[0]
    print >>sys.stderr, 'Path to X3D specification:', pathToSpec

    parser = X3DSpecParser()

    if not textSpec:
        componentsPath = os.path.join(pathToSpec, 'Part01', 'components')

        if not os.path.exists(componentsPath):
            error('Path %s does not exists.' % componentsPath)

        if not os.path.isdir(componentsPath):
            error('Path %s is not a directory.' % componentsPath)

        componentsHtml = glob.glob(os.path.join(componentsPath, '*.html'))

        if len(componentsHtml) == 0:
            error('No *.html files in %s directory' % componentsPath)

        for f in componentsHtml:
            debug('processing file %s' % f)
            fd = open(f, 'r')
            parser.parse(fd.read(), specFile=f)
            #parser.reset()
            #parser.feed(fd.read())
            #parser.close()
            fd.close()
    else:
        fd = open(pathToSpec, 'r')
        parser.parseFromText(fd.read(), specFile=pathToSpec)
        fd.close()

    parser.finishParsing()

    nodeDB = parser.getNodeDB()
    
    if pickleNodeDB:
        pickle.dump(nodeDB, sys.stdout)
    else:
        specFile = None
        for node in nodeDB.getNodeList():
            if node.getSpecFile() != specFile:
                specFile = node.getSpecFile()
                print '# file : %s' % specFile
                print
            print node
            print

    if printErrors:
        for e in parser.collectedErrors:
            print >>sys.stderr, e
        if len(parser.collectedErrors):
            sys.exit(1)

if __name__ == '__main__':
    main()
