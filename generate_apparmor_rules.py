#!/usr/bin/python3

import sys

blocks=[]

#
# blocks is an array of paths under which we want to block by
# default.
#
#  blocks[0] = ['path' = '/sys', 'children' = [A,B] ]
#  blocks[1] = ['path' = '/proc/sys', 'children' = [ E ] ]
#  A = [ 'path' = 'fs', children = [C] ]
#  C = [ 'path' = 'cgroup', children = [F] ]
#  B = [ 'path' = 'class', children = [D] ]
#  D = [ 'path' = 'net', children = [F] ]
#  E = [ 'path' = 'shm*' ]
#  F = [ 'path' = '**' ]

def add_block(path):
    for b in blocks:
        if b['path'] == path:
            # duplicate
            return
    blocks.append({'path': path.strip(), 'children': []})

def child_get(prev, path):
    for p in prev:
        if p['path'] == path:
            return p
    return None

def add_allow(path):
    # find which block we belong to
    found=None
    for b in blocks:
        l=len(b['path'])
        if len(path) <= l:
            continue
        if path[0:l] == b['path']:
            found=b
            break
    if found is None:
        print("allow with no previous block at %s" % path)
        sys.exit(1)
    p = path[l:].strip()
    while p[:1] == "/":
        p = p[1:]
    prev = b['children']
    for s in p.split('/'):
        n = {'path': s.strip(), 'children' : [] }
        tmp = child_get(prev, n['path'])
        if tmp is not None:
            prev = tmp
        else:
            prev.append(n)
            prev = n['children']

config="config"
if len(sys.argv) > 1:
    config=sys.argv[1]
with open(config) as f:
    for x in f.readlines():
        x.strip()
        if x[:1] == '#':
            continue
        try:
            (cmd,path) = x.split(' ')
        except: # blank line
            continue
        if cmd == "block":
            add_block(path)
        elif cmd == "allow":
            add_allow(path)
        else:
            print("Unknown command: %s"% cmd)
            sys.exit(1)

# print("%s" % blocks)

denies=[]

def collect_chars(children, ref, index):
    r = ""
    for c in children:
        if index >= len(c['path']):
            continue
        if ref[0:index] != c['path'][0:index]:
            continue
        r = r + c['path'][index]
    return r

def append_deny(s):
    if s not in denies:
        denies.append("%s wklx," % s)

def gen_denies(pathsofar, children):
    for c in children:
        for char in range(len(c['path'])):
            if char == len(c['path'])-1 and c['path'][char] == '*':
                continue
            if char == len(c['path'])-2 and c['path'][char:char+2] == '**':
                continue
            x = collect_chars(children, c['path'], char)
            newdeny = "deny %s/%s[^%s]*{,/**}" % (pathsofar, c['path'][0:char], x)
            append_deny(newdeny)
        if c['path'] != '**' and c['path'][len(c['path'])-1] != '*':
            newdeny = "deny %s/%s?*{,/**}" % (pathsofar, c['path'])
            append_deny(newdeny)
        elif c['path'] != '**':
            newdeny = "deny %s/%s/**"% (pathsofar, c['path'])
            append_deny(newdeny)
        if len(c['children']) != 0:
            newpath = "%s/%s" % (pathsofar, c['path'])
            gen_denies(newpath, c['children'])

for b in blocks:
    gen_denies(b['path'], b['children'])

denies.sort()
for d in denies:
    print(d)
