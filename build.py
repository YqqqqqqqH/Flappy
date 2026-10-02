"""Build index.html and dev.html from flappy-dawn.html (the artifact source).

  python build.py

flappy-dawn.html is the only file you edit. It has no doctype/html/head/body
because the Claude Artifact host wraps it at publish time. This script applies
the same wrapper so the game can be opened directly in a browser:

  index.html  standalone game, double-click to play
  dev.html    same, plus window.__dbg (game internals) and window.__events
              (a log of every marker trigger) for scripted testing
"""
import io
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'flappy-dawn.html')

HEAD = ('<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#fafafa}'
        'img{max-width:100%}[hidden]{display:none!important}</style></head><body>\n')
TAIL = '\n</body></html>\n'

DBG = (
    "requestAnimationFrame(frame); window.__dbg = { start, die, reset, flap, pipes, placeColumn, makeGaps, triggerGap, addScore, "
    "setScore: n => { score = n; }, setBird: (y, v) => { birdY = y; vy = v; }, advance: s => { t += s; }, "
    "state: () => ({ state, score, birdY, vy, speed, columnsMade, cols: pipes.map(c => ({ x: Math.round(c.x*10)/10, "
    "gaps: c.gaps.map(g => [Math.round(g.y*100)/100, g.size, g.marker]), segs: c.segs.map(sg => sg.map(n => Math.round(n*100)/100)) })) }), "
    "step: dt => { updatePlaying(dt); animateMarkers(dt); renderer.render(scene, camera); }, render: () => renderer.render(scene, camera) };"
)
EVENT_HOOK = ("function triggerGap(c, i) { (window.__events = window.__events || []).push("
              "[c.gaps[i].marker, score, Math.round(birdY * 100) / 100]);")


def replace_once(text, old, new, what):
    if text.count(old) != 1:
        sys.exit(f'build: expected exactly one match for {what}')
    return text.replace(old, new)


def syntax_check(path):
    node = shutil.which('node')
    if not node:
        print('build: node not found, skipping syntax check')
        return
    check = ("const fs=require('fs');const s=fs.readFileSync(process.argv[1],'utf8');"
             "const m=s.match(/<script>\\n([\\s\\S]*?)<\\/script>/);new Function(m[1]);console.log('syntax ok:',process.argv[1])")
    subprocess.run([node, '-e', check, path], check=True)


def main():
    src = io.open(SRC, encoding='utf-8').read()
    index = HEAD + src + TAIL
    dev = replace_once(src, '\nrequestAnimationFrame(frame);\n', '\n' + DBG + '\n', 'the main loop start')
    dev = replace_once(dev, 'function triggerGap(c, i) {', EVENT_HOOK, 'triggerGap')
    dev = HEAD + dev + TAIL
    for name, content in (('index.html', index), ('dev.html', dev)):
        io.open(os.path.join(HERE, name), 'w', encoding='utf-8', newline='\n').write(content)
        print('wrote', name, len(content), 'bytes')
    syntax_check(SRC)


if __name__ == '__main__':
    main()
