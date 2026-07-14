"""binpb の柔軟ロード・保存とセットアップ一覧."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from google.protobuf.message import DecodeError
from meridian.model import model
from meridian.schema.serde import meridian_serde
from mmm.v1 import mmm_pb2 as mmm_pb
from mmm.v1.model import mmm_kernel_pb2 as kernel_pb
from mmm.v1.model.meridian import meridian_model_pb2 as meridian_pb

from runner_lib import constants


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
    return Path(output_dir) / constants.EDA_DIRNAME / f"{setup_name}_eda.json"


def eda_html_path(output_dir: str | Path, setup_name: str) -> Path:
    return Path(output_dir) / constants.EDA_DIRNAME / f"{setup_name}_eda.html"


def full_binpb_path(output_dir: str | Path, setup_name: str) -> Path:
    return Path(output_dir) / constants.FULL_DIRNAME / f"{setup_name}_full.binpb"


def geo_json_path(output_dir: str | Path, setup_name: str) -> Path:
    return Path(output_dir) / constants.FULL_DIRNAME / f"{setup_name}_geo.json"


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
