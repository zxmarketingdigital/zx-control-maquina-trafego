#!/usr/bin/env python3
'''Setup 15 — Desinstalador idempotente.'''
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

OPERACAO = Path.home() / '.operacao-ia'
CONFIG_DIR = OPERACAO / 'config'
CONFIG = CONFIG_DIR / 'config.json'
PROGRESS = CONFIG_DIR / 'setup15_progress.json'
SKILLS_HOME = Path.home() / '.claude' / 'skills'
BLOG_PLIST = Path.home() / 'Library' / 'LaunchAgents' / 'com.setup15.blog-daily.plist'

ENV_FILES = [
    'gemini.env',
    'meta.env',
    'google_ads.env',
    'tracking.env',
    'cloudflare.env',
]

SKILLS = [
    'gerar-imagem',
    'zx-safezone',
    'criar-thumbnail',
    'meta-creative-brief',
    'criar-arte-oferta',
    'criar-anuncio-video-html',
    'criar-anuncio-video-momentum',
    'gerar-video-mp4',
    'criar-anuncio-video-gemini-omni',
    'meta-metrics-fetcher',
    'meta-performance-analyzer',
    'google-metrics-fetcher',
    'google-performance-analyzer',
    'preflight_guardian',
    'meta-estrategista',
    'meta-campaign',
    'google-estrategista',
    'google-campaign',
]

ERRORS = []
_REMOVE = object()
_MISSING = object()


def remove_path(path, label):
    try:
        if not path.exists() and not path.is_symlink():
            print(f'  - {label}: já removido')
            return
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f'  ✓ {label}: removido')
    except Exception as exc:
        ERRORS.append(f'{label}: {exc}')
        print(f'  ❌ {label}: não foi possível remover ({exc})')


def restore_or_remove_env(filename):
    path = CONFIG_DIR / filename
    backups = sorted(CONFIG_DIR.glob(f'.s15-backup-{filename}-*'))
    if backups:
        backup_path = backups[0]
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            shutil.copy2(backup_path, path)
            os.chmod(path, 0o600)
            backup_path.unlink()
            for leftover in backups[1:]:
                leftover.unlink()
            print(f'  ↩️  {filename}: restaurado ao estado anterior ao Setup 15 (já existia antes da instalação)')
        except Exception as exc:
            ERRORS.append(f'{filename}: falha ao restaurar backup ({exc})')
            print(f'  ❌ {filename}: não foi possível restaurar o backup ({exc})')
        return
    remove_path(path, filename)


def restore_or_remove_skill(slug):
    path = SKILLS_HOME / slug
    backups = sorted(SKILLS_HOME.glob(f'.s15-backup-{slug}-*'))
    if backups:
        oldest = backups[0]
        try:
            if path.exists() and path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
            shutil.move(str(oldest), str(path))
            for leftover in backups[1:]:
                shutil.rmtree(leftover, ignore_errors=True)
            print(f'  ↩️  skill {slug}: restaurada ao estado anterior ao Setup 15 (já existia antes da instalação)')
        except Exception as exc:
            ERRORS.append(f'skill {slug}: falha ao restaurar backup ({exc})')
            print(f'  ❌ skill {slug}: não foi possível restaurar o backup ({exc})')
        return
    remove_path(path, f'skill {slug}')


def read_progress():
    if not PROGRESS.exists():
        return None
    try:
        return json.loads(PROGRESS.read_text(encoding='utf-8'))
    except Exception as exc:
        ERRORS.append(f'checkpoint: {exc}')
        print(f'  ⚠️  checkpoint inválido; não foi possível ler fase anterior ({exc})')
        return None


def previous_phase(progress):
    if not isinstance(progress, dict):
        return _MISSING

    marker = progress.get('phase_completed_before_setup15', _MISSING)
    if isinstance(marker, dict) and 'present' in marker:
        if marker.get('present'):
            return marker.get('value', _MISSING)
        return _REMOVE

    for key in ('previous_phase_completed', 'phase_completed_previous'):
        if key in progress:
            value = progress[key]
            if isinstance(value, dict) and 'present' in value:
                return value.get('value', _MISSING) if value.get('present') else _REMOVE
            return value
    return _MISSING


