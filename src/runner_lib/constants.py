"""パス規約とサブプロセス exit code(テストで固定される契約)."""

EXIT_OK = 0
EXIT_FAILURE = 2
EXIT_EDA_ERROR = 3

POSTERIOR_PREFIX = "posterior_"
EDA_DIRNAME = "eda"
CHECKS_DIRNAME = "checks"
FULL_DIRNAME = "full"
OPTIMIZATION_DIRNAME = "optimization"
HEALTH_DIRNAME = "health"  # checks/health/ に配置
ALL_DIRNAME = "_all"  # 横断比較(全セットアップ1枚もの)
SUMMARY_DIRNAME = "summary"  # 意思決定用の主要グラフ集約
