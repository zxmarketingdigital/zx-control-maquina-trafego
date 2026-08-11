#!/usr/bin/env python3
'''Setup 15 — Auditoria técnica da instalação.'''
import json
import sys
from pathlib import Path

OPERACAO = Path.home() / '.operacao-ia'
CONFIG_DIR = OPERACAO / 'config'
SKILLS = Path.home() / '.claude' / 'skills'
PROGRESS = CONFIG_DIR / 'setup15_progress.json'
CONFIG = CONFIG_DIR / 'config.json'
GEMINI_ENV = CONFIG_DIR / 'gemini.env'
BLOG_BUILD = Path(__file__).resolve().parent.parent / 'blog' / 'generator' / 'build.js'

EXPECTED_SKILLS = [
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
    'preflight_guardian',
    'meta-estrategista',
    'meta-campaign',
]

BASE_DIRS = [
    OPERACAO / 'config',
    OPERACAO / 'scripts',
    OPERACAO / 'dashboards',
    OPERACAO / 'leads',
    OPERACAO / 'logs',
]

CHECKS = []
REQUIRED_CHECKS = {
    'Python 3.9+',
    'Checkpoint setup15 válido',
    'Chave Gemini configurada',
    'Estado do Setup íntegro',
    'Motor do blog instalado',
    'Diretórios base',
}


def check(name, fn):
    try:
        ok, msg = fn()
    except Exception as exc:
        ok, msg = False, f'Exceção: {exc}'
    CHECKS.append((name, bool(ok), str(msg)))


def c_python_version():
    version = sys.version_info
    ok = version >= (3, 9)
    return ok, f'Python {version.major}.{version.minor}.{version.micro}'


def c_progress():
    if not PROGRESS.exists():
        return False, 'setup15_progress.json não existe'
    try:
        json.loads(PROGRESS.read_text(encoding='utf-8'))
        return True, 'setup15_progress.json existe e contém JSON válido'
    except Exception as exc:
        return False, f'JSON corrompido: {exc}'


def _gemini_key_from_env():
    content = GEMINI_ENV.read_text(encoding='utf-8')
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, separator, value = line.partition('=')
        if separator and key.strip() == 'GEMINI_API_KEY':
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1].strip()
            return value
    return ''


def c_gemini():
    if not GEMINI_ENV.exists():
        return False, 'gemini.env não existe'
    mode = oct(GEMINI_ENV.stat().st_mode)[-3:]
    if mode != '600':
        return False, (
            f'gemini.env está com permissão {mode}; execute novamente a Etapa 1 '
            'para corrigir para 600'
        )
    try:
        value = _gemini_key_from_env()
    except Exception as exc:
        return False, f'Não foi possível ler gemini.env: {exc}'
    placeholders = {
        'your_gemini_api_key',
        'sua_chave_aqui',
        'replace_me',
        'changeme',
        '<sua-chave>',
    }
    if not value or value.lower() in placeholders or value.startswith('<'):
        return False, 'GEMINI_API_KEY ausente ou ainda em formato de placeholder'
    return True, 'GEMINI_API_KEY configurada (valor mascarado)'


def c_skills():
    installed = [
        slug for slug in EXPECTED_SKILLS
        if (SKILLS / slug / 'SKILL.md').exists()
    ]
    missing = [slug for slug in EXPECTED_SKILLS if slug not in installed]
    if missing:
        return True, (
            f'{len(installed)}/{len(EXPECTED_SKILLS)} skills opcionais instaladas; '
            f'faltam: {", ".join(missing)} (não bloqueante)'
        )
    return True, f'{len(installed)}/{len(EXPECTED_SKILLS)} skills opcionais instaladas'


def c_config():
    candidates = (
        (PROGRESS, 'setup15_progress.json'),
        (CONFIG, 'config.json'),
    )
    errors = []
    for path, label in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                errors.append(f'{label} não contém um objeto JSON')
                continue
            if path == CONFIG and 'phase_completed' not in data:
                errors.append(f'{label}: chave phase_completed ausente')
                continue
            return True, f'{label} íntegro'
        except Exception as exc:
            errors.append(f'{label} corrompido: {exc}')
    if errors:
        return False, '; '.join(errors)
    return False, 'nem setup15_progress.json nem config.json existem'


