import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Union, List, Dict, Tuple, Optional

from cryri.config import CryConfig, ContainerConfig

DATETIME_FORMAT = "%Y_%m_%d_%H%M"
HASH_LENGTH = 6


def create_job_description(cfg: CryConfig) -> str:
    team_name = None
    if cfg.container.environment is not None:
        team_name = cfg.container.environment.get("TEAM_NAME", None)
    if team_name is None:
        team_name = os.environ.get('TEAM_NAME', None)
    job_description = cfg.cloud.description
    if job_description is None:
        job_description = str(Path(cfg.container.work_dir).resolve()).replace('/home/jovyan/', '').replace('/', '-')
    if team_name is not None:
        job_description = f"{job_description} #{team_name}"

    return job_description


def create_run_copy(cfg: CryConfig) -> Path:
    """Create a copy of the work directory for the run."""
    copy_from_folder = Path(cfg.container.work_dir).parent.resolve()

    now = datetime.now()
    now_str = now.strftime(DATETIME_FORMAT)
    hash_suffix = hashlib.sha1(
        now.strftime(f"{DATETIME_FORMAT}%S").encode()
    ).hexdigest()[:HASH_LENGTH]

    run_name = f"run_{now_str}_{hash_suffix}"
    run_folder = Path(cfg.container.cry_copy_dir) / run_name

    ignore_fun = shutil.ignore_patterns(*cfg.container.exclude_from_copy)
    shutil.copytree(
        copy_from_folder,
        run_folder,
        ignore=ignore_fun
    )

    return run_folder


def expand_config_vars_and_user(cfg: ContainerConfig):
    cfg.environment = expand_vars_and_user(cfg.environment)
    cfg.work_dir = expand_vars_and_user(cfg.work_dir)
    cfg.cry_copy_dir = expand_vars_and_user(cfg.cry_copy_dir)
    cfg.exclude_from_copy = expand_vars_and_user(cfg.exclude_from_copy)


def sanitize_config_paths(cfg: ContainerConfig):
    cfg.work_dir = sanitize_dir_path(cfg.work_dir)
    cfg.cry_copy_dir = sanitize_dir_path(cfg.cry_copy_dir)


def expand_vars_and_user(
        s: Union[None, str, Tuple[Any], List[Any], Dict[Any, Any]]
) -> Union[None, str, Tuple[Any], List[Any], Dict[Any, Any]]:
    """
    Universal function that returns a copy of an input with values expanded,
    if they are str and contain known expandable parts (`~` home or `$XXX` env var)
    """

    if s is None:
        return None

    if isinstance(s, tuple):
        # noinspection PyTypeChecker
        return tuple(expand_vars_and_user(x) for x in s)

    if isinstance(s, list):
        return [expand_vars_and_user(x) for x in s]

    if isinstance(s, dict):
        return {k: expand_vars_and_user(v) for k, v in s.items()}

    if not isinstance(s, str):
        return s

    from os.path import expandvars, expanduser
    # NB: expand vars then user, since vars could be expanded into a path
    #   that requires user expansion
    # NB2: expect only known/existing environment vars to be expanded!
    #   others will be left as-is
    return expanduser(expandvars(s))


def sanitize_dir_path(p: Optional[str]) -> Optional[str]:
    if p is None:
        return None

    # NB: it expects already expanded path
    # NB2: it expects existing path (= all parts along the path are existing)

    # resolve to make an absolute normalized path
    p = Path(p).resolve()
    if not p.is_dir():
        p = p.parent

    return str(p)
