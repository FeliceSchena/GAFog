#!/usr/bin/python3
from mako.template import Template
import argparse
import json
import subprocess
import pathlib

def get_filename(ftemplate):
    return ftemplate.replace('.mako', '')

def process_template(ftemplate, sol):
    mytemplate=Template(filename=ftemplate)
    return mytemplate.render(mapping=sol)

def render_image(dotcode, type='svg'):
    #subprocess.run(['dot', dotfile, '-Tsvg', '-O'])
    p = subprocess.run(['dot', '-T%s'%type], input=bytearray(dotcode.encode()), capture_output=True)
    return p.stdout

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', help='output file. Default graph.svg')
    parser.add_argument('-f', '--file', help='input file. Default use sample_output.json')
    args = parser.parse_args()
    fdata = args.file if args.file is not None else 'sample_output.json'
    ftemplate = 'graph.dot.mako'
    with open(fdata, 'r') as f:
        data = json.load(f)
    out = process_template(ftemplate, data)
    fout = args.output if args.output is not None else 'graph.svg'
    if fout.endswith('.dot'):
        with open(fout, 'w') as f:
            f.write(out)
    else:
        type=pathlib.Path(fout).suffix
        with open(fout, 'wb') as f:
            f.write(render_image(out))        