def c_blog():
    if BLOG_BUILD.exists():
        return True, f'build.js encontrado em {BLOG_BUILD}'
    return False, f'build.js não encontrado em {BLOG_BUILD}'


def c_base_dirs():
    missing = [str(path.relative_to(OPERACAO)) for path in BASE_DIRS if not path.is_dir()]
    if missing:
        return False, f'Diretórios ausentes: {", ".join(missing)}'
    return True, 'config, scripts, dashboards, leads e logs existem'


def _write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + chr(10),
        encoding='utf-8',
    )


def _numeric_phase_at_least(value, minimum):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value >= minimum
    if isinstance(value, str):
        try:
            return int(value.strip()) >= minimum
        except ValueError:
            return False
    return False


def mark_phase_completed():
    '''Marca 15 sem sobrescrever campos nem reduzir fase maior.'''
    try:
        if CONFIG.exists():
            data = json.loads(CONFIG.read_text(encoding='utf-8'))
            if isinstance(data, dict) and 'phase_completed' in data:
                current = data.get('phase_completed')
                if _numeric_phase_at_least(current, 15):
                    return True, f'phase_completed preservado em {current!r}'

                if PROGRESS.exists():
                    progress = json.loads(PROGRESS.read_text(encoding='utf-8'))
                    if isinstance(progress, dict) and 'phase_completed_before_setup15' not in progress:
                        previous = {'present': 'phase_completed' in data}
                        if previous['present']:
                            previous['value'] = current
                        progress['phase_completed_before_setup15'] = previous
                        _write_json(PROGRESS, progress)

                data['phase_completed'] = 15
                _write_json(CONFIG, data)
                return True, 'phase_completed atualizado para 15'

        if PROGRESS.exists():
            progress = json.loads(PROGRESS.read_text(encoding='utf-8'))
            if not isinstance(progress, dict):
                return False, 'setup15_progress.json não contém um objeto JSON'
            current = progress.get('phase_completed')
            if _numeric_phase_at_least(current, 15):
                return True, f'phase_completed preservado em {current!r}'
            progress['phase_completed'] = 15
            _write_json(PROGRESS, progress)
            return True, 'phase_completed atualizado para 15 no setup15_progress.json'

        return False, 'nenhum arquivo de estado do Setup foi encontrado'
    except Exception as exc:
        return False, f'Não foi possível atualizar phase_completed: {exc}'


def main():
    CHECKS.clear()
    print()
    print('🔍 Auditoria Técnica — Setup 15')
    print()

    check('Python 3.9+', c_python_version)
    check('Checkpoint setup15 válido', c_progress)
    check('Chave Gemini configurada', c_gemini)
    check('Skills opcionais instaladas', c_skills)
    check('Estado do Setup íntegro', c_config)
    check('Motor do blog instalado', c_blog)
    check('Diretórios base', c_base_dirs)

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    for name, ok, message in CHECKS:
        icon = '✅' if ok else '❌'
        print(f'  {icon} {name:32s} — {message}')

    print()
    print(f'{passed}/{total} checks passaram')
    print()

    blocking_failures = [
        name for name, ok, _ in CHECKS
        if not ok and name in REQUIRED_CHECKS
    ]
    if blocking_failures:
        print('⚠️  Falhas obrigatórias: ' + ', '.join(blocking_failures))
        print('Corrija o que foi indicado e execute a auditoria novamente.')
        return 1

    phase_ok, phase_message = mark_phase_completed()
    if not phase_ok:
        print(f'❌ Fechamento: {phase_message}')
        return 1
    print(f'✅ Fechamento: {phase_message}')
    print('🎉 Auditoria concluída sem falhas bloqueantes.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'❌ Auditoria interrompida de forma segura: {exc}')
        sys.exit(1)
