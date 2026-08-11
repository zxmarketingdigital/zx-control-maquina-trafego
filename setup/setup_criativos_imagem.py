#!/usr/bin/env python3
'''Setup 15 — Etapa 2: instalar skills de criativos de imagem.

Copia as skills de imagem do repositório para ~/.claude/skills/. A operação é
idempotente: versões idênticas são puladas e versões customizadas recebem um
backup antes de serem substituídas.
'''
import datetime as dt
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / 'skills'
SKILLS_DST = Path.home() / '.claude' / 'skills'
BACKUP_BASE = SKILLS_DST

EXPECTED = [
    'gerar-imagem',
    'zx-safezone',
    'criar-thumbnail',
    'meta-creative-brief',
    'criar-arte-oferta',
]


def dirs_equal(a: Path, b: Path) -> bool:
    '''Retorna True quando as árvores de diretórios têm conteúdo idêntico.'''
    if not (a.exists() and b.exists()):
        return False

    cmp = filecmp.dircmp(str(a), str(b))
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False

    for sub in cmp.common_dirs:
        if not dirs_equal(a / sub, b / sub):
            return False

    return True


def main():
    if not SKILLS_SRC.is_dir():
        print(f'⚠️ Pasta skills/ não encontrada no repositório: {SKILLS_SRC}')

    SKILLS_DST.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S')

    installed = []
    updated = []
    skipped = []
    backupped = []
    pending = []

    for slug in EXPECTED:
        src = SKILLS_SRC / slug
        dst = SKILLS_DST / slug

        if not src.is_dir():
            print(f'⚠️ Skill pendente no repo (pasta ainda não existe): {slug}')
            pending.append(slug)
            if dst.is_dir():
                skipped.append(slug)
            continue

        if not dst.exists():
            shutil.copytree(src, dst)
            installed.append(slug)
            continue

        if dirs_equal(src, dst):
            skipped.append(slug)
            continue

        backup_dir = BACKUP_BASE / f'.s15-backup-{slug}-{timestamp}'
        shutil.copytree(dst, backup_dir)
        shutil.rmtree(dst)
        shutil.copytree(src, dst)
        updated.append(slug)
        backupped.append(backup_dir)

    print()
    print('📦 Resumo da instalação de skills de criativos de imagem:')
    if installed:
        print(f'  ✅ Instaladas (novas): {", ".join(installed)}')
    if updated:
        print(f'  🔄 Atualizadas (com diff vs versão local): {", ".join(updated)}')
    if skipped:
        print(f'  ⏭  Já estavam idênticas ou já instaladas (puladas): {", ".join(skipped)}')
    if backupped:
        print()
        print('💾 Backups das versões anteriores:')
        for backup_dir in backupped:
            print(f'   • {backup_dir}')
        print('   (apague depois se não precisar)')
    if pending:
        print(f'  ⚠️ Pendentes no repo: {", ".join(pending)}')

    total = sum(1 for slug in EXPECTED if (SKILLS_DST / slug).is_dir())
    print()
    print(f'{total}/{len(EXPECTED)} skills esperadas no destino.')

    available = any(
        (SKILLS_SRC / slug).is_dir() or (SKILLS_DST / slug).is_dir()
        for slug in EXPECTED
    )
    if not available:
        print('❌ Nenhuma das skills esperadas está disponível no repo ou já instalada.')
        return 1

    if pending:
        print('As skills pendentes serão instaladas quando suas pastas forem criadas no repo.')
    print('Etapa 2 concluída sem bloquear pelas pendências do repo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
