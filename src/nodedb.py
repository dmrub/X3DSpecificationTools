# nodedb.py -- X3D Node Type Database
#
# Authors: Dmitri Rubinstein <rubinstein@cs.uni-saarland.de>,
#          Boris Broenner <borisbroenner@googlemail.com>
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

import cPickle as pickle
import json
import xml.sax.saxutils
import re

# field access types

INITIALIZE_ONLY = 0
INPUT_ONLY      = 1
OUTPUT_ONLY     = 2
INPUT_OUTPUT    = 3

class NodeDBException(Exception):
    pass

class ValueParsingException(NodeDBException):
    pass

# field value parsers

def normalizeVRMLValue(value):
    """removes starting '[' and ending ']', and
    tries to replace all commas with spaces
    """
    value = value.strip()
    if value.startswith('['):
        value = value[1:]
    if value.endswith(']'):
        value = value[:-1]
    if '"' not in value:
        value = value.replace(',', ' ')
    value = value.strip()
    return value

class NumberParser:
    """Converts strings with space separated numbers to number tuples"""

    def __init__(self, converter, numbersPerTuple, numTuples=1):
        self.converter = converter
        self.numbersPerTuple = numbersPerTuple
        self.numTuples = numTuples

    def __call__(self, value):
        parsedValue = map(self.converter, normalizeVRMLValue(value).split())
        lpv = len(parsedValue)
        div, mod = divmod(lpv, self.numbersPerTuple)

        if mod != 0:
            raise ValueParsingException('incorrect count of numbers in %s' \
                                        % repr(value))

        if self.numTuples != -1 and div != self.numTuples:
            raise ValueParsingException( \
                'incorrect number of tuples (%i) in %s, should be %i' \
                % (div, repr(value), self.numTuples))

        # special case, single number and array of numbers
        if self.numbersPerTuple == 1:
            if self.numTuples == 1 and lpv == 1:
                return parsedValue[0]
            else:
                return parsedValue

        r = [parsedValue[i:i+self.numbersPerTuple] \
             for i in range(0,lpv,self.numbersPerTuple)]

        # special case, single tuple
        if self.numTuples == 1:
            return r[0]

        return r

class BoolParser:

    def __init__(self, parseArray=False):
        self.parseArray = parseArray

    def __call__(self, value):
        value = normalizeVRMLValue(value).split()

        if not self.parseArray and len(value) != 1:
            raise ValueParsingException('expected single value in %s' \
                                        % repr(value))

        def toBool(v):
            vu = v.upper()
            if vu == 'TRUE':
                return True
            if vu == 'FALSE':
                return False
            raise ValueParsingException('incorrect value %s' \
                                        % repr(v))
        value = [toBool(i) for i in value]

        if not self.parseArray:
            return value[0]
        return value

SFSTRING_PATTERN = re.compile(r'''^[\s,]*"((?:[^"\\]|\\[\\"]?)*)"''')

def fixSFString(s):
    return s.replace('\\\\', '\\').replace('\\"', '"')

def sfStringParser(value):
    value = normalizeVRMLValue(value)
    m = SFSTRING_PATTERN.match(value)
    if not m:
        raise ValueParsingException('expected single string value in %s' %
                                    repr(value))
    rest = normalizeVRMLValue(value[m.end():])
    if rest:
        # there should be nothing after first string
        raise ValueParsingException('expected single string value in %s' %
                                    repr(value))
    return fixSFString(m.group(1))

def mfStringParser(value):
    value = normalizeVRMLValue(value)
    rest = value
    result = []
    while True:
        m = SFSTRING_PATTERN.match(rest)
        if m:
            rest = normalizeVRMLValue(rest[m.end():])
            result.append(fixSFString(m.group(1)))
        else:
            break

    if rest:
        # there should be nothing after first string
        raise ValueParsingException('expected multiple string values in %s' %
                                    repr(value))
    return result


class NullNode(object):
    pass

NULL_NODE = NullNode()

def sfNodeParser(value):
    value = normalizeVRMLValue(value)
    if value == 'NULL':
        return NULL_NODE
    raise ValueParsingException('Expected NULL value but found : %s' %
                                repr(value))

