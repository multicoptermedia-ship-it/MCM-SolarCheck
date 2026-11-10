"""Explicit local OpenSfM RGB pilot using the existing offline app Python."""
from __future__ import annotations

import argparse
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
    OpenSfMPilotConfig, run_opensfm_rgb_pilot,
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
        Path(__file__).with_name('MCM_SolarCheck_OPENSFM_STAGE.py'), Path(output))
    return run_opensfm_rgb_pilot(frames, config, should_cancel=cancel, on_progress=progress,
        on_workspace=workspace,
        inputs_unchanged=lambda: input_signature(read_rgb_project(database, project)) == signature)


def window(*, conda=CONDA, environment=ENVIRONMENT):
    import tkinter as tk
    from tkinter import filedialog, ttk
    root = tk.Tk()
    root.title('SolarCheck – RGB-Orthofoto mit OpenSfM testen')
    root.geometry('1000x570')
    values = {key: tk.StringVar(value=value) for key, value in (
        ('database', ''), ('conda', str(conda)), ('environment', str(environment)), ('output', ''))}
    events, cancel = queue.Queue(), threading.Event()
    state = {'running': False, 'closing': False, 'projects': (), 'workspace': None, 'tick': None}
    status = tk.StringVar(value='Projektdatei und Projekt bewusst auswaehlen; gerechnet wird erst nach dem Startklick.')
    clock = tk.StringVar(value='')
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
    ttk.Label(root, textvariable=status, wraplength=950).pack(anchor='w', padx=16, pady=12)
    ttk.Label(root, textvariable=clock).pack(anchor='w', padx=16)
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
        cancel.clear()
        for control in controls:
            control['state'] = 'disabled'
        start_button['state'], cancel_button['state'], open_button['state'] = 'disabled', 'normal', 'disabled'
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

    start_button = ttk.Button(buttons, text='RGB-Pilot starten', command=start)
    start_button.pack(side='left')
    cancel_button = ttk.Button(buttons, text='Abbrechen', state='disabled', command=abort)
    cancel_button.pack(side='left', padx=6)
    open_button = ttk.Button(buttons, text='Ausgabeordner oeffnen', state='disabled', command=show_output)
    open_button.pack(side='left', padx=6)
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
