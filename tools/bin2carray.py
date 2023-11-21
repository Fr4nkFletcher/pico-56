# bin2carray.py
#
# Convert binary files into C arrays
#
# Copyright (c) 2023 Troy Schrapel
#
# This code is licensed under the MIT license
#
# https://github.com/visrealm/pico-56
#
#

import os
import sys
import glob
import re
import argparse
import datetime


def main() -> int:
    """
    main program entry-point
    """
    parser = argparse.ArgumentParser(
        description='Convert binary files into C-style arrays for use with the PICO-56.',
        epilog="GitHub: https://github.com/visrealm/pico-56")
    parser.add_argument('-v', '--verbose', help='verbose output', action='store_true')
    parser.add_argument('-p', '--prefix', help='array variable prefix', default='')
    parser.add_argument('-o', '--out', help='output file - defaults to base input file name with .c extension')
    parser.add_argument('-i', '--in', nargs='+', help='input file(s) to store in Pi Pico ROM - can use wildcards')
    args = vars(parser.parse_args())

    outSourceFileName = args['out']
    outSourceFile = None
    outHeaderFileName = ''
    outHeaderFile = None

    inFileNames = []

    for inGlob in args['in']:
        for inFileName in glob.glob(inGlob):
            inFileNames.append(inFileName)

    if outSourceFileName:
        outSourceFile = open(outSourceFileName, "w")
        outHeaderFileName = os.path.splitext(outSourceFileName)[0] + ".h"
        outHeaderFile = open(outHeaderFileName, "w")

        outSourceFile.write(getFileHeader(outSourceFileName, inFileNames, args, isHeaderFile=False))
        outHeaderFile.write(getFileHeader(outHeaderFileName, inFileNames, args, isHeaderFile=True))

    for infile in inFileNames:
        processFile(infile, outSourceFile,
                    outHeaderFile, args)

    outSourceFile.close()
    outHeaderFile.write("\n#endif")
    outHeaderFile.close()

    fileList = ""
    for infile in inFileNames:
        fileList += os.path.split(infile)[1] + ", "

    print(sys.argv[0] + " generated C data arrays in " +
          os.path.join(os.getcwd(), outSourceFile.name) + " from (" + fileList.rstrip(", ") + ")")

    return 0


def getFileHeader(fileName, fileList, args, isHeaderFile) -> str:
    """
    write the header at the top of the .c/.h file
    """
    timestamp = datetime.datetime.now()
    hdrText = (
        f"/*\n"
        f" * Data file generated by {os.path.split(sys.argv[0])[1]}\n"
        f" * Copyright (c) {timestamp.strftime('%Y')} Troy Schrapel\n"
        f" *\n"
        f" * Generated using the following command:\n"
        f" *   > cd {os.getcwd()}\n"
        f" *   > python3 {' '.join(sys.argv[:])}\n"
        f" *\n"
        f" * Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f" *\n"
        f" * Contains the following images:\n"
        f" *\n")

    for infile in fileList:
        hdrText += f" * - {os.path.split(infile)[1]}\n"

    hdrText += " */\n\n"

    if isHeaderFile:
        baseName = args['prefix'] + "_" + os.path.basename(fileName)
        sanitizedFile = re.sub('[^0-9a-zA-Z]+', '_', baseName.upper())
        hdrText += f"#ifndef _{sanitizedFile}\n"
        hdrText += f"#define _{sanitizedFile}\n\n"
    else:
        hdrText += "#include \"pico/platform.h\"\n"
    hdrText += "#include <inttypes.h>"
    return hdrText


def generateArrayComment(infile, src) -> str:
    """
    generate a comment bloack for an image giving some metadata
    """
    comment = "\n\n/* source: " + infile + "\n"

    src.seek(0, os.SEEK_END)

    comment += " * size  : " + str(src.tell()) + " bytes */\n"

    src.seek(0, os.SEEK_SET)

    return comment


def generateProto(varName, isHeader) -> str:
    """
    generate an array prototype (or definition)
    """
    typePrefix = ("extern " if isHeader else " ")
    varNamePrefix = "" if isHeader else ("__aligned(4) ")
    dataType = "const uint8_t "
    suffix = ";" if isHeader else " = "
    proto = ""

    # output the image array prototype
    proto += typePrefix + dataType + varNamePrefix + varName + "[]" + suffix
    return proto


def dataToArrayContents(src) -> str:
    """
    return a string containing a c-style array of the image pixels
    """
    values = []
    data = bytearray(src.read())
    for b in data:
        values.append("{0:#0{1}x}".format(b, 4))

    return "\n  " + (", ".join(values))


def processFile(infile, srcOutput, hdrOutput, args) -> None:
    """
    process a single image and output it to the header and source files
    """
    outPathWithoutExt = os.path.splitext(infile)[0]
    closeFile = False
    if srcOutput == None:
        srcOutput = open(outPathWithoutExt + ".c", "w")
        srcOutput.write(getFileHeader(srcOutput.name, [infile], args, isHeaderFile=False))
        hdrOutput = open(outPathWithoutExt + ".h", "w")
        hdrOutput.write(getFileHeader(hdrOutput.name, [infile], args, isHeaderFile=True))
        closeFile = True

    varName = os.path.split(infile)[1]
    varName = re.sub('[^0-9a-zA-Z]+', '_', args['prefix'] + varName)

    try:
        src = open(infile, "rb")

        comment = generateArrayComment(infile, src)

        hdrOutput.write(comment)
        hdrOutput.write(generateProto(
            varName, isHeader=True) + "\n")

        srcOutput.write(comment)
        srcOutput.write(generateProto(
            varName, isHeader=False) + "{")
        srcOutput.write(dataToArrayContents(src) + "};")

        src.close()

    except IOError:
        print("cannot convert", infile)

    if closeFile:
        srcOutput.close()
        hdrOutput.write("\n#endif")
        hdrOutput.close()

    return


# program entry
if __name__ == "__main__":
    sys.exit(main())