def mfNodeParser(value):
    value = normalizeVRMLValue(value).split()
    result = []
    for i in value:
        if i == 'NULL':
            result.append(NULL_NODE)
        else:
            raise ValueParsingException('Expected NULL value but found : %s' %
                                        repr(i))
    return result

sfBool1Parser = BoolParser(parseArray=False)
mfBool1Parser = BoolParser(parseArray=True)

sfFloat1Parser = NumberParser(float, 1)
mfFloat1Parser = NumberParser(float, 1, -1)

sfInt1Parser = NumberParser(int, 1)
mfInt1Parser = NumberParser(int, 1, -1)

sfFloat2Parser = NumberParser(float, 2)
mfFloat2Parser = NumberParser(float, 2, -1)

sfInt2Parser = NumberParser(int, 2)
mfInt2Parser = NumberParser(int, 2, -1)

sfFloat3Parser = NumberParser(float, 3)
mfFloat3Parser = NumberParser(float, 3, -1)

sfInt3Parser = NumberParser(int, 3)
mfInt3Parser = NumberParser(int, 3, -1)

sfFloat4Parser = NumberParser(float, 4)
mfFloat4Parser = NumberParser(float, 4, -1)

sfInt4Parser = NumberParser(int, 4)
mfInt4Parser = NumberParser(int, 4, -1)

sfFloat16Parser = NumberParser(float, 16)
mfFloat16Parser = NumberParser(float, 16, -1)

# Just a hack, image should be 0 0 0
sfImageParser = sfInt3Parser
mfImageParser = mfInt3Parser

FIELD_PARSERS = {'SFBool'  : sfBool1Parser,
                 'MFBool'  : mfBool1Parser,
                 'SFColor' : sfFloat3Parser,
                 'MFColor' : mfFloat3Parser,
                 'SFColorRGBA' : sfFloat4Parser,
                 'MFColorRGBA' : mfFloat4Parser,
                 'SFDouble' : sfFloat1Parser,
                 'MFDouble' : mfFloat1Parser,
                 'SFFloat' : sfFloat1Parser,
                 'MFFloat' : mfFloat1Parser,
                 'SFImage' : sfImageParser,
                 'MFImage' : mfImageParser,
                 'SFInt32' : sfInt1Parser,
                 'MFInt32' : mfInt1Parser,
                 'SFNode' : sfNodeParser,
                 'MFNode' : mfNodeParser,
                 'SFRotation' : sfFloat4Parser,
                 'MFRotation' : mfFloat4Parser,
                 'SFString' : sfStringParser,
                 'MFString' : mfStringParser,
                 'SFTime' : sfFloat1Parser,
                 'MFTime' : mfFloat1Parser,
                 'SFVec2d' : sfFloat2Parser,
                 'MFVec2d' : mfFloat2Parser,
                 'SFVec2f' : sfFloat2Parser,
                 'MFVec2f' : mfFloat2Parser,
                 'SFVec3d' : sfFloat3Parser,
                 'MFVec3d' : mfFloat3Parser,
                 'SFVec3f' : sfFloat3Parser,
                 'MFVec3f' : mfFloat3Parser,
                 'SFVec4d' : sfFloat4Parser,
                 'MFVec4d' : mfFloat4Parser,
                 'SFVec4f' : sfFloat4Parser,
                 'MFVec4f' : mfFloat4Parser,
                 'SFMatrix4d' : sfFloat16Parser,
                 'MFMatrix4d' : mfFloat16Parser,
                 'SFMatrix4f' : sfFloat16Parser,
                 'MFMatrix4f' : mfFloat16Parser,
                 }

def parseFieldValue(fieldType, fieldValue):
    global FIELD_PARSERS
    parser = FIELD_PARSERS.get(fieldType)
    if parser is None or fieldValue is None:
        return None
    return parser(fieldValue)

def convertAccessTypeNameToId(name):
    n = name.replace(' ', '')
    if n == '[]':
        return INITIALIZE_ONLY
    elif n == '[in]':
        return INPUT_ONLY
    elif n == '[out]':
        return OUTPUT_ONLY
    elif n == '[in,out]' or n == '[out,in]':
        return INPUT_OUTPUT
    else:
        return -1

