"""Real Git ownership rejection and two exact process-only exceptions."""
import os
import shutil
import subprocess

import pytest


def test_git_accepts_only_two_trusted_build_directories_without_config_writes(tmp_path):
    git = shutil.which('git')
    if not git:
        pytest.skip('Git executable required')
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('GIT_')}
    global_config = tmp_path / 'unused-global-config'
    env.update(GIT_CONFIG_GLOBAL=str(global_config), GIT_CONFIG_NOSYSTEM='1')

    def run(*args, child_env=None):
        return subprocess.run([git, *args], env=child_env or env, cwd=tmp_path,
                              capture_output=True, text=True, timeout=15)

    repos = [tmp_path / name for name in ('source', 'opencl-clhpp', 'unrelated')]
    for repo in repos:
        result = run('init', str(repo))
        assert result.returncode == 0, result.stderr
    original_configs = {repo: (repo / '.git' / 'config').read_bytes() for repo in repos}
    ownerless = {**env, 'GIT_TEST_ASSUME_DIFFERENT_OWNER': '1'}
    denied = run('-C', str(repos[0]), 'rev-parse', '--git-dir', child_env=ownerless)
    assert denied.returncode == 128
    assert 'dubious ownership' in denied.stderr
    scoped = {**ownerless, 'GIT_CONFIG_COUNT': '3',
              'GIT_CONFIG_KEY_0': 'user.synthetic', 'GIT_CONFIG_VALUE_0': 'preserved',
              'GIT_CONFIG_KEY_1': 'safe.directory', 'GIT_CONFIG_VALUE_1': repos[0].resolve().as_posix(),
              'GIT_CONFIG_KEY_2': 'safe.directory', 'GIT_CONFIG_VALUE_2': repos[1].resolve().as_posix()}
    for repo in repos[:2]:
        result = run('-C', str(repo), 'rev-parse', '--git-dir', child_env=scoped)
        assert result.returncode == 0, result.stderr
        preserved = run('-C', str(repo), 'config', '--get', 'user.synthetic', child_env=scoped)
        assert preserved.stdout.strip() == 'preserved'
    unrelated = run('-C', str(repos[2]), 'rev-parse', '--git-dir', child_env=scoped)
    assert unrelated.returncode == 128
    assert 'dubious ownership' in unrelated.stderr
    denied_again = run('-C', str(repos[0]), 'rev-parse', '--git-dir', child_env=ownerless)
    assert denied_again.returncode == 128
    assert not global_config.exists()
    for repo in repos:
        assert (repo / '.git' / 'config').read_bytes() == original_configs[repo]
