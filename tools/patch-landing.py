from pathlib import Path
import re
import subprocess

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Remove radar and collapse the status block to the operator flow only.
status_start = s.find('<div class="status">')
visual_start = s.find('</section><section class="visual">', status_start)
if status_start != -1 and visual_start != -1:
    status = '<div class="status"><div class="flow"><strong>&gt;</strong> HUNT<br><strong>&gt;</strong> VERIFY<br><strong>&gt;</strong> ENRICH<br><strong>&gt;</strong> EXPLAIN</div></div>'
    s = s[:status_start] + status + s[visual_start:]
radar_css = s.find('.radar{')
visual_css = s.find('.visual{', radar_css)
if radar_css != -1 and visual_css != -1:
    s = s[:radar_css] + s[visual_css:]
s = s.replace('.status{margin-top:auto;border-top:1px solid var(--line);padding-top:18px;display:grid;grid-template-columns:1fr 180px;gap:18px;align-items:end;}', '.status{margin-top:auto;border-top:1px solid var(--line);padding-top:18px;display:block;}')
s = s.replace('.flow{font-size:10px;line-height:1.7', '.flow{font-size:11px;line-height:1.75')
s = s.replace('.status{grid-template-columns:1fr 180px}', '')
s = s.replace('.status{grid-template-columns:1fr}.radar{width:100%;height:170px}', '')

# Embed the cat directly so the live page has no image fetch dependency.
b64 = Path('assets/rotund-operator.webp.b64').read_text(encoding='utf-8').strip()
s = s.replace('src="assets/rotund-operator.webp"', 'src="data:image/webp;base64,' + b64 + '"')

# Faster, heavier dark-pentatonic pursuit engine.
s = s.replace('const bpm=116', 'const bpm=148').replace('const bpm = 116', 'const bpm = 148').replace('const bpm = 132', 'const bpm = 148')
s = re.sub(r'const arp\s*=\s*\[[^\]]+\];', 'const arp = [62,74,62,69,77,67,74,62,65,77,69,62,72,67,79,69];', s, count=1)
s = re.sub(r'const bass\s*=\s*\[[^\]]+\];', 'const bass = [38,38,36,31];', s, count=1)
s = s.replace('master.gain.value=.34', 'master.gain.value=.38').replace('master.gain.value = 0.34', 'master.gain.value = 0.38')
s = s.replace('musicBus.gain.value=.32', 'musicBus.gain.value=.37').replace('musicBus.gain.value = 0.32', 'musicBus.gain.value = 0.37')
s = s.replace('dryBus.gain.value=.78', 'dryBus.gain.value=.84').replace('dryBus.gain.value = 0.78', 'dryBus.gain.value = 0.84')

bass_fn = r'''function bassNote(note, at, dur = .24) {
    const o1=ctx.createOscillator(), o2=ctx.createOscillator(), sub1=ctx.createOscillator(), sub2=ctx.createOscillator();
    const f=ctx.createBiquadFilter(), subF1=ctx.createBiquadFilter(), subF2=ctx.createBiquadFilter();
    const g=envGain(at,.003,.075,dur,.19), subG1=envGain(at,.002,.09,dur+.055,.15), subG2=envGain(at,.002,.08,dur+.04,.085);
    const p1=ctx.createStereoPanner(), p2=ctx.createStereoPanner(); p1.pan.value=-.06; p2.pan.value=.06;
    o1.type='sawtooth'; o2.type='square'; sub1.type='sine'; sub2.type='triangle';
    o1.frequency.value=midi(note); o2.frequency.value=midi(note-12); o2.detune.value=-5;
    sub1.frequency.value=midi(note-12); sub2.frequency.value=midi(note-12); sub2.detune.value=3;
    f.type='lowpass'; f.frequency.setValueAtTime(610,at); f.Q.value=6.4;
    subF1.type='lowpass'; subF1.frequency.setValueAtTime(118,at); subF1.Q.value=.8;
    subF2.type='lowpass'; subF2.frequency.setValueAtTime(165,at); subF2.Q.value=.9;
    o1.connect(f); o2.connect(f); f.connect(g).connect(master);
    sub1.connect(subF1).connect(subG1).connect(p1).connect(master);
    sub2.connect(subF2).connect(subG2).connect(p2).connect(master);
    o1.start(at);o2.start(at);sub1.start(at);sub2.start(at);
    o1.stop(at+dur+.18);o2.stop(at+dur+.18);sub1.stop(at+dur+.25);sub2.stop(at+dur+.22);
  }

  function driveCurve(amount=38) {
    const n=1024,curve=new Float32Array(n),k=amount;
    for(let i=0;i<n;i++){const x=i*2/n-1;curve[i]=(1+k)*x/(1+k*Math.abs(x));}
    return curve;
  }

  function arpNote'''