def getObjectDict(obj):
    if getattr(obj, '__dict__', None) is None:
        return None
    
    serializedFields = getattr(obj, '__serialize__', None)
    if serializedFields:
        objectDict = {}
        for k, v in obj.__dict__.items():
            if k in serializedFields:
                objectDict[k] = v
    else:
        objectDict = obj.__dict__.copy()
    return objectDict

def makeObjectRepr(obj):
    objectDict = getObjectDict(obj)
    if not objectDict:
        return repr(obj)
    
    className = obj.__class__.__name__

    initValues = ', '.join(['%s=%s' % (kv[0], repr(kv[1]))
                            for kv in objectDict.items()])
    return '%s(%s)' % (className, initValues)


class Annotation(object):

    __serialize__ = ['name', 'valList']

    def __init__(self, name, valList=None):
        self.name = str(name)
        if valList is not None:
            self.valList = list(valList)
        else:
            self.valList = None

    def getName(self):
        return self.name

    def getValueList(self):
        return self.valList

    def copy(self):
        """A.copy() -> a deep copy of A"""
        return Annotation(self.name, self.valList)

    def __getstate__(self):
        """Serialization"""
        return self.__dict__

    def __setstate__(self, state):
        """Deserialization"""
        self.__dict__ = state

    def __hash__(self):
        h = hash(self.name)
        if self.valList is not None:
            h = h ^ hash(len(self.valList))
            for value in self.valList:
                h = h ^ hash(value)
        return h

    def __eq__(self, other):
        return (self.name == other.name and self.valList == other.valList)

    def __repr__(self):
        return 'Annotation(%s, %s)' % (repr(self.name), repr(self.valList))

    def toString(self):
        s = ''
        if self.valList is not None and len(self.valList) > 0:
            s = '(' + ', '.join(['%s' % val for val in self.valList]) + ')'
        return "@" + self.name + s

    def __str__(self):
        return self.toString()

class Annotations(object):

    __serialize__ = ['annotDict']

    def __init__(self, annList = []):

        self.annotDict = {}
        map(self.setAnnotation, annList)

    def getAnnotation(self, name):

        if not name in self.annotDict:
            return None

        return self.annotDict[name]

    def setAnnotation(self, ann):
        self.annotDict[ann.getName()] = ann

    def __getstate__(self):
        """Serialization"""
        return self.__dict__

    def __setstate__(self, state):
        """Deserialization"""
        self.__dict__ = state

    def copy(self):
        """A.copy() -> a deep copy of A"""
        return Annotations(self.annotDict.values())

    def __hash__(self):
        h = hash(len.self.annotDict.keys())
        for key in self.annotDict.keys():
            h = h ^ hash(self.annotDict[key])
        return h

    def __eq__(self, other):
        return (self.annotDict == other.annotDict)

    def __repr__(self):
        s = '[ '
        for key in self.annotDict.keys():
            s += repr(self.annotDict[key]) + ' '
        s += ']'

        return s

    def toString(self):
        s = ''
        for key in self.annotDict.keys():
            s += self.annotDict[key].toString() + ' '

        return s

    def __str__(self):
        return self.toString()

