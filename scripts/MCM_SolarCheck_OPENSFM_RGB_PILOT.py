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
    PilotCancelled, PilotError, input_signature, project_choices, read_rgb_project, read_thermal_project,
)
from mcm_solarcheck.services.opensfm_rgb_pilot import (  # noqa: E402
    LABELS, STAGES, OpenSfMPilotConfig, check_opensfm_depthmap_cache, local_run_label,
    run_opensfm_rgb_pilot, run_opensfm_thermal_pilot, report_modality,
)
from mcm_solarcheck.services.opensfm_dense_continuation import (  # noqa: E402
    can_continue_opensfm, read_opensfm_run_metrics, run_opensfm_dense_continuation,
)

from mcm_solarcheck.services.opensfm_sparse_bridge import (  # noqa: E402
    can_bridge, run_sparse_bridge, MARKER,
)

CONDA = r'E:\Tools\Miniforge3\Scripts\conda.exe'
ENVIRONMENT = r'E:\SolarCheck-OpenSfM\env'


def execute(database, project, conda, environment, output, cancel, progress, workspace, *, modality='rgb'):
    prefix = Path(environment)
    python = prefix / ('python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file():
        raise PilotError('Vorhandene OpenSfM-Umgebung nicht gefunden; keine Neuinstallation starten.')
    reader = read_thermal_project if modality == 'thermal' else read_rgb_project
    frames = reader(database, project)
    signature = input_signature(frames)
    config = OpenSfMPilotConfig(
        (str(conda), 'run', '--no-capture-output', '--prefix', str(prefix), 'python'),
        Path(__file__).with_name('MCM_SolarCheck_OPENSFM_STAGE.py'), Path(output),
        project_label=dict(project_choices(database)).get(project, 'Projekt'), modality=modality)
    run = run_opensfm_thermal_pilot if modality == 'thermal' else run_opensfm_rgb_pilot
    return run(frames, config, should_cancel=cancel, on_progress=progress,
        on_workspace=workspace,
        inputs_unchanged=lambda: input_signature(reader(database, project)) == signature)


def saved_config(workspace, conda, environment):
    prefix = Path(environment)
    if not (prefix / ('python.exe' if os.name == 'nt' else 'bin/python')).is_file():
        raise PilotError('Vorhandene OpenSfM-Umgebung nicht gefunden.')
    config = OpenSfMPilotConfig(
        (str(conda), 'run', '--no-capture-output', '--prefix', str(prefix), 'python'),
        Path(__file__).with_name('MCM_SolarCheck_OPENSFM_STAGE.py'), Path(workspace).parent,
        modality=report_modality(read_opensfm_run_metrics(workspace)))
    return config


def execute_cache(workspace, conda, environment, cancel):
    return check_opensfm_depthmap_cache(workspace, saved_config(workspace, conda, environment), should_cancel=cancel)


def execute_continue(workspace, conda, environment, cancel, progress):
    return run_opensfm_dense_continuation(workspace, saved_config(workspace, conda, environment),
                                          should_cancel=cancel, on_progress=progress)


def execute_bridge(workspace, conda, environment, cancel, progress, on_workspace):
    return run_sparse_bridge(workspace, saved_config(workspace, conda, environment),
        should_cancel=cancel, on_progress=progress, on_workspace=on_workspace)


def bridge_eligible(workspace, report):
    return can_bridge(report) and not (Path(workspace) / MARKER).exists()


def window(*, conda=CONDA, environment=ENVIRONMENT, modality='rgb'):
    if modality not in ('rgb', 'thermal'):
        raise PilotError('Unbekannte Bildart.')
    kind = 'THERMAL' if modality == 'thermal' else 'RGB'
    import tkinter as tk
    from tkinter import filedialog, ttk
    root = tk.Tk()
    root.title(f'SolarCheck – {kind}-Orthofoto mit OpenSfM testen')
    root.geometry('1100x730')
    values = {key: tk.StringVar(value=value) for key, value in (
        ('database', ''), ('conda', str(conda)), ('environment', str(environment)), ('output', ''))}
    events, cancel = queue.Queue(), threading.Event()
    state = {'running': False, 'closing': False, 'projects': (), 'workspace': None, 'tick': None}
    status = tk.StringVar(value='Projektdatei und Projekt bewusst auswaehlen; gerechnet wird erst nach dem Startklick.')
    clock = tk.StringVar(value='')
    run_info = tk.StringVar(value='Noch kein OpenSfM-Lauf ausgewaehlt.')
    copy_note = tk.StringVar(value='')
    controls = []
    intro = ('Thermal-Pilot: alle importierten M3T-Thermal-JPGs des gewaehlten Projekts (3 bis 300).\n'
        'RGB wird nicht erneut gerechnet. Eigene Thermal-Kameramodelle; private Arbeitskopien mit erhaltenem 16-Bit-Raster.\n'
        'Ausgabe: Thermal-Darstellung als GeoTIFF, keine Celsiusmatrix. Max. 60 Minuten je Stufe/drei Stunden insgesamt.\n'
        'Bei Zeitlimit: Lauf laden → Tiefenkarten pruefen → Tiefenkarten fortsetzen.\n'
        'Gescheiterter Kameraverbund mit grossem Hauptmodell: einmaliger Zusatzabgleich im neuen Ordner (max. drei Stunden).'
        if modality == 'thermal' else 'Erster Bildlauf: ein kleines, vollstaendiges RGB-Projekt mit 3 bis 300 Bildern.\n'
        'Alle importierten RGB-JPGs werden als private Arbeitskopien verarbeitet. '
        'Maximal 60 Minuten je Stufe, drei Stunden insgesamt.\n'
        'RGB-Ergebnis zur Sichtpruefung; Thermal und fachliche Abnahme folgen danach.\n'
        'Gespeicherten Dense-Lauf laden → Tiefenkarten pruefen: maximal zehn Minuten.\n'
        'Nach erfolgreicher Pruefung: Tiefenkarten fortsetzen (max. zwei Stunden Tiefenkarten, drei Stunden insgesamt).')
    ttk.Label(root, text=intro, wraplength=950).pack(anchor='w', padx=16, pady=12)

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
    saved_buttons = ttk.Frame(root)
    saved_buttons.pack(fill='x', padx=16, pady=6)

    def work(args):
        try:
            callbacks = (cancel.is_set, lambda text: events.put(('progress', text)),
                         lambda path: events.put(('workspace', path)))
            result = (execute(*args, *callbacks, modality='thermal') if modality == 'thermal'
                      else execute(*args, *callbacks))
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
        cache_button['state'] = 'disabled'
        continue_button['state'] = 'disabled'
        bridge_button['state'] = 'disabled'
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
                event_kind, payload = events.get_nowait()
                if event_kind == 'workspace':
                    state['workspace'] = payload
                    try:
                        run_info.set(local_run_label(payload))
                    except (OSError, PilotError):
                        run_info.set(f'OpenSfM {kind} · Ordner: ' + payload.name)
                    open_button['state'] = 'normal'
                    continue
                if event_kind == 'progress':
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
                cache_button['state'] = copy_button['state']
                try:
                    report = read_opensfm_run_metrics(state['workspace']) if state['workspace'] is not None else None
                    bridge_ok = report is not None and bridge_eligible(state['workspace'], report)
                    eligible = report is not None and can_continue_opensfm(report)
                except (OSError, PilotError):
                    eligible, bridge_ok = False, False
                continue_button['state'] = 'normal' if eligible else 'disabled'
                bridge_button['state'] = 'normal' if bridge_ok and modality == 'thermal' else 'disabled'
                if event_kind == 'success':
                    path = payload.thermal_geotiff if modality == 'thermal' else payload.rgb_geotiff
                    status.set(f'{kind}-Ergebnis zur Sichtpruefung erstellt: ' + str(path))
                elif event_kind == 'cache':
                    detail = payload['depthmap_cache_check']
                    status.set('Cachepruefung: ' + detail['status'] + '. Bildlauf bleibt unveraendert am bisherigen Stand.')
                    copy_note.set('Pruefbericht gespeichert. Kennzahlen kopieren und als Text einfuegen.')
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
            text = json.dumps(read_opensfm_run_metrics(state['workspace']), indent=2, ensure_ascii=False)
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
            report = read_opensfm_run_metrics(chosen)
            if report_modality(report) != modality:
                raise PilotError('Anderer Sensortyp.')
            label = local_run_label(chosen)
        except (OSError, PilotError):
            copy_note.set('Kein passender OpenSfM-Lauf dieser Bildart; RGB/Thermal/COLMAP getrennt halten.')
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
        continuation = report.get('dense_continuation')
        if continuation:
            status.set('Gespeicherte Fortsetzung: ' + states[continuation['status']] + '; urspruenglicher Bildlauf bleibt als Historie erhalten.')
            clock.set(f'Fortsetzung: {continuation["elapsed_seconds"]:.0f} Sekunden; urspruenglicher Lauf: {report.get("elapsed_seconds", 0):.0f} Sekunden')
        open_button['state'] = 'normal'
        copy_button['state'] = 'normal' if report['status'] != 'running' else 'disabled'
        cache_button['state'] = ('normal' if report['status'] in ('failed', 'cancelled')
                                 and report.get('registration_complete') else 'disabled')
        continue_button['state'] = 'normal' if can_continue_opensfm(report) else 'disabled'
        bridge_button['state'] = 'normal' if modality == 'thermal' and bridge_eligible(chosen, report) else 'disabled'

    def check_cache(continue_run=False, bridge=False):
        if state['running'] or state['workspace'] is None:
            return
        args = (state['workspace'], values['conda'].get(), values['environment'].get())
        state.update(running=True, tick=time.monotonic())
        cancel.clear()
        for control in controls:
            control['state'] = 'disabled'
        start_button['state'], copy_button['state'], cache_button['state'] = 'disabled', 'disabled', 'disabled'
        continue_button['state'] = 'disabled'
        bridge_button['state'] = 'disabled'
        cancel_button['state'] = 'normal'
        status.set('Einmaliger Zusatzabgleich wird in neuem Ordner vorbereitet; max. drei Stunden.' if bridge else
                   'Fortsetzung wird vorbereitet; max. zwei Stunden Tiefenkarten/drei Stunden insgesamt.' if continue_run
                   else 'Gespeicherte Tiefenkarten und Cluster pruefen; keine neue Bildverarbeitung. Maximal zehn Minuten.')
        copy_note.set('')
        def work_cache():
            try:
                if bridge:
                    result = execute_bridge(*args, cancel.is_set, lambda text: events.put(('progress', text)),
                        lambda path: events.put(('workspace', path)))
                    events.put(('success', result))
                elif continue_run:
                    result = execute_continue(*args, cancel.is_set, lambda text: events.put(('progress', text)))
                    events.put(('success', result))
                else:
                    events.put(('cache', execute_cache(*args, cancel.is_set)))
            except PilotError as error:
                events.put(('error', str(error)))
            except Exception:
                events.put(('error', 'Fortsetzung/Cachepruefung fehlgeschlagen; gespeicherten Bericht kopieren.'))
        threading.Thread(target=work_cache, daemon=False).start()

    start_button = ttk.Button(buttons, text=f'{kind}-Pilot starten', command=start)
    start_button.pack(side='left')
    cancel_button = ttk.Button(buttons, text='Abbrechen', state='disabled', command=abort)
    cancel_button.pack(side='left', padx=6)
    open_button = ttk.Button(buttons, text='Ausgabeordner oeffnen', state='disabled', command=show_output)
    open_button.pack(side='left', padx=6)
    load_button = ttk.Button(saved_buttons, text='Lauf laden', command=load_run)
    load_button.pack(side='left', padx=6)
    controls.append(load_button)
    cache_button = ttk.Button(saved_buttons, text='Tiefenkarten pruefen', state='disabled', command=check_cache)
    cache_button.pack(side='left', padx=6)
    continue_button = ttk.Button(saved_buttons, text='Tiefenkarten fortsetzen', state='disabled', command=lambda: check_cache(True))
    continue_button.pack(side='left', padx=6)
    bridge_button = ttk.Button(saved_buttons, text='Zusatzabgleich starten', state='disabled',
        command=lambda: check_cache(bridge=True))
    if modality == 'thermal':
        bridge_button.pack(side='left', padx=6)
    copy_button = ttk.Button(saved_buttons, text='Kennzahlen kopieren', state='disabled', command=copy_metrics)
    copy_button.pack(side='left', padx=6)
    ttk.Button(buttons, text='Schliessen', command=close).pack(side='right')
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(150, poll)
    root.mainloop()


def main(argv=None, *, modality='rgb'):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('database', 'project', 'output'):
        parser.add_argument('--' + key)
    parser.add_argument('--conda', default=CONDA)
    parser.add_argument('--environment', default=ENVIRONMENT)
    args = parser.parse_args(argv)
    if not any((args.database, args.project, args.output)):
        if modality == 'thermal':
            window(conda=args.conda, environment=args.environment, modality=modality)
        else:
            window(conda=args.conda, environment=args.environment)
        return 0
    if not all((args.database, args.project, args.output)):
        parser.error('Projektdatei, Projekt und Ausgabe zusammen angeben oder ohne Argumente starten.')
    try:
        result = execute(args.database, args.project, args.conda, args.environment, args.output,
                         lambda: False, print, lambda path: None, modality=modality)
        path = result.thermal_geotiff if modality == 'thermal' else result.rgb_geotiff
        print(modality.upper() + '-Ergebnis zur Sichtpruefung:', path)
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
