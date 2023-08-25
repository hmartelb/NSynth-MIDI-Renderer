# NSynth-MIDI-Renderer for massive MIDI dataset 

This project is slightly modified from original work. It is designed to render large midifile datasets.
For a given MIDI sequence, it goes through a process of finding and assigning candidates to lock in a single preset from the beginning to the end of the sequence. 
If it fails to find one because the combination of instrument, pitch, and velocity is unique, it will randomly use a preset for every note. 
When tested with a 130,000 MIDI dataset, only 95 MIDI sequences were randomized, with a probability of 0.0007%.

* Original Project: https://github.com/hmartelb/NSynth-MIDI-Renderer

<p align="center">
<a href="docs/NoteSynthesizer_diagram.png"><img src="docs/NoteSynthesizer_diagram.png" width="650" height="450"/></a>
</p>

# Quick start
Clone this repository to your system.
```bash
$ git clone https://github.com/spear011/NSynth-MIDI-Renderer.git
```

To start synthesizing audios, you need to download the NSynth dataset and MIDI dataset you want.

* The NSynth Dataset, “A large-scale and high-quality dataset of annotated musical notes.” https://magenta.tensorflow.org/datasets/nsynth

# How to use it 
For the general use case, 3 parameters must be specified:
1)	The path to the NSynth Dataset (audios directory)
2)	csv file that containing midi file id and instrument information
3)	The MIDI file list (*.mid, *.midi)
4)	The output dir path 

# Import the NoteSynthesizer Class into a Python script
It is also possible to use the NoteSynthesizer Class in a Python script to have custom functionality. Here is a generic way to import and use it:

```python
from NoteSynthesizer import NoteSynthesizer

# Initialize variables here
# ...

# Create the NoteSynthesizer instance
synth = NoteSynthesizer(path_to_nsynth, path_to_midi_csv, output_dir, sr, velocities, preload)  

# Generate the audio for a given MIDI sequence
output_dict = synth.render_sequence(sequence_path, instrument, transpose, playback_speed, duration_scale, write_wav=True)

# Or you can use it with multiprocessing
import billiard as mp
from tqdm.auto import tqdm

cnt_cpu = mp.cpu_count() - 2
pool = mp.Pool(cnt_cpu)

output_dict = {'id': [], 'instrument': [], 'preset': [], 'source': []}
total = len(selected_file_list)

with tqdm(total=total) as pbar:
    for dict_object in tqdm(pool.imap_unordered(synth.render_sequence, selected_file_list)):
        for k, v in dict_object.items():
            output_dict[k].append(v)
        pbar.update()

```

# Examples
The files in the /output folder have been generated using different instruments, with sr=44100, playback_speed=1 and duration_scale=4, leaving the rest of optional parameters as default. The files are named using midi file ID.
```bash
<midi_name>.wav
```
The output dictionary looks like this
'''bash
output_dict = {'id': ['midifile01', 'midifile02', 'midifile03'], 'instrument': ['keyboard', 'guitar', 'guitar'] ,'preset': ['030', '002', 'random'], 'source': [1, 0, 'random']}
'''

The result of this dictionary can be used to track which presets and sources were selected for the MIDI file. 
Information about the presets of audio sources that were subsequently used can be matched with the nsynth dataset.

# Citation
If you use this code in your research, please cite it as below:
```
@software{Martel_NSynth-MIDI-Renderer_2019,
    author = {Martel, Héctor},
    month = {8},
    title = {{NSynth-MIDI-Renderer: Sample based concatenative synthesizer for the NSynth dataset.}},
    url = {https://github.com/hmartelb/NSynth-MIDI-Renderer},
    version = {1.0.0},
    year = {2019}
}
```

# Licence

```
MIT License
Copyright (c) 2019 Héctor Martel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