class Field(object):

    __serialize__ = ['type', 'accessType', 'name', 'value', 'parsedValue',
                     'validValueTypes', 'info', 'annotations']

    accessTypeNames = ['[]', '[in]', '[out]', '[in,out]']
    accessTypeConsts = ['INITIALIZE_ONLY', 'INPUT_ONLY',
                        'OUTPUT_ONLY', 'INPUT_OUTPUT']


    def __init__(self, type, accessType, name, value=None,
                 validValueTypes=None, annotations=None, info=None):
        self.type = type
        self.accessType = accessType
        self.name = name
        self.value = value
        self.parsedValue = parseFieldValue(type, value)
        if validValueTypes:
            self.validValueTypes = validValueTypes[:]
        else:
            self.validValueTypes = []
        if annotations is None:
            self.annotations = Annotations()
        elif isinstance(annotations, Annotations):
            self.annotations = annotations.copy()
        else:
            self.annotations = Annotations(annotations)
        if info is not None:
            self.info = str(info)
            if len(self.info) == 0:
                self.info = None
        else:
            self.info = None
        # self.declaredInNodes store references to the nodes where the field
        # intially declared.
        # self.declaredInNodes is filled by NodeDB.updateHierarchy
        self.declaredInNodes = None

    def __getstate__(self):
        """Serialization"""
        return self.__dict__

    def __setstate__(self, state):
        """Deserialization"""
        self.__dict__ = state
        self.declaredInNodes = None
        # fix deserialized info value :
        # make it None when it is empty string
        if self.info is not None:
            if len(self.info) == 0:
                self.info = None
        # fix deserialized annotations property :
        # if it is not there, create it
        if 'annotations' not in self.__dict__:
            self.annotations = Annotations()
        # fix deserialized parsedValue property :
        # if it is not there, create it
        if 'parsedValue' not in self.__dict__:
            try:
                self.parsedValue = parseFieldValue(self.type, self.value)
            except ValueError:
                # value in the old specification cannot be parsed,
                # use None
                self.parsedValue = None

    def copy(self):
        """F.copy() -> a deep copy of F"""
        return Field(self.type, self.accessType, self.name,
                     self.value, self.validValueTypes, self.annotations,
                     self.info)

    def addDeclarationNode(self, node):
        if self.declaredInNodes is None:
            self.declaredInNodes = []
        if node not in self.declaredInNodes:
            self.declaredInNodes.append(node)

    def getDeclarationNodes(self):
        return self.declaredInNodes

    def getType(self):
        return self.type

    def getAccessType(self):
        return self.accessType

    def getAccessTypeName(self):
        if self.accessType >= 0 and self.accessType < 4:
            return self.accessTypeNames[self.accessType]
        else:
            return str(self.accessType)

    def getAccessTypeConst(self):
        if self.accessType >= 0 and self.accessType < 4:
            return self.accessTypeConsts[self.accessType]
        else:
            return str(self.accessType)

    def getName(self):
        return self.name

    def setValue(self, value):
        self.value = value
        self.parsedValue = parseFieldValue(self.type, value)

    def getValue(self):
        return self.value

    def getParsedValue(self):
        return self.parsedValue

    def getValidValueTypes(self):
        return self.validValueTypes

    def setValidValueTypes(self, validValueTypes):
        self.validValueTypes = validValueTypes

    def getValidValueTypesStr(self):
        if self.validValueTypes:
            return '[' + ','.join(self.validValueTypes) + ']'
        return ''

    def getAnnotations(self):
        return self.annotations

    def getInfo(self):
        return self.info

    def toString(self, typePadLen=0, accessTypeNamePadLen=0,
                 namePadLen=0, valuePadLen=0, validValueTypesPadLen=0):
        info = self.info

        if self.validValueTypes:
            vvt = self.getValidValueTypesStr().ljust(validValueTypesPadLen)+' '
        else:
            vvt = ''

        info = vvt
        if self.info is not None:
            info += '# '+self.info
        elif self.annotations is not None:
            info += '# '+self.getAnnotations().toString()

        if self.value:
            value = self.value.ljust(valuePadLen)
        else:
            value = ' '*valuePadLen
        
        return self.type.ljust(typePadLen)+' '+\
               self.getAccessTypeName().ljust(accessTypeNamePadLen)+' '+\
               self.name.ljust(namePadLen)+' '+\
               value+' '+info

    def __hash__(self):

        h = hash(len(self.validValueTypes))
        for vvt in self.validValueTypes:
            h = h ^ hash(vvt)

        return (hash(self.type) ^ hash(self.accessType) ^ \
                hash(self.value) ^ h ^ hash(self.annotations) ^ \
                hash(self.info))

    def __eq__(self, other):
        return (self.type == other.type and \
                self.accessType == other.accessType and \
                self.value == other.value and \
                self.validValueTypes == other.validValueTypes and \
                self.annotations == other.annotations and \
                self.info == other.info)

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return self.toString()

    def __repr__(self):
        s = 'Field(%s, %s, %s, %s, %s, %s, %s)' % (repr(self.type),
                                                   self.getAccessTypeConst(),
                                                   repr(self.name),
                                                   repr(self.value),
                                                   repr(self.validValueTypes),
                                                   repr(self.annotations),
                                                   repr(self.info))
        return s

    def toXML(self, xmlgen):
        xmlgen.startElement('field', {'name' : self.name,
                                      'type' : self.type,
                                      'accessType' : self.getAccessTypeName()})

        xmlgen.startElement('value', {})
        if self.value:
            xmlgen.characters(self.value)
        xmlgen.endElement('value')
        
        xmlgen.startElement('validValueTypes', {})
        if self.validValueTypes:
            for t in self.validValueTypes:
                xmlgen.startElement('type', {})
                xmlgen.characters(t)
                xmlgen.endElement('type')
        xmlgen.endElement('validValueTypes')
        
        xmlgen.startElement('info', {})
        if self.info:
            xmlgen.characters(self.info)
        xmlgen.endElement('info')
        
        xmlgen.endElement('field')