s = re.sub(r'function bassNote\(note, at, dur = \.24\) \{.*?\n  \}\n\n  function arpNote', bass_fn, s, count=1, flags=re.S)

arp_fn = r'''function arpNote(note, at, accent = false) {
    const mix=ctx.createGain(),f=ctx.createBiquadFilter(),drive=ctx.createWaveShaper(),clean=ctx.createGain(),dirty=ctx.createGain();
    const g=envGain(at,.001,.004,accent?.085:.068,accent?.066:.052);
    f.type='lowpass'; f.frequency.setValueAtTime(accent?3900:2850,at); f.frequency.exponentialRampToValueAtTime(accent?1500:1100,at+.09); f.Q.value=accent?7.2:5.4;
    drive.curve=driveCurve(accent?58:42); drive.oversample='2x'; clean.gain.value=.56; dirty.gain.value=.48;
    const det=[-19,-7,7,19],pans=[-.72,-.24,.24,.72],types=['sawtooth','sawtooth','square','sawtooth'];
    det.forEach((d,i)=>{const o=ctx.createOscillator(),pan=ctx.createStereoPanner();o.type=types[i];o.frequency.value=midi(note);o.detune.value=d+(step%2?2:-2);pan.pan.value=pans[i];o.connect(pan).connect(mix);o.start(at);o.stop(at+.14);});
    mix.connect(f); f.connect(clean).connect(g); f.connect(drive).connect(dirty).connect(g); g.connect(musicBus);
    const send=ctx.createGain();send.gain.value=accent?.66:.48;g.connect(send).connect(delay);
    const verb=ctx.createGain();verb.gain.value=accent?.13:.075;g.connect(verb).connect(reverb);
  }

  function rollingNote(note, at, direction=1) {
    const root=midi(note),det=[-12,-4,4,12],pans=[-.82,-.34,.34,.82];
    det.forEach((d,i)=>{const o=ctx.createOscillator(),p=ctx.createStereoPanner(),f=ctx.createBiquadFilter(),g=envGain(at,.001,.018,.11,.018);o.type='sawtooth';o.frequency.value=root;o.detune.value=d;p.pan.value=pans[i]*direction;f.type='bandpass';f.frequency.value=1300+i*390+(step%4)*180;f.Q.value=4.5;o.connect(f).connect(g).connect(p).connect(musicBus);o.start(at);o.stop(at+.16);});
  }

  function padChord'''
s = re.sub(r'function arpNote\(note, at, accent = false\) \{.*?\n  \}\n\n  function padChord', arp_fn, s, count=1, flags=re.S)

sched_fn = r'''function schedule(s, at) {
    if (!audioOn) return;
    const beat16=s%16;
    if(beat16%4===0)kick(at);
    if(beat16===4||beat16===12)snare(at);
    if(beat16%2===0)hat(at,beat16===14);
    arpNote(arp[beat16],at,[0,1,4,6,8,10,12,14,15].includes(beat16));
    rollingNote(pent[(beat16+Math.floor(s/16))%pent.length]+(beat16%4===3?12:0),at+sixteenth*.18,beat16%2?-1:1);
    if([3,7,11,15].includes(beat16))arpNote([50,55,53,57][Math.floor(beat16/4)],at+sixteenth*.36,true);
    const bassRoot=bass[Math.floor((s/16)%4)];
    if(beat16%2===0)bassNote(bassRoot+(beat16%4===2?12:0),at,beat16%4===2?.12:.205);
    if([3,7,11,15].includes(beat16))bassNote(bassRoot,at+sixteenth*.14,.085);
    if(beat16===0)padChord(padVoicings[Math.floor((s/16)%4)],at);
    if(Math.floor(s/16)%2===1){if(beat16===10)tom(at,176,.12);if(beat16===13)tom(at,142,.135);if(beat16===15)tom(at,108,.155);}
  }

  function scheduler'''
s = re.sub(r'function schedule\(s, at\) \{.*?\n  \}\n\n  function scheduler', sched_fn, s, count=1, flags=re.S)

s = s.replace("'KERNEL // ON'", "'SFX // ON'").replace("'KERNEL // OFF'", "'SFX // OFF'")

# Sanity checks before publishing.
assert 'THREAT RADAR' not in s and '.radar{' not in s
assert 'src="data:image/webp;base64,' in s
assert 'const bpm = 148' in s or 'const bpm=148' in s
assert 'rollingNote' in s and 'driveCurve' in s
assert 'SFX // ON' in s and 'KERNEL //' not in s

p.write_text(s, encoding='utf-8')
Path('live.html').write_text(s, encoding='utf-8')

js = re.search(r'<script>(.*)</script>', s, re.S)
if js:
    Path('/tmp/landing.js').write_text(js.group(1), encoding='utf-8')
    subprocess.run(['node','--check','/tmp/landing.js'], check=True)
