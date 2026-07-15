# Changelog

## [0.2.0](https://github.com/tamko-5555/meridian-runner-lib/compare/meridian-runner-lib-v0.1.2...meridian-runner-lib-v0.2.0) (2026-07-15)


### Features

* add analysis spec builders ported from complete_model_geo ([e8b94ba](https://github.com/tamko-5555/meridian-runner-lib/commit/e8b94ba819bcd4c9c33ea2591a561cab073f634a))
* add checks module with summary table and exports ([06c2048](https://github.com/tamko-5555/meridian-runner-lib/commit/06c204848229d3cf3f621ee1444b91474062e607))
* add EDA module with ERROR gate and artifact saving ([724f8d8](https://github.com/tamko-5555/meridian-runner-lib/commit/724f8d85b8333421c47d0130d30fc50110afeb5c))
* add full binpb and geo JSON generation ([bb0409d](https://github.com/tamko-5555/meridian-runner-lib/commit/bb0409d86389b8a787524a3255e73d3f0312c89c))
* add io module with flexible binpb loading and setup listing ([59a2076](https://github.com/tamko-5555/meridian-runner-lib/commit/59a20760813971deb8c15340475474326ea3498f))
* add orchestrator setup_table and run_all_mcmc ([c2995eb](https://github.com/tamko-5555/meridian-runner-lib/commit/c2995eb3ed3ee074c166fcd02ff6c38f7ac0e5f1))
* add periods module for analysis window and budget calculation ([7121984](https://github.com/tamko-5555/meridian-runner-lib/commit/7121984736a93e28cc274f2c8e4a933c86155523))
* add plots module for chart suite generation ([8161e84](https://github.com/tamko-5555/meridian-runner-lib/commit/8161e841cc8dfa90d2bd3e3900be8cf85c40f235))
* add run_full CLI and orchestrator full generation ([47431ee](https://github.com/tamko-5555/meridian-runner-lib/commit/47431ee6e33220774a8c454ca14305d0eb671d65))
* add sampling wrapper and run_mcmc subprocess CLI ([409584b](https://github.com/tamko-5555/meridian-runner-lib/commit/409584bb6df5c979de0a5507a217e5cff30dfdd6))
* add synthetic data module and test fixtures ([3039a21](https://github.com/tamko-5555/meridian-runner-lib/commit/3039a2148e3b2545e14955d76a857bd8db0b96b3))
* scaffold meridian-runner-lib package ([7952361](https://github.com/tamko-5555/meridian-runner-lib/commit/79523612d6196cdefe6260888fea9de0307bd56f))


### Bug Fixes

* always close matplotlib figures in trace plot generation ([5b8fc41](https://github.com/tamko-5555/meridian-runner-lib/commit/5b8fc416b90ffbaa8ca290641546f815064d5d06))
* disable xarray bottleneck dispatch to prevent segfault in Colab EDA report ([f97a67e](https://github.com/tamko-5555/meridian-runner-lib/commit/f97a67ef79e3a7466dec77fe6c1f7a02faebbdea))
* emit RFC 8259-compliant JSON in model summaries export ([5ba2dfb](https://github.com/tamko-5555/meridian-runner-lib/commit/5ba2dfb8b282ba2379f8235063fdcc277413ccd0))
* fail closed on unexpected EDA check errors and cover national models ([7f12369](https://github.com/tamko-5555/meridian-runner-lib/commit/7f12369c74d84161a805405fdabc42d9c36ade22))
* validate cost_rate and harden empty/misconfigured directory handling ([458611e](https://github.com/tamko-5555/meridian-runner-lib/commit/458611ed8c01b936669dadb8a6837aadf1186ff5))


### Documentation

* point install example at v0.1.1 ([2f85b45](https://github.com/tamko-5555/meridian-runner-lib/commit/2f85b453458b80cc1ccdc25c34b9937b912577a1))
* point install example at v0.1.2 ([be4840d](https://github.com/tamko-5555/meridian-runner-lib/commit/be4840d02e6bd3ce43a3e8d5c3599df801b34843))
* update install URL to transferred repo (tamko-5555) ([f053fa7](https://github.com/tamko-5555/meridian-runner-lib/commit/f053fa74f719098790960d43e89f1f271af0b392))