class Node(object):

    __serialize__ = ['type', 'superTypes', 'fields', 'specFile',
                     'abstract', 'componentName',
                     'attributes']

    def __init__(self, type=None, superTypes=None, fields=None, specFile=None,
                 abstract=False, componentName=None, attributes=None):
        self.type = type
        if superTypes:
            self.superTypes = superTypes[:]
        else:
            self.superTypes = []
        # Note: fieldMap is updated by addField
        self.fieldMap = {}
        if fields:
            self.fields = fields[:]
            for field in self.fields:
                fieldName = field.getName()
                if field in self.fieldMap:
                    raise NodeDBException('In node %s field %s'     \
                                          ' was already declared' % \
                                          (self.type, field.getName()))

                self.fieldMap[field.getName()] = field
        else:
            self.fields = []

        self.specFile = specFile
        self.abstract = abstract
        self.componentName = componentName
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes.copy()
        # superNodes and derivedNodes fields are updated by the NodeDB class,
        # be sure that it is up-to-date before accessing it.
        self.superNodes = None
        self.derivedNodes = None

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state
        if self.__dict__.get('attributes') is None:
            self.attributes =  {}
        self.superNodes = None
        self.derivedNodes = None

    def isAbstract(self):
        return self.abstract

    def setAbstract(self, abstract):
        self.abstract = bool(abstract)

    def setAttribute(self, name, value):
        if name == 'abstract':
            self.setAbstract(value)
        elif name == 'componentName':
            self.setComponentName(value)
        else:
            self.attributes[name] = value

    def getAttribute(self, name):
        if name == 'abstract':
            return self.isAbstract()
        elif name == 'componentName':
            return self.getComponentName()
        else:
            return self.attributes.get(name)

    def getComponentName(self):
        return self.componentName

    def setComponentName(self, componentName):
        self.componentName = str(componentName)

    def getType(self):
        return self.type

    def setSpecFile(self, specFile):
        self.specFile = specFile

    def getSpecFile(self):
        return self.specFile

    def getSuperTypes(self):
        return self.superTypes

    def setSuperTypes(self, superTypes):
        self.superTypes = superTypes[:]

    def addField(self, field):
        if field.name in self.fieldMap:
            return False
        self.fields.append(field)
        self.fieldMap[field.name] = field
        return True

    def removeField(self, field):
        if field.name not in self.fieldMap:
            return False
        del self.fieldMap[field.name]
        self.fields.remove(field)
        return True

    def findField(self, fieldName):
        return self.fieldMap.get(fieldName)

    def getFieldAt(self, fieldIndex):
        return self.fields[fieldIndex]

    def getNumFields(self):
        return len(self.fields)

    def getFields(self):
        return self.fields

    # support for super nodes, derived nodes, and own fields
    # results are valid only after NodeDB.updateHierarchy was called

    def getOwnFields(self):
        return [f for f in self.getFields() if self in f.getDeclarationNodes()]

    def getDerivedNodes(self):
        return self.derivedNodes

    def addDerivedNode(self, node):
        if self.derivedNodes is None:
            self.derivedNodes = [node]
        elif node not in self.derivedNodes:
            self.derivedNodes.append(node)

    def hasDerivedNode(self, node):
        return node in self.derivedNodes

    def clearDerivedNodes(self):
        self.derivedNodes = []

    def getSuperNodes(self):
        return self.superNodes

    def addSuperNode(self, node):
        if self.superNodes is None:
            self.superNodes = [node]
        elif node not in self.superNodes:
            self.superNodes.append(node)

    def hasSuperNode(self, node):
        return node in self.superNodes

    def clearSuperNodes(self):
        self.superNodes = []

    def diff(self, other, fullDiff=False):
        # check differences
        # - data unique to self
        # + data unique to other

        result = []
        if self.type != other.type:
            result.append('- type %s' % repr(self.type))
            result.append('+ type %s' % repr(other.type))
            
        if self.superTypes != other.superTypes:
            result.append('- superTypes %s' % repr(self.superTypes))
            result.append('+ superTypes %s' % repr(other.superTypes))

        if fullDiff and (self.specFile != other.specFile):
            result.append('- specFile %s' % repr(self.specFile))
            result.append('+ specFile %s' % repr(other.specFile))

        if self.abstract != other.abstract:
            result.append('- abstract %s' % repr(self.abstract))
            result.append('+ abstract %s' % repr(other.abstract))

        if self.componentName != other.componentName:
            result.append('- componentName %s' % repr(self.componentName))
            result.append('+ componentName %s' % repr(other.componentName))

        if self.attributes != other.attributes:
            result.append('- attributes %s' % repr(self.attributes))
            result.append('+ attributes %s' % repr(other.attributes))

        # Note: we use built-in set here, it is available starting
        # with Python 2.4.

        # fields
        self_fieldNames = set([f.getName() for f in self.fields])
        other_fieldNames = set([f.getName() for f in other.fields])

        commonFieldNames = self_fieldNames.intersection(other_fieldNames)
        removedFieldNames = self_fieldNames.difference(other_fieldNames)
        addedFieldNames = other_fieldNames.difference(self_fieldNames)

        for fn in commonFieldNames:
            field1 = self.findField(fn)
            field2 = other.findField(fn)

            if field1 != field2:
                result.append('- field %s' % str(field1))
                result.append('+ field %s' % str(field2))

        result.extend( [('- field %s' % str(self.findField(fn))) \
                        for fn in removedFieldNames] )
        result.extend( [('+ field %s' % str(other.findField(fn))) \
                        for fn in addedFieldNames] )
        
        if len(result):
            result.insert(0, '@@ node %s @@' % self.type)
            result.append('')
            
        return result

    def __eq__(self, other):
        self_fields = self.fields[:]
        other_fields = other.fields[:]

        key_func = lambda field: field.getName()

        self_fields.sort(key=key_func)
        other_fields.sort(key=key_func)
        
        return (self.type == other.type and \
                self.superTypes == other.superTypes and \
                self_fields == other_fields and \
                self.specFile == other.specFile and \
                self.abstract == other.abstract and \
                self.componentName == other.componentName)

    def __ne__(self, other):
        return not (self == other)

    # convert to X3D specification format
        
    def __str__(self):
        s = str(self.type)
        if len(self.superTypes) > 0:
            s += ' : %s' % (','.join(self.superTypes),)
        s += ' {\n'

        if self.isAbstract():
            s += '  attribute abstract TRUE\n'

        s += '  attribute componentName "%s"\n' % self.componentName

        for k,v in self.attributes.items():
            if v == True:
                v = 'TRUE'
            elif v == False:
                v = 'FALSE'
            elif isinstance(v, str):
                v = "\"%s\"" % v
            s += '  attribute ' + k + ' ' + str(v) +'\n'

        def myLen(s):
            if s:
                return len(s)
            else:
                return 0

        # type accessTypeName name value validValueTypes
        maxLen = [0, 0, 0, 0, 0]
        for field in self.fields:
            maxLen[0] = max(maxLen[0], myLen(field.type))
            maxLen[1] = max(maxLen[1], myLen(field.getAccessTypeName()))
            maxLen[2] = max(maxLen[2], myLen(field.name))
            maxLen[3] = max(maxLen[3], myLen(field.value))
            maxLen[4] = max(maxLen[4], myLen(field.getValidValueTypesStr()))
        
        for field in self.fields:
            s += '  ' + field.toString(*maxLen)+'\n'
        s += '}'
        return s

    def __repr__(self):
        return makeObjectRepr(self)

    def toPythonCode(self, var='_n'):
        s = '################ %s ################\n' % self.type
        s += '%s = Node(type=%s)\n' % (var, repr(self.type))
        s += '%s.setSuperTypes(%s)\n' % (var, repr(self.superTypes))
        s += '%s.setSpecFile(%s)\n' % (var, repr(self.specFile))
        s += '%s.setAbstract(%s)\n' % (var, repr(self.abstract))
        s += '%s.setComponentName(%s)\n' % (var, repr(self.componentName))
        s += '# fields\n'
        for field in self.fields:
            s+= '%s.addField(%s)\n' % (var, repr(field))
        return s

    def toXML(self, xmlgen):


        if self.abstract:
            abstract = 'true'
        else:
            abstract = 'false'
        
        xmlgen.startElement('node', {'type' : self.type,
                                     'abstract' : abstract,
                                     'componentName' : self.componentName})

        xmlgen.startElement('fields', {})
        for field in self.fields:
            field.toXML(xmlgen)
        xmlgen.endElement('fields')

        xmlgen.startElement('specFile', {})
        xmlgen.characters(self.specFile)
        xmlgen.endElement('specFile')

        xmlgen.endElement('node')

