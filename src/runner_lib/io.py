"""binpb の柔軟ロード・保存とセットアップ一覧."""

from __future__ import annotations

from runner_lib import compat  # noqa: F401  # import 時に xarray の互換対策を適用  # isort: skip

import dataclasses
import json
import re
from pathlib import Path

from google.protobuf.message import DecodeError
from meridian.model import model
from meridian.schema.serde import meridian_serde
from mmm.v1 import mmm_pb2 as mmm_pb
from mmm.v1.model import mmm_kernel_pb2 as kernel_pb
from mmm.v1.model.meridian import meridian_model_pb2 as meridian_pb

from runner_lib import constants


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")


def setup_dir(output_dir: str | Path, setup_name: str) -> Path:
    """セットアップ単位の成果物ルート: OUTPUT_DIR/<setup>/"""
    return Path(output_dir) / safe_filename(setup_name)


def eda_dir(output_dir: str | Path, setup_name: str) -> Path:
    return setup_dir(output_dir, setup_name) / constants.EDA_DIRNAME


def checks_dir(output_dir: str | Path, setup_name: str) -> Path:
    return setup_dir(output_dir, setup_name) / constants.CHECKS_DIRNAME


def health_dir(output_dir: str | Path, setup_name: str) -> Path:
    return checks_dir(output_dir, setup_name) / constants.HEALTH_DIRNAME


def full_dir(output_dir: str | Path, setup_name: str) -> Path:
    return setup_dir(output_dir, setup_name) / constants.FULL_DIRNAME


def optimization_dir(output_dir: str | Path, setup_name: str) -> Path:
    return setup_dir(output_dir, setup_name) / constants.OPTIMIZATION_DIRNAME


def all_dir(output_dir: str | Path) -> Path:
    return Path(output_dir) / constants.ALL_DIRNAME


def summary_dir(output_dir: str | Path) -> Path:
    return Path(output_dir) / constants.SUMMARY_DIRNAME


def load_meridian_flexible(file_path: str | Path) -> model.Meridian:
    """Mmm / MmmKernel どちらの binpb でも Meridian を返す."""
    data = Path(file_path).read_bytes()
    try:
        full = mmm_pb.Mmm.FromString(data)
        kernel = full.mmm_kernel
        if kernel.model.Is(meridian_pb.MeridianModel.DESCRIPTOR):
            return meridian_serde.MeridianSerde().deserialize(kernel)
    except DecodeError:
        pass
    return meridian_serde.MeridianSerde().deserialize(kernel_pb.MmmKernel.FromString(data))


def posterior_path(output_dir: str | Path, setup_name: str) -> Path:
    return Path(output_dir) / f"{constants.POSTERIOR_PREFIX}{setup_name}.binpb"


def eda_json_path(output_dir: str | Path, setup_name: str) -> Path:
    return eda_dir(output_dir, setup_name) / f"{setup_name}_eda.json"


def eda_html_path(output_dir: str | Path, setup_name: str) -> Path:
    return eda_dir(output_dir, setup_name) / f"{setup_name}_eda.html"


def full_binpb_path(output_dir: str | Path, setup_name: str) -> Path:
    return full_dir(output_dir, setup_name) / f"{setup_name}_full.binpb"


def geo_json_path(output_dir: str | Path, setup_name: str) -> Path:
    return full_dir(output_dir, setup_name) / f"{setup_name}_geo.json"


def save_posterior(mmm: model.Meridian, output_dir: str | Path, setup_name: str) -> Path:
    out = posterior_path(output_dir, setup_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    meridian_serde.save_meridian(mmm, str(out))
    return out


@dataclasses.dataclass
class SetupStatus:
    name: str
    input_path: Path
    status: str  # "pending" | "done" | "eda_error"


def list_setups(input_dir: str | Path, output_dir: str | Path) -> list[SetupStatus]:
    result = []
    for p in sorted(Path(input_dir).glob("*.binpb")):
        if p.stem.startswith(constants.POSTERIOR_PREFIX):
            continue
        name = p.stem
        if posterior_path(output_dir, name).exists():
            status = "done"
        else:
            status = "pending"
            ej = eda_json_path(output_dir, name)
            if ej.exists():
                try:
                    if json.loads(ej.read_text()).get("has_error"):
                        status = "eda_error"
                except (json.JSONDecodeError, OSError):
                    pass
        result.append(SetupStatus(name=name, input_path=p, status=status))
    return result
