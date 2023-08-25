import argparse
import os
import sys

import numpy as np
import pandas as pd
import random

import pretty_midi
import librosa
from scipy.io.wavfile import write as write_wav

class NoteSynthesizer():
    def __init__(self, dataset_path, sr=44100, transpose=0, attack_in_ms=5, release_in_ms=100, leg_stac=.9, velocities=np.arange(0,128), preset=0, preload=True):
        self.dataset_path = dataset_path
        self.nsynth_df = self.make_dataframes(self.dataset_path)
        self.minpitch, self.maxpitch = self._min_max_pitch(self.nsynth_df)
        self.sr = sr
        self.transpose = transpose
        self.release_in_ms = release_in_ms
        self.release_in_sample = int(self.release_in_ms * 0.001 * self.sr)
        self.attack_in_ms = attack_in_ms
        self.attack_in_sample = int(self.attack_in_ms * 0.001 * self.sr)
        self.leg_stac = leg_stac
        self.velocities = velocities
        self.preset = preset

        self.preload = preload

        # make dataframe from json
    def make_dataframes(self, dataset_path):
        json_path = os.path.join(dataset_path, 'examples.json')
        df = pd.read_json(json_path).T
        df['preset'] = df['instrument_str'].apply(lambda x: x.split('_')[-1])
        return df
    
        # get min and max pitch for each instrument
    def _min_max_pitch(self, nsynth_df):
        min_pitch_inst = nsynth_df.groupby('instrument_family_str').min().pitch.index.tolist()
        min_pitch_value = nsynth_df.groupby('instrument_family_str').min().pitch.values.tolist()
        minpitch = {inst : value for inst, value in zip(min_pitch_inst, min_pitch_value)}

        max_pitch_inst = nsynth_df.groupby('instrument_family_str').max().pitch.index.tolist()
        max_pitch_value = nsynth_df.groupby('instrument_family_str').max().pitch.values.tolist()
        maxpitch = {inst : value for inst, value in zip(max_pitch_inst, max_pitch_value)}
        return minpitch, maxpitch

    def pop_candidates(self, candidates, currnet_candidates):
        for i in candidates.copy().keys():
            if (i in currnet_candidates) and (candidates[i] == currnet_candidates[i]):
                continue
            else:
                candidates.pop(i)
        return candidates
    
        
    def _find_candidates(self, seq, current_inst):
        '''
        find preset, instrument source candidates for each note in the sequence

        Input:
            seq: list of tuples (note, velocity, start_time, end_time)
            current_inst: seq's instrument
        
        Output:
            candidates: dict of candidates {preset : instrument source}

        '''

        min_p = self.minpitch[current_inst]
        max_p = self.maxpitch[current_inst]
        nsynth_df = self.nsynth_df

        candidates = {p : s for p, s in zip(nsynth_df[(nsynth_df['instrument_family_str'] == current_inst)]['preset'].values.tolist() ,
                                                nsynth_df[(nsynth_df['instrument_family_str'] == current_inst)]['instrument_source'].values.tolist())}

        for n, v, _, _ in seq:

            if n < min_p or n > max_p:
                continue

            currnet_candidates = {p : s for p, s in zip(nsynth_df[(nsynth_df['instrument_family_str'] == current_inst) & 
                                                                (nsynth_df['pitch'] == n) &
                                                                (nsynth_df['velocity'] == v)]['preset'].values.tolist() ,

                                                        nsynth_df[(nsynth_df['instrument_family_str'] == current_inst) &
                                                                (nsynth_df['pitch'] == n) &
                                                                (nsynth_df['velocity'] == v)]['instrument_source'].values.tolist())}
            
            candidates = self.pop_candidates(candidates, currnet_candidates)

            if len(candidates) == 0:
                print('No candidates')
                return None

        return candidates   

    def _get_note_name_fixed(self, note, velocity, instrument, preset, source):

        if source == 0:
            source = 'acoustic'
        elif source == 1:
            source = 'electronic'
        elif source == 2:
            source = 'synthetic'

        return "%s_%s_%s-%s-%s.wav" % (instrument, source, str(preset).zfill(3), str(note).zfill(3), str(velocity).zfill(3))    

    def _get_note_name_random(self, note, velocity, instrument):
        nsynth_df = self.nsynth_df
        chosen_name = random.choice(nsynth_df[
                                            (nsynth_df['pitch'] == note) & 
                                            (nsynth_df['velocity'] == velocity) &
                                            (nsynth_df['instrument_family_str'] == instrument)].index)
        return f"{chosen_name}.wav"

    def _quantize(self, value, quantized_values):
        diff = np.array([np.abs(q - value) for q in quantized_values])
        return quantized_values[diff.argmin()]

    def preload_notes(self, instrument, source_type, preset=None):
        preset = preset if(preset is not None) else self.preset
        print("Preloading notes for " + instrument + "_" + source_type + "_" + str(preset).zfill(3))
        self.notes = {}
        for n in range(22, 108):
            for v in self.velocities:
                note_name = self._get_note_name(n, v, instrument, source_type, preset)
                try:
                    audio, _ = librosa.load(os.path.join(self.dataset_path, note_name), sr=self.sr)
                except:
                    audio = None
                self.notes[note_name] = audio
        print("Notes loaded")

    def _read_midi(self, filename):
        midi_data = pretty_midi.PrettyMIDI(filename)
        end_time = midi_data.get_end_time()
        
        sequence = []
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                if note.start < end_time:
                    note.velocity = self._quantize(note.velocity, self.velocities)
                    sequence.append((note.pitch, note.velocity, note.start/end_time, note.end/end_time))
        return sequence, end_time

    def _render_note(self, note_filename, duration):

        leg_stac = self.leg_stac
        attack_in_sample = self.attack_in_sample
        release_in_sample = self.release_in_sample

        note, _ = librosa.load(note_filename)
        attack_env = np.arange(attack_in_sample) / attack_in_sample
        note[:attack_in_sample] *= attack_env

        decay_ind = int(leg_stac*duration)
        envelope = np.exp(-np.arange(len(note)-decay_ind)/3000.)
        note[decay_ind:] = np.multiply(note[decay_ind:],envelope)

        release_env = (release_in_sample-np.arange(release_in_sample)) / release_in_sample

        if duration > len(note):
            note[-release_in_sample:] *= release_env
            note = np.pad(note, (0, duration - len(note)), 'constant')  
        elif duration <= len(note):
            note[duration-release_in_sample : duration] *= release_env

        return note[:duration]


    def render_sequence(self, path, instrument='guitar', playback_speed=1, duration_scale=1, transpose=0, eps=1e-9):
        
        dataset_path = self.dataset_path
        transpose = transpose if(transpose is not None) else self.transpose

        seq, end_time = self._read_midi(path)
        total_length = int(end_time * self.sr / playback_speed)
        data = np.zeros(total_length)

        candidate = self._find_candidates(seq, instrument)

        if candidate:
            preset, source = random.choice(list(candidate.items()))
        
        for note, velocity, note_start, note_end in seq:
            start_sample = int(note_start * total_length)
            end_sample = int(note_end * total_length)
            duration = end_sample - start_sample

            if note < self.minpitch[instrument] or note > self.maxpitch[instrument]:
                continue

            if(duration_scale != 1):
                duration = int(duration * duration_scale)
                end_sample = start_sample + duration

            if duration < self.release_in_sample:
                continue
            
            if candidate == None:
                note_filename = os.path.join(dataset_path, self._get_note_name_random(
                                                                        note=note, 
                                                                        velocity=velocity, 
                                                                        instrument=instrument
                                                                    ))
            else:
                note_filename = os.path.join(dataset_path, self._get_note_name_fixed(
                                                                        note=note, 
                                                                        velocity=velocity, 
                                                                        instrument=instrument,
                                                                        preset=preset,
                                                                        source=source,
                                                                    ))
            
            note = self._render_note(note_filename, duration)

            if(end_sample <= len(data) and duration == len(note)):
                data[start_sample:end_sample] += note
            elif(duration > len(note) and end_sample <= len(data)):
                data[start_sample:start_sample+len(note)] += note
            # elif(end_sample > len(data)):
            #     data[start_sample:] = note[0:len(data)-start_sample]

        data /= np.max(np.abs(data)) + eps
        return data

