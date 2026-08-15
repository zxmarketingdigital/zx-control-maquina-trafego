#!/usr/bin/env python3
"""Setup 15 — Etapa 7: instalar as duas camadas da Máquina.

Instala as skills de decisão e execução em ``~/.claude/skills/`` de forma
idempotente. Uma versão local customizada é preservada em um backup antes de
ser substituída.
"""
import datetime as dt
import filecmp
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_SRC = REPO_ROOT / "skills"
SKILLS_DST = Path.home() / ".claude" / "skills"
BACKUP_BASE = SKILLS_DST

EXPECTED = [
    "meta-estrategista",
    "meta-campaign",
    "google-estrategista",
    "google-campaign",
]


def dirs_equal(a: Path, b: Path) -> bool:
    """Retorna True quando duas árvores de diretórios são idênticas."""
    if not (a.is_dir() and b.is_dir()):
        return False

    comparison = filecmp.dircmp(str(a), str(b))
    if (
        comparison.left_only
        or comparison.right_only
        or comparison.diff_files
        or comparison.funny_files
        or comparison.common_funny
    ):
        return False

    for subdir in comparison.common_dirs:
        if not dirs_equal(a / subdir, b / subdir):
            return False

    return True


def _unique_backup_path(slug: str, timestamp: str) -> Path:
    """Gera um caminho de backup sem sobrescrever outro backup existente."""
    base = BACKUP_BASE / f".s15-backup-{slug}-{timestamp}"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = BACKUP_BASE / f".s15-backup-{slug}-{timestamp}-{suffix}"
        suffix += 1
    return candidate


def backup_existing(path: Path, backup_dir: Path) -> None:
    """Copia uma skill existente para o diretório de backup."""
    if path.is_dir():
        shutil.copytree(path, backup_dir)
        return

    backup_dir.mkdir(parents=True, exist_ok=False)
    target = backup_dir / path.name
    if path.is_symlink():
        target.symlink_to(path.readlink())
    else:
        shutil.copy2(path, target)


def _print_contract() -> None:
    print("\n🔗 Contrato entre as duas camadas da Máquina:")
    print(
        "  • O meta-estrategista lê a conta ao vivo e recomenda pausar, escalar ou "
        "testar. Ele nunca executa sozinho e sempre pede confirmação antes de "
        "qualquer ação real."
    )
    print(
        "  • Quando a recomendação é testar, o estrategista aciona o meta-campaign, "
        "que gera os criativos e monta campanha, conjunto e anúncio via Graph API."
    )
    print(
        "  • O google-estrategista recomenda e nunca executa sozinho; toda ação real "
        "passa pelo google-campaign e exige confirmação do dono da conta."
    )
    print(
        "  • O google-campaign monta o plano dos 7 passos; a campanha nasce PAUSED "
        "com geo Brasil e idioma português obrigatórios."
    )
    print(
        "  • O QA de safe-zone é obrigatório antes de qualquer arte ir para aprovação; "
        "suba sempre os dois tamanhos (4:5 e 9:16)."
    )
    print("  • Mantenha o ledger que vincula cada arte ao respectivo ad_id.")


def main() -> int:
    _print_contract()

    if not SKILLS_SRC.is_dir():
        print(f"\n⚠️ Pasta skills/ ainda não existe no repo: {SKILLS_SRC}")
        print("   As skills serão instaladas quando outra etapa criar seu conteúdo.")

    try:
        SKILLS_DST.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"❌ Não foi possível preparar o destino das skills: {exc}")

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    installed = []
    updated = []
    skipped = []
    existing_without_source = []
    backupped = []
    pending = []
    errors = []

    for slug in EXPECTED:
        src = SKILLS_SRC / slug
        dst = SKILLS_DST / slug

        if not src.is_dir():
            pending.append(slug)
            if dst.is_dir():
                existing_without_source.append(slug)
                print(
                    f"⚠️ Skill {slug} pendente no repo; a versão já instalada será mantida."
                )
            else:
                print(f"⚠️ Skill pendente no repo: {slug}")
            continue

        if not dst.exists():
            try:
                shutil.copytree(src, dst)
                installed.append(slug)
            except OSError as exc:
                errors.append(slug)
                print(f"❌ Falha ao instalar {slug}: {exc}")
            continue

        if dirs_equal(src, dst):
            skipped.append(slug)
            continue

        backup_dir = _unique_backup_path(slug, timestamp)
        try:
            backup_existing(dst, backup_dir)
            backupped.append(backup_dir)
        except OSError as exc:
            errors.append(slug)
            print(f"❌ Falha ao criar backup de {slug}: {exc}")
            continue

        try:
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
            shutil.copytree(src, dst)
            updated.append(slug)
        except OSError as exc:
            errors.append(slug)
            print(f"❌ Falha ao atualizar {slug}: {exc}")
            if not dst.exists():
                try:
                    if backup_dir.is_dir():
                        shutil.copytree(backup_dir, dst)
                    else:
                        shutil.copy2(backup_dir, dst)
                except OSError as restore_exc:
                    print(f"❌ Não foi possível restaurar {slug}: {restore_exc}")

    available = [slug for slug in EXPECTED if (SKILLS_DST / slug).is_dir()]
    repo_available = [slug for slug in EXPECTED if (SKILLS_SRC / slug).is_dir()]

    print("\n📦 Resumo da instalação das camadas da Máquina:")
    if installed:
        print(f"  ✅ Instaladas (novas): {', '.join(installed)}")
    if updated:
        print(f"  🔄 Atualizadas (com diff vs versão local): {', '.join(updated)}")
    if skipped:
        print(f"  ⏭  Já estavam idênticas (puladas): {', '.join(skipped)}")
    if existing_without_source:
        print(
            "  📌 Já instaladas, aguardando conteúdo no repo: "
            + ", ".join(existing_without_source)
        )
    if pending:
        print(f"  ⚠️ Pendentes no repo: {', '.join(pending)}")
    if errors:
        print(f"  ❌ Com erro durante a instalação: {', '.join(errors)}")

    if backupped:
        print("\n💾 Backups das versões anteriores:")
        for backup_dir in backupped:
            print(f"   • {backup_dir}")
        print("   (apague depois se não precisar)")

    print(f"\n{len(available)}/{len(EXPECTED)} skills esperadas disponíveis em {SKILLS_DST}.")
    if repo_available:
        print(
            f"{len(repo_available)}/{len(EXPECTED)} skills esperadas disponíveis no repo; "
            "conteúdo pendente será instalado quando existir."
        )

    if not available and not repo_available:
        print("❌ Nenhuma das 4 skills está disponível no destino ou no repo.")
        return 1

    print("✅ Etapa 7 concluída; camadas disponíveis ou aguardando conteúdo no repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