class NodeDB(object):

    __serialize__ = ['nodeList']

    def __init__(self, nodeList=None):
        # nodeDict maps node typename to node
        # Note: nodeDict is updated by addNode
        self.nodeDict = {}

        # list of stored nodes
        if nodeList:
            self.nodeList = nodeList[:]
            for node in self.nodeList:
                typeName = node.getType()
                if typeName in self.nodeDict:
                    raise NodeDBException('Node %s is already in the database'\
                                          % typeName)
                self.nodeDict[typeName] = node
        else:
            self.nodeList = []

        # list of root nodes, updated by updateHierarchy function
        self.rootNodes = []

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state
        self.rootNodes = []

    def getNode(self, typeName):
        return self.nodeDict.get(typeName)

    def getNodeList(self):
        return self.nodeList

    def getDerivedNodes(self, node):
        assert self.nodeDict[node.getType()] is node
        
        derivedNodes = node.getDerivedNodes()
        if derivedNodes is None:
            self.updateHierarchy()
            return node.getDerivedNodes()
        return derivedNodes

    def getSuperNodes(self, node):
        assert self.nodeDict[node.getType()] is node
        
        superNodes = node.getSuperNodes()
        if superNodes is None:
            self.updateHierarchy()
            return node.getSuperNodes()
        return superNodes

    def getRootNodes(self):
        return self.rootNodes

    def addNode(self, node):
        typeName = node.getType()
        if typeName in self.nodeDict:
            raise NodeDBException('Node %s is already in the database'\
                                  % typeName)
        self.nodeList.append(node)
        self.nodeDict[typeName] = node


    def diff(self, other, fullDiff=False):
        # check differences
        # - data unique to self
        # + data unique to other

        result = []

        # Note: we use built-in set here, it is available starting
        # with Python 2.4.

        self_nodeTypes = set([n.getType() for n in self.nodeList])
        other_nodeTypes = set([n.getType() for n in other.nodeList])

        commonNodeTypes = self_nodeTypes.intersection(other_nodeTypes)
        removedNodeTypes = self_nodeTypes.difference(other_nodeTypes)
        addedNodeTypes = other_nodeTypes.difference(self_nodeTypes)

        for nt in commonNodeTypes:
            node1 = self.getNode(nt)
            node2 = other.getNode(nt)
            result.extend(node1.diff(node2, fullDiff))

        result.extend( [('- node %s' % nt) for nt in removedNodeTypes] )
        result.extend( [('+ node %s' % nt) for nt in addedNodeTypes] )

        return result

    def __eq__(self, other):
        self_nodeList = self.nodeList[:]
        other_nodeList = other.nodeList[:]

        key_func = lambda node: node.getType()

        self_nodeList.sort(key=key_func)
        other_nodeList.sort(key=key_func)
        
        return self_nodeList == other_nodeList

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return makeObjectRepr(self)

    def toPythonCode(self, var='_ndb'):
        s = 'from nodedb import *\n'
        s += '%s = NodeDB()\n' % var
        for node in self.nodeList:
            s += '\n'
            s += node.toPythonCode('_n')
            s += '%s.addNode(_n)\n' % var
        s += 'del _n\n'
        return s

    def toXML(self, xmlgen):
        xmlgen.startElement('nodedb', {})

        xmlgen.startElement('nodeList', {})
        for node in self.nodeList:
            node.toXML(xmlgen)
        xmlgen.endElement('nodeList')

        xmlgen.endElement('nodedb')

    def findFirstFieldDeclNodes(self, node, fieldName):
        if node.findField(fieldName) is None:
            return []
        result = []
        for n in node.getSuperNodes():
            result.extend(self.findFirstFieldDeclNodes(n, fieldName))
        if len(result) == 0:
            result = [node]
        return result
            
    def updateHierarchy(self):
        self.rootNodes = []
        
        for node in self.nodeList:
            node.clearSuperNodes()
            node.clearDerivedNodes()

        for node in self.nodeList:
            nodeType = node.getType()
            superTypes = node.getSuperTypes()
            for superType in superTypes:
                superNode = self.getNode(superType)
                if superNode is None:
                    raise NodeDBException('In node %s super type %s' \
                                          ' is not declared' % \
                                          (nodeType, superType))
                node.addSuperNode(superNode)
                superNode.addDerivedNode(node)

            if len(superTypes) == 0:
                self.rootNodes.append(node)

        # compute for every field node types where this field was declared
        # first time
        for node in self.nodeList:
            for field in node.getFields():
                declInNodes = self.findFirstFieldDeclNodes(node,
                                                           field.getName())
                for n in declInNodes:
                    field.addDeclarationNode(n)
            
    def save(self, filename):
        # check if the file object is provided instead of string
        if getattr(filename, 'write', None) is not None:
            fd = filename
            closeFile = False
        else:
            fd = open(filename, 'w')
            closeFile = True

        try:
            pickle.dump(self, fd)
        finally:
            if closeFile:
                fd.close()

    def saveAsPythonCode(self, filename):
        fd = open(filename, 'w')
        fd.write(repr(self)+'\n')
        fd.close()

