#!python3
import os, sys, glob, re, argparse, shutil
from os import path
# Note: Python 3.5 or later is required !

def concat_files(in_files, out_file):
  with open(out_file, 'wb') as wfd:
    for f in in_files:
        with open(f, 'rb') as fd:
            shutil.copyfileobj(fd, wfd, 1024*1024*10)


def find_glob(root, filename, recursive):
  if recursive:
    filename = '**/' + filename
  return glob.glob(path.join(root, filename), recursive=recursive)

def find_pdbs(root = '.', recursive = False):
  return find_glob(root, '*.pdb', recursive)

def find_obj_symbols(root = '.', recursive = False):
  return find_glob(root, 'all_obj.smb', recursive)

def find_objs(root = '.', recursive = False):
  return find_glob(root, '*.obj', recursive)

def find_dirs_with_objs(root = '.'):
  all_objs = find_objs(root, True)
  return list(set(map(lambda x: path.dirname(x), all_objs)))


def analyze_objs_with_pdbs(symbols, pdbs, outfile='object_files.report', options=[]):
  in_objs = ' '.join(map(lambda f: '-in:comdat ' + f, symbols))
  info_pdbs = ' '.join(map(lambda f: '-info ' + f, pdbs)) if pdbs is not None else ''
  with open('options.txt', 'wt') as f:
    f.write(
      "-out %s\n" % outfile
      + in_objs + '\n'
      + info_pdbs + '\n'
      + ' '.join(options) + '\n'
    )
  os.system('SymbolSort -options_from_file options.txt')

def dumpbin_file(bin_file, force = False):
  smb_file = bin_file + '.smb'
  if force or not path.isfile(smb_file) or path.getmtime(bin_file) >= path.getmtime(smb_file):
    print("dumping %s..." % bin_file)
    os.system('dumpbin /headers %s >%s' % (bin_file, smb_file))
  return smb_file

def dump_all_symbols(root = '.', recursive = False, force = False):
  if recursive:
    dirs = find_dirs_with_objs(root)
    for d in dirs:
      dump_all_symbols(d, False, force)
    return
  obj_files = find_objs(root, False)
  smb_files = list(map(lambda f: dumpbin_file(f, force), obj_files))
  concat_files(smb_files, path.join(root, 'all_obj.smb'))


def run_objs_with_pdbs(objs, pdbs, options=[]):
  smbs = find_obj_symbols(objs, True)
  if pdbs is not None:
    pdbs = find_pdbs(pdbs, True)
  analyze_objs_with_pdbs(smbs, pdbs, options = options)


parser = argparse.ArgumentParser(description='Analyze code bloat using SymbolSort.')
parser.add_argument('--obj', nargs='?', help='path to directory with .OBJ files (recursive)')
parser.add_argument('--pdb', nargs='?', help='path to directory with .PDB files (recursive)')
parser.add_argument('--dump', action='store_true', help='run dumpbin for all .OBJ files')
parser.add_argument('--analyze', action='store_true', help='perform analysis of all the specified data')
parser.add_argument('--file', nargs='?', help='analyze single binary file')
args, unknown_args = parser.parse_known_args()
print(args, unknown_args)

if args.file is not None:
  fn = args.file
  if path.splitext(fn)[1] == '.obj':
    fn = dumpbin_file(fn)
  if path.splitext(fn)[1] == '.smb':
    analyze_objs_with_pdbs([fn], None, outfile = fn + '.report', options = ['-complete'] + unknown_args)
  if path.splitext(fn)[1] in ['.exe', '.dll', '.pdb']:
    os.system('SymbolSort -in %s -out %s.report %s' % (fn, fn, " ".join(unknown_args)))
  sys.exit(0)

if not args.dump and not args.analyze:
  parser.print_help()
  sys.exit(1)
if args.obj is None:
  print("Must specify path to .OBJ files")
  sys.exit(1)

if args.dump:
  dump_all_symbols(args.obj, True)
if args.analyze:
  run_objs_with_pdbs(args.obj, args.pdb, options = unknown_args)
