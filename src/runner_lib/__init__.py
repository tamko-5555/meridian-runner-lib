from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("meridian-runner-lib")
except PackageNotFoundError:  # 未インストールのソースツリー実行時
    __version__ = "0.0.0"
