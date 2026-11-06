"""Local COLMAP/OpenMVS pilot launcher; no downloads or project writes.

Run from an extracted SolarCheck source ZIP with the existing offline Python.
Without arguments the explicit local selectors open; CLI supports later job use.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import queue
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcm_solarcheck.services.colmap_openmvs_pilot import (  # noqa: E402
    PilotCancelled, PilotError, RgbPilotConfig, input_signature, project_choices,
    read_rgb_project, run_rgb_pilot,
)


def execute(database, project, config, cancel, progress):
    frames = read_rgb_project(database, project)
    expected = input_signature(frames)
    return run_rgb_pilot(frames, config, should_cancel=cancel, on_progress=progress,
                         inputs_unchanged=lambda: input_signature(read_rgb_project(database, project)) == expected)


def window(*, use_gpu=True, target_crs=None, stage_hours=24, resume_job=None):
    import tkinter as tk
    from tkinter import filedialog, ttk

    root = tk.Tk()
    root.title('SolarCheck – lokaler RGB-Pilot mit COLMAP/OpenMVS')
    root.geometry('900x670')
    values = {key: tk.StringVar() for key in ('database', 'colmap', 'openmvs', 'output')}
    events, cancel = queue.Queue(), threading.Event()
    state = {'running': False, 'closing': False, 'projects': (), 'result': None}
    status = tk.StringVar(value='Bereit. Es wird erst nach Projektwahl und Klick auf Pilot starten gerechnet.')
    gpu = tk.BooleanVar(value=use_gpu)
    crs = tk.StringVar(value=target_crs or '')
    hours = tk.StringVar(value=f'{stage_hours:g}')
    resume = tk.StringVar(value=str(resume_job) if resume_job else '')
    controls = []
    ttk.Label(root, text='Verwendet alle bereits importierten RGB-JPGs des gewaehlten Projekts.\n'
              'Fortsetzung uebernimmt Merkmale/Paarergebnisse aus dem gewaehlten alten Job.\n'
              'Projektdatei/Originale bleiben unveraendert. Thermal und Fachfreigabe folgen spaeter.',
              wraplength=800).pack(anchor='w', padx=16, pady=12)

    def choose(key):
        if key == 'database':
            selected = filedialog.askopenfilename(title='Vorhandene SolarCheck-Projektdatei',
                       filetypes=[('SolarCheck SQLite', '*.sqlite3 *.sqlite *.db'), ('Alle Dateien', '*')])
            if selected:
                try:
                    choices = project_choices(selected)
                except Exception:
                    status.set('Projektdatei konnte nicht nur lesend geoeffnet werden.')
                    return
                state['projects'] = choices
                projects['values'] = [name + ' · ' + key[-8:] for key, name in choices]
                projects.set('Bitte Projekt auswaehlen')
        elif key == 'colmap':
            selected = filedialog.askopenfilename(title='COLMAP 3.12.6: bin/colmap.exe',
                                                  filetypes=[('COLMAP', 'colmap.exe'), ('Alle Dateien', '*')])
        else:
            selected = filedialog.askdirectory(title='OpenMVS-Programmordner' if key == 'openmvs' else 'Privater Ausgabeordner')
        if selected:
            values[key].set(selected)

    for key, label in (('database', 'Vorhandene Projektdatei'), ('colmap', 'COLMAP 3.12.6: colmap.exe'),
                       ('openmvs', 'OpenMVS 2.4.0: Programmordner'), ('output', 'Privater Ausgabeordner ausserhalb Originalen/Git')):
        row = ttk.Frame(root)
        row.pack(fill='x', padx=16, pady=4)
        ttk.Label(row, text=label, width=47).pack(side='left')
        entry = ttk.Entry(row, textvariable=values[key], state='readonly')
        entry.pack(side='left', fill='x', expand=True)
        button = ttk.Button(row, text='Auswaehlen', command=lambda k=key: choose(k))
        button.pack(side='left', padx=4)
        controls.append(button)
    resume_row = ttk.Frame(root)
    resume_row.pack(fill='x', padx=16, pady=4)
    ttk.Label(resume_row, text='Bildabgleich fortsetzen: alter RGB-Job (optional)', width=47).pack(side='left')
    resume_entry = ttk.Entry(resume_row, textvariable=resume)
    resume_entry.pack(side='left', fill='x', expand=True)
    def choose_resume():
        selected = filedialog.askdirectory(title='Gestoppter RGB-Job mit job.json und features.db')
        if selected:
            resume.set(selected)
    resume_pick = ttk.Button(resume_row, text='Job waehlen', command=choose_resume)
    resume_pick.pack(side='left', padx=4)
    controls.extend((resume_entry, resume_pick))
    time_row = ttk.Frame(root)
    time_row.pack(fill='x', padx=16, pady=4)
    ttk.Label(time_row, text='Zeitlimit je Rechenstufe (Stunden, max. 72)', width=47).pack(side='left')
    time_entry = ttk.Spinbox(time_row, from_=1, to=72, textvariable=hours, width=8)
    time_entry.pack(side='left')
    controls.append(time_entry)
    projects = ttk.Combobox(root, state='readonly')
    projects.pack(fill='x', padx=16, pady=8)
    projects.set('Zuerst vorhandene Projektdatei waehlen')
    controls.append(projects)
    crs_row = ttk.Frame(root)
    crs_row.pack(fill='x', padx=16, pady=4)
    ttk.Label(crs_row, text='Ziel-CRS optional, leer: automatische WGS84-UTM-Zone', width=58).pack(side='left')
    crs_entry = ttk.Entry(crs_row, textvariable=crs)
    crs_entry.pack(side='left', fill='x', expand=True)
    controls.append(crs_entry)
    check = ttk.Checkbutton(root, text='NVIDIA fuer COLMAP-Merkmale/Bildabgleich verwenden; OpenMVS rechnet auf CPU', variable=gpu)
    check.pack(anchor='w', padx=16, pady=5)
    controls.append(check)
    ttk.Label(root, textvariable=status, wraplength=800).pack(anchor='w', padx=16, pady=12)
    buttons = ttk.Frame(root)
    buttons.pack(fill='x', padx=16, pady=8)

    def worker(database, project, config):
        try:
            result = execute(database, project, config, cancel.is_set, lambda text: events.put(('progress', text)))
            events.put(('success', result))
        except PilotCancelled:
            events.put(('error', 'Pilot abgebrochen; private Arbeitsdateien bleiben erhalten.'))
        except PilotError as error:
            events.put(('error', str(error)))
        except Exception:
            events.put(('error', 'RGB-Pilot fehlgeschlagen. Privaten Jobordner und lokale Protokolle pruefen.'))

    def start():
        if state['running']:
            return
        selected = projects.current()
        if selected < 0 or not all(value.get() for value in values.values()):
            status.set('Projektdatei, Projekt, beide Werkzeugpfade und Ausgabeordner auswaehlen.')
            return
        try:
            duration = float(hours.get())
            if not math.isfinite(duration) or not 0 < duration <= 72:
                raise ValueError
        except ValueError:
            status.set('Zeitlimit als positive Stundenzahl bis maximal 72 angeben.')
            return
        state['running'], state['result'] = True, None
        cancel.clear()
        open_output['state'] = 'disabled'
        for control in controls:
            control['state'] = 'disabled'
        start_button['state'] = 'disabled'
        close_button['text'] = 'Abbrechen'
        config = RgbPilotConfig(Path(values['colmap'].get()), Path(values['openmvs'].get()), Path(values['output'].get()),
                                use_gpu=gpu.get(), target_crs=crs.get().strip() or None,
                                stage_timeout_seconds=duration * 3600,
                                resume_job=Path(resume.get().strip()) if resume.get().strip() else None)
        threading.Thread(target=worker, args=(values['database'].get(), state['projects'][selected][0], config), daemon=False).start()

    def close():
        if state['running']:
            state['closing'] = True
            cancel.set()
            status.set('Abbruch wird abgeschlossen; laufender Prozessbaum wird beendet.')
        else:
            root.destroy()

    def poll():
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == 'progress':
                    if not state['closing']:
                        status.set(payload)
                    continue
                state['running'] = False
                if state['closing']:
                    root.destroy()
                    return
                for control in controls:
                    control['state'] = 'readonly' if control is projects else 'normal'
                start_button['state'], close_button['text'] = 'normal', 'Schliessen'
                if kind == 'success':
                    state['result'] = payload
                    status.set('Erstellt: ' + str(payload.rgb_geotiff) + '\nRGB ungeprueft; kein Thermal und keine Fachfreigabe.')
                    open_output['state'] = 'normal'
                else:
                    status.set(payload)
        except queue.Empty:
            pass
        root.after(150, poll)

    def show_output():
        if state['result'] is not None:
            import os
            os.startfile(state['result'].workspace)

    start_button = ttk.Button(buttons, text='Pilot starten', command=start)
    start_button.pack(side='left')
    open_output = ttk.Button(buttons, text='Ausgabeordner oeffnen', state='disabled', command=show_output)
    open_output.pack(side='left', padx=8)
    close_button = ttk.Button(buttons, text='Schliessen', command=close)
    close_button.pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(150, poll)
    root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('database', 'project', 'colmap', 'openmvs', 'output'):
        parser.add_argument('--' + name)
    parser.add_argument('--cpu', action='store_true')
    parser.add_argument('--target-crs')
    parser.add_argument('--stage-hours', type=float, default=24,
                        help='Zeitlimit je Rechenstufe in Stunden (positiv, maximal 72; Standard 24).')
    parser.add_argument('--resume-job', help='Expliziter alter RGB-Job, der beim Bildabgleich gestoppt wurde.')
    args = parser.parse_args(argv)
    if not math.isfinite(args.stage_hours) or not 0 < args.stage_hours <= 72:
        parser.error('Zeitlimit als positive Stundenzahl bis maximal 72 angeben.')
    if not any((args.database, args.project, args.colmap, args.openmvs, args.output)):
        window(use_gpu=not args.cpu, target_crs=args.target_crs,
               stage_hours=args.stage_hours, resume_job=args.resume_job)
        return 0
    if not all((args.database, args.project, args.colmap, args.openmvs, args.output)):
        parser.error('Alle fuenf lokalen Pfade/Projektargumente angeben oder ohne Argumente starten.')
    try:
        result = execute(args.database, args.project,
                         RgbPilotConfig(Path(args.colmap), Path(args.openmvs), Path(args.output),
                                        use_gpu=not args.cpu, target_crs=args.target_crs,
                                        stage_timeout_seconds=args.stage_hours * 3600,
                                        resume_job=Path(args.resume_job) if args.resume_job else None),
                         lambda: False, print)
        print('Erstellt:', result.rgb_geotiff)
        print('RGB ungeprueft; keine Thermal-/Fachfreigabe.')
        return 0
    except (PilotCancelled, KeyboardInterrupt):
        print('RGB-Pilot abgebrochen.')
        return 130
    except PilotError as error:
        print(str(error))
        return 2
    except Exception:
        print('RGB-Pilot fehlgeschlagen; private lokale Jobprotokolle pruefen.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