if __name__ == "__main__":
    NSYNTH_SAMPLE_RATE = 16000
    NSYNTH_VELOCITIES = [25, 50, 100, 127]

    ap = argparse.ArgumentParser()
    if len(sys.argv) > -1:
        ap.add_argument('--db', required=True, help="Path to the NSynth audios folder. (ex: /NSynth/nsynth-train/audios)")
        ap.add_argument('--seq', required=True, help="MIDI file (.mid) to be rendered")
        ap.add_argument('--output', required=True, help="Output filename")
        ap.add_argument('--sr', required=False, default=NSYNTH_SAMPLE_RATE, help="Sample rate of the output (default: 16000, typical for professional audio: 44100, 48000)")
        ap.add_argument('--instrument', required=False, default="guitar", help="Name of the NSynth instrument. (default: 'guitar')")
        ap.add_argument('--source_type', required=False, default="acoustic", help="Source type of the NSynth instrument (default: 'acoustic')")
        ap.add_argument('--preset', required=False, default=0, help="Preset of the NSynth instrument (default: 0)")
        ap.add_argument('--transpose', required=False, default=0, help="Transpose the MIDI sequence by a number of semitones")
        ap.add_argument('--playback_speed', required=False, default=1, help="Multiply the sequence length by a scalar (default: 1")
        ap.add_argument('--duration_scale', required=False, default=1, help="Multiply the note durations by a scalar. (default: 1)")
        ap.add_argument('--preload', required=False, default=True, help="Load all notes in memory before rendering for better performance (at least 1 GB of RAM is required)")
    args = vars(ap.parse_args())

    assert os.path.isdir(args['db']), 'Dataset not found in ' + args['db']
    assert os.path.isfile(args['seq']), 'File ' + args['seq'] + ' not found.'

    synth = NoteSynthesizer(
                                args['db'], 
                                sr=NSYNTH_SAMPLE_RATE, 
                                velocities=NSYNTH_VELOCITIES, 
                                preload=args['preload']
                            )    
    if(args['preload']):
        synth.preload_notes(args['instrument'], args['source_type'], int(args['preset']))

    y, _ = synth.render_sequence(
                                    sequence=args['seq'], 
                                    instrument=args['instrument'], 
                                    source_type=args['source_type'], 
                                    preset=int(args['preset']),
                                    transpose=int(args['transpose']),
                                    playback_speed=float(args['playback_speed']),
                                    duration_scale=float(args['duration_scale'])
                                )

    if(int(args['sr']) != NSYNTH_SAMPLE_RATE):
        y = librosa.core.resample(y, NSYNTH_SAMPLE_RATE, int(args['sr']))
    
    print("Saving audio output to", args['output'])
    write_wav(args['output'], int(args['sr']), np.array(32000.*y, np.short))