def _write_config(data):
    CONFIG.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + chr(10),
        encoding='utf-8',
    )


def revert_phase(progress):
    if not CONFIG.exists():
        print('  - config.json: não existe')
        return
    try:
        data = json.loads(CONFIG.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('config.json não contém um objeto JSON')
        if data.get('phase_completed') != 15:
            print(f'  - phase_completed já é {data.get("phase_completed")!r}')
            return

        old_phase = previous_phase(progress)
        if old_phase is _MISSING or old_phase is _REMOVE:
            data.pop('phase_completed', None)
            description = 'chave phase_completed removida (nenhuma fase anterior salva)'
        else:
            data['phase_completed'] = old_phase
            description = f'phase_completed restaurado para {old_phase!r}'
        _write_config(data)
        print(f'  ✓ {description}')
    except Exception as exc:
        ERRORS.append(f'reverter phase_completed: {exc}')
        print(f'  ❌ Não foi possível reverter phase_completed: {exc}')


def remove_blog_launchagent():
    if not BLOG_PLIST.exists():
        print('  - LaunchAgent blog-daily: já removido')
        return

    try:
        unloaded = subprocess.run(
            ['launchctl', 'unload', str(BLOG_PLIST)],
            capture_output=True,
            text=True,
            check=False,
        )
        if unloaded.returncode == 0:
            print('  ✓ LaunchAgent blog-daily: descarregado')
        else:
            detail = (unloaded.stderr or unloaded.stdout or '').strip()
            print(
                '  ⚠️  LaunchAgent blog-daily: unload não confirmou o descarregamento '
                f'(o job pode já não estar carregado{": " + detail if detail else ""})'
            )
    except OSError as exc:
        print(f'  ⚠️  LaunchAgent blog-daily: não foi possível executar unload ({exc})')

    remove_path(BLOG_PLIST, 'plist do LaunchAgent blog-daily')


def uninstall(choice):
    progress = read_progress()

    print()
    print('Removendo configurações do Setup 15...')
    print()
    print('Reverter fase:')
    revert_phase(progress)

    print()
    print('Configs e checkpoint:')
    for filename in ENV_FILES:
        restore_or_remove_env(filename)
    remove_path(PROGRESS, 'setup15_progress.json')

    if choice == 'B':
        print()
        print('Skills:')
        for slug in SKILLS:
            restore_or_remove_skill(slug)
    else:
        print()
        print('Skills: mantidas (escolha [A])')

    remove_blog_launchagent()


def main():
    print('=' * 60)
    print('DESINSTALAR Setup 15 — Máquina de Tráfego')
    print('=' * 60)
    print()
    print('[A] Manter skills + remover só configs/checkpoint')
    print('[B] Remover TUDO, inclusive as skills do Setup 15')
    print('[C] Cancelar')
    print()

    try:
        choice = input('Escolha [A/B/C]: ').strip().upper()
    except (EOFError, KeyboardInterrupt):
        choice = 'C'

    if choice not in ('A', 'B'):
        print('Cancelado. Nenhuma alteração foi feita.')
        return 0

    try:
        uninstall(choice)
    except Exception as exc:
        ERRORS.append(f'erro inesperado: {exc}')
        print(f'❌ Erro inesperado capturado: {exc}')

    print()
    if ERRORS:
        print('⚠️  Uninstall concluído com ocorrências:')
        for error in ERRORS:
            print(f'  - {error}')
        return 1

    print('✅ Uninstall completo.')
    if choice == 'A':
        print('   Skills preservadas para uma eventual reinstalação.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'❌ Desinstalação interrompida de forma segura: {exc}')
        sys.exit(1)