def loadFromPythonCode(filename):
    fd = open(filename, 'r')
    code = fd.read()
    fd.close()
    ndb = eval(code)
    ndb.updateHierarchy()
    return ndb

def load(filename):

    # check if the file object is provided instead of string
    if (getattr(filename, 'read', None) is not None and \
        getattr(filename, 'readline', None) is not None):
        fd = filename
        closeFile = False
    else:
        fd = open(filename, 'r')
        closeFile = True

    try:
        ndb = pickle.load(fd)
    finally:
        if closeFile:
            fd.close()
        
    ndb.updateHierarchy()
        
    return ndb

class NodeDBEncoder(json.JSONEncoder):

    def default(self, obj):
        if (isinstance(obj, Field) or \
            isinstance(obj, Node)  or \
            isinstance(obj, NodeDB) or \
            isinstance(obj, Annotation) or \
            isinstance(obj, Annotations) or \
            isinstance(obj, NullNode)):

            objectDict = getObjectDict(obj)
            objectDict['__class__'] = obj.__class__.__name__

            return objectDict
            
        return json.JSONEncoder.default(self, obj)

def toJSON(ndb):
    return json.dumps(ndb, sort_keys=True, indent=4, cls=NodeDBEncoder)

def toXML(v, xmlgen=None):
    if not xmlgen:
        import StringIO
        f = StringIO.StringIO()
        xmlgen = xml.sax.saxutils.XMLGenerator(f)
        v.toXML(xmlgen)
        return f.getvalue()
    else:
        return v.toXML(xmlgen)
