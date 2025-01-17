########################################################################
#
#  zxing.py -- a quick and dirty wrapper for zxing for python
#
#  this allows you to send images and get back data from the ZXing
#  library:  http://code.google.com/p/zxing/
#
#  by default, it will expect to be run from the zxing source code directory
#  otherwise you must specify the location as a parameter to the constructor
#

__version__ = '0.3'
import subprocess, re, os
import shlex
import tempfile
from contextlib import contextmanager
import cv2

class BarCodeReader():
  location = ""
  command = "java"
  libs = ["javase/target/javase-3.4.0-jar-with-dependencies.jar"]
  args = ["-cp", "LIBS",
          "-Djava.awt.headless=true",
          "com.google.zxing.client.j2se.CommandLineRunner"]

  def __init__(self, loc=""):
    if not len(loc):
      if (os.environ.has_key("ZXING_LIBRARY")):
        loc = os.environ["ZXING_LIBRARY"]
      else:
        loc = ".."

    self.location = loc

  def list_formats(self):
      return ["UPC_A",
                "UPC_E",
                "EAN_13",
                "EAN_8",
                "RSS_14",
                "RSS_EXPANDED",
                "CODE_39",
                "CODE_93",
                "CODE_128",
                "ITF",
                "QR_CODE",
                "DATA_MATRIX",
                "AZTEC",
                "PDF_417",
                "CODABAR",
                "MAXICODE"]

  @contextmanager
  def _temp_ramfile_input(self, img):
      temp_name = tempfile.mktemp(suffix=".png", dir="/dev/shm")
      cv2.imwrite(temp_name, img)
      try:
          yield temp_name
      finally:
          os.unlink(temp_name)

  @contextmanager
  def _temp_file_from_bytes(self, img_bytes):
      temp_name = tempfile.mktemp(dir="/dev/shm") #extension doesn't matter
      with open(temp_name, 'wb') as output:
          output.write(img_bytes)
      try:
          yield temp_name
      finally:
          #time.sleep(0.5)
          os.unlink(temp_name)

  def decode_bytes(self, img_bytes, multi=True, pure=False, possible_formats=None):
    cmd = [self.command]
    cmd += self.args[:] #copy arg values
    if multi:
      cmd.append("--multi")
    if possible_formats is not None:
      cmd.append("--possible_formats " + possible_formats)
    if pure:
      cmd.append("--pure_barcode")
    cmd.append("--try_harder")

    libraries = [self.location + "/" + l for l in self.libs]

    cmd = [ c if c != "LIBS" else os.pathsep.join(libraries) for c in cmd ]

    stdout=None
    stderr=None
    with self._temp_file_from_bytes(img_bytes) as file_name:
        cmd.append(file_name)
        cmd = ' '.join(cmd)
        (stdout, stderr) = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, universal_newlines=True).communicate()

    codes = []
    file_results = stdout.split("\nfile:")
    for result in file_results:
      lines = stdout.split("\n")
      if re.search("No barcode found", lines[0]):
        codes.append(None)
        continue

      codes.append(BarCode(result))
    return codes

  #NOTE: possible_formats should be a comma-separated list
  def decode(self, img, multi=True, pure=False, possible_formats=None):
    if type(img) is not str and type(img[0]) is str:
      raise Exception("Only a single file argument is accepted")
    cmd = [self.command]
    cmd += self.args[:] #copy arg values
    if multi:
      cmd.append("--multi")
    if possible_formats is not None:
      cmd.append("--possible_formats " + possible_formats)
    if pure:
      cmd.append("--pure_barcode")
    cmd.append("--try_harder")

    libraries = [self.location + "/" + l for l in self.libs]

    cmd = [ c if c != "LIBS" else os.pathsep.join(libraries) for c in cmd ]

    stdout=None
    stderr=None
    if type(img) is not str: #then assume it's a writeable image
        with self._temp_ramfile_input(img) as file_name:
            cmd.append(file_name)
            cmd = ' '.join(cmd)
            (stdout, stderr) = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, universal_newlines=True).communicate()
    else:
        cmd.append(img)
        cmd = ' '.join(cmd)
        (stdout, stderr) = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, universal_newlines=True).communicate()

    codes = []
    file_results = stdout.split("\nfile:")
    for result in file_results:
      lines = stdout.split("\n")
      if re.search("No barcode found", lines[0]):
        codes.append(None)
        continue

      codes.append(BarCode(result))
    return codes

#this is the barcode class which has
class BarCode:
  format = ""
  points = []
  data = ""
  raw = ""

  def __init__(self, zxing_output):
    lines = zxing_output.split("\n")
    raw_block = False
    parsed_block = False
    point_block = False

    self.points = []
    for l in lines:
      m = re.search("format:\s([^,]+)", l)
      if not raw_block and not parsed_block and not point_block and m:
        self.format = m.group(1)
        continue

      if not raw_block and not parsed_block and not point_block and l == "Raw result:":
        raw_block = True
        continue

      if raw_block and l != "Parsed result:":
        self.raw += l + "\n"
        continue

      if raw_block and l == "Parsed result:":
        raw_block = False
        parsed_block = True
        continue

      if parsed_block and not re.match("Found\s\d\sresult\spoints", l):
        self.data += l + "\n"
        continue

      if parsed_block and re.match("Found\s\d\sresult\spoints", l):
        parsed_block = False
        point_block = True
        continue

      if point_block:
        m = re.search("Point\s(\d+):\s\(([\d\.]+),([\d\.]+)\)", l)
        if (m):
          self.points.append((float(m.group(2)), float(m.group(3))))

    return


if __name__ == "__main__":
  print("ZXing module")
