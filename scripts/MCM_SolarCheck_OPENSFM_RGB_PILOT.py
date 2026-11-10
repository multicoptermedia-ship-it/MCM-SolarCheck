"""Explicit local OpenSfM RGB pilot using the existing offline app Python."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mcm_solarcheck.services.colmap_openmvs_pilot import (  # noqa: E402
    PilotCancelled, PilotError, input_signature, project_choices, read_rgb_project,
)
from mcm_solarcheck.services.opensfm_rgb_pilot import (  # noqa: E402
    LABELS, STAGES, OpenSfMPilotConfig, local_run_label, read_opensfm_metrics, run_opensfm_rgb_pilot,
)

CONDA = r'E:\Tools\Miniforge3\Scripts\conda.exe'
ENVIRONMENT = r'E:\SolarCheck-OpenSfM\env'


def execute(database, project, conda, environment, output, cancel, progress, workspace):
    prefix = Path(environment)
    python = prefix / ('python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        raise PilotError('Vorhandene OpenSfM-Umgebung nicht gefunden; keine Neuinstallation starten.')
    frames = read_rgb_project(database, project)
    signature = input_signature(frames)
    config = OpenSfMPilotConfig(
        (str(conda), 'run', '--no-capture-output', '--prefix', str(prefix), 'python'),
        Path(__file__).with_name('MCM_SolarCheck_OPENSFM_STAGE.py'), Path(output),
        project_label=dict(project_choices(database)).get(project, 'Projekt'))
    return run_opensfm_rgb_pilot(frames, config, should_cancel=cancel, on_progress=progress,
        on_workspace=workspace,
        inputs_unchanged=lambda: input_signature(read_rgb_project(database, project)) == signature)


def window(*, conda=CONDA, environment=ENVIRONMENT):
    import tkinter as tk
    from tkinter import filedialog, ttk
    root = tk.Tk()
    root.title('SolarCheck – RGB-Orthofoto mit OpenSfM testen')
    root.geometry('1000x650')
    values = {key: tk.StringVar(value=value) for key, value in (
        ('database', ''), ('conda', str(conda)), ('environment', str(environment)), ('output', ''))}
    events, cancel = queue.Queue(), threading.Event()
    state = {'running': False, 'closing': False, 'projects': (), 'workspace': None, 'tick': None}
    status = tk.StringVar(value='Projektdatei und Projekt bewusst auswaehlen; gerechnet wird erst nach dem Startklick.')
    clock = tk.StringVar(value='')
    run_info = tk.StringVar(value='Noch kein OpenSfM-Lauf ausgewaehlt.')
    copy_note = tk.StringVar(value='')
    controls = []
    ttk.Label(root, text='Erster Bildlauf: ein kleines, vollstaendiges RGB-Projekt mit 3 bis 300 Bildern.\n'
        'Alle importierten RGB-JPGs werden als private Arbeitskopien verarbeitet. '
        'Maximal 60 Minuten je Stufe, drei Stunden insgesamt.\n'
        'RGB-Ergebnis zur Sichtpruefung; Thermal und fachliche Abnahme folgen danach.',
        wraplength=950).pack(anchor='w', padx=16, pady=12)

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
        elif key == 'conda':
            selected = filedialog.askopenfilename(title='Vorhandene conda.exe',
                filetypes=[('Conda', 'conda.exe'), ('Alle Dateien', '*')])
        else:
            selected = filedialog.askdirectory(title='Vorhandene OpenSfM-Umgebung' if key == 'environment'
                                               else 'Privater Ausgabeordner ausserhalb Originalen/Git')
        if selected:
            values[key].set(selected)

    for key, label in (('database', 'Vorhandene Projektdatei'), ('conda', 'Vorhandenes Miniforge'),
                       ('environment', 'Vorhandene OpenSfM-Umgebung'), ('output', 'Privater Ausgabeordner')):
        row = ttk.Frame(root)
        row.pack(fill='x', padx=16, pady=5)
        ttk.Label(row, text=label, width=35).pack(side='left')
        ttk.Entry(row, textvariable=values[key], state='readonly').pack(side='left', fill='x', expand=True)
        button = ttk.Button(row, text='Auswaehlen', command=lambda k=key: choose(k))
        button.pack(side='left', padx=4)
        controls.append(button)
    projects = ttk.Combobox(root, state='readonly')
    projects.pack(fill='x', padx=16, pady=8)
    projects.set('Zuerst vorhandene Projektdatei waehlen')
    controls.append(projects)
    ttk.Label(root, textvariable=run_info, wraplength=950).pack(anchor='w', padx=16, pady=5)
    ttk.Label(root, textvariable=status, wraplength=950).pack(anchor='w', padx=16, pady=12)
    ttk.Label(root, textvariable=clock).pack(anchor='w', padx=16)
    ttk.Label(root, textvariable=copy_note).pack(anchor='w', padx=16)
    buttons = ttk.Frame(root)
    buttons.pack(fill='x', padx=16, pady=12)

    def work(args):
        try:
            result = execute(*args, cancel.is_set,
                lambda text: events.put(('progress', text)), lambda path: events.put(('workspace', path)))
            events.put(('success', result))
        except PilotCancelled:
            events.put(('error', 'Abgebrochen; private Arbeitsdateien und Laufzeiten bleiben erhalten.'))
        except PilotError as error:
            events.put(('error', str(error)))
        except Exception:
            events.put(('error', 'Pilot fehlgeschlagen; neuen privaten Jobordner lokal pruefen.'))

    def start():
        if state['running']:
            return
        index = projects.current()
        if index < 0 or not all(value.get() for value in values.values()):
            status.set('Projektdatei, Projekt und privaten Ausgabeordner auswaehlen.')
            return
        state.update(running=True, workspace=None, tick=time.monotonic())
        run_info.set('Neuer OpenSfM-Lauf wird vorbereitet.')
        copy_note.set('')
        cancel.clear()
        for control in controls:
            control['state'] = 'disabled'
        start_button['state'], cancel_button['state'], open_button['state'] = 'disabled', 'normal', 'disabled'
        copy_button['state'] = 'disabled'
        args = (values['database'].get(), state['projects'][index][0], values['conda'].get(),
                values['environment'].get(), values['output'].get())
        threading.Thread(target=work, args=(args,), daemon=False).start()

    def abort():
        cancel.set()
        status.set('Abbruch wird abgeschlossen; eigener Prozessbaum wird beendet.')

    def close():
        if state['running']:
            state['closing'] = True
            abort()
        else:
            root.destroy()

    def poll():
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == 'workspace':
                    state['workspace'] = payload
                    try:
                        run_info.set(local_run_label(payload))
                    except (OSError, PilotError):
                        run_info.set('OpenSfM RGB · Ordner: ' + payload.name)
                    open_button['state'] = 'normal'
                    continue
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
                start_button['state'], cancel_button['state'] = 'normal', 'disabled'
                copy_button['state'] = 'normal' if state['workspace'] is not None else 'disabled'
                if kind == 'success':
                    status.set('RGB-Ergebnis zur Sichtpruefung erstellt: ' + str(payload.rgb_geotiff))
                else:
                    status.set(payload)
        except queue.Empty:
            pass
        if state['running']:
            clock.set(f'Laufzeit dieses Piloten: {int(time.monotonic() - state["tick"]):d} Sekunden')
        root.after(150, poll)

    def show_output():
        if state['workspace'] is not None:
            os.startfile(state['workspace'])

    def copy_metrics():
        if state['workspace'] is None:
            return
        try:
            text = json.dumps(read_opensfm_metrics(state['workspace']), indent=2, ensure_ascii=False)
            root.clipboard_clear()
            root.clipboard_append(text)
            copy_note.set('Kennzahlen dieses OpenSfM-Laufs kopiert; hier als Text einfuegen.')
        except (OSError, PilotError):
            copy_note.set('Kennzahlen noch nicht lesbar oder kein OpenSfM-Bericht. Keine Rohprotokolle kopieren.')

    def load_run():
        if state['running']:
            return
        chosen = filedialog.askdirectory(title='Gespeicherten OpenSfM-Laufordner mit job.json auswaehlen',
            initialdir=values['output'].get() or r'F:\Auswertung1')
        if not chosen:
            return
        try:
            report = read_opensfm_metrics(chosen)
            label = local_run_label(chosen)
        except (OSError, PilotError):
            copy_note.set('Kein gueltiger OpenSfM-Lauf. COLMAP-Ordner werden nicht uebernommen.')
            return
        state['workspace'] = Path(chosen)
        run_info.set(label)
        copy_note.set('Gespeicherter Lauf geladen; es wird nichts neu berechnet.')
        states = {'running': 'laeuft', 'finished': 'abgeschlossen',
                  'failed': 'fehlgeschlagen', 'cancelled': 'abgebrochen'}
        last = report['steps'][-1]['stage'] if report['steps'] else None
        stage_label = ' · ' + dict(zip(STAGES, LABELS))[last] if last else ''
        status.set('Gespeicherter OpenSfM-Lauf: ' + states[report['status']] + stage_label)
        clock.set(f'Gespeicherte Gesamtlaufzeit: {report.get("elapsed_seconds", 0):.0f} Sekunden')
        open_button['state'] = 'normal'
        copy_button['state'] = 'normal' if report['status'] != 'running' else 'disabled'

    start_button = ttk.Button(buttons, text='RGB-Pilot starten', command=start)
    start_button.pack(side='left')
    cancel_button = ttk.Button(buttons, text='Abbrechen', state='disabled', command=abort)
    cancel_button.pack(side='left', padx=6)
    open_button = ttk.Button(buttons, text='Ausgabeordner oeffnen', state='disabled', command=show_output)
    open_button.pack(side='left', padx=6)
    copy_button = ttk.Button(buttons, text='Kennzahlen kopieren', state='disabled', command=copy_metrics)
    copy_button.pack(side='left', padx=6)
    load_button = ttk.Button(buttons, text='Lauf laden', command=load_run)
    load_button.pack(side='left', padx=6)
    controls.append(load_button)
    ttk.Button(buttons, text='Schliessen', command=close).pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(150, poll)
    root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('database', 'project', 'output'):
        parser.add_argument('--' + key)
    parser.add_argument('--conda', default=CONDA)
    parser.add_argument('--environment', default=ENVIRONMENT)
    args = parser.parse_args(argv)
    if not any((args.database, args.project, args.output)):
        window(conda=args.conda, environment=args.environment)
        return 0
    if not all((args.database, args.project, args.output)):
        parser.error('Projektdatei, Projekt und Ausgabe zusammen angeben oder ohne Argumente starten.')
    try:
        result = execute(args.database, args.project, args.conda, args.environment, args.output,
                         lambda: False, print, lambda path: None)
        print('RGB-Ergebnis zur Sichtpruefung:', result.rgb_geotiff)
        return 0
    except (PilotCancelled, KeyboardInterrupt):
        print('OpenSfM-Pilot abgebrochen.')
        return 130
    except PilotError as error:
        print(str(error))
        return 2
    except Exception:
        print('OpenSfM-Pilot fehlgeschlagen; privaten Jobordner lokal pruefen.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
