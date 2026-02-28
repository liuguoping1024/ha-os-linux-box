################################################################################
#
# python-bflb-crypto-plus
#
################################################################################

PYTHON_BFLB_CRYPTO_PLUS_VERSION = 1.0
PYTHON_BFLB_CRYPTO_PLUS_SOURCE = bflb-crypto-plus-$(PYTHON_BFLB_CRYPTO_PLUS_VERSION).tar.gz
PYTHON_BFLB_CRYPTO_PLUS_SITE = https://files.pythonhosted.org/packages/9a/d8/f62021beefe0ef6d29fbd978f6d439b2f8bde2f10f9e281ba259a5f147b4
PYTHON_BFLB_CRYPTO_PLUS_SETUP_TYPE = setuptools
PYTHON_BFLB_CRYPTO_PLUS_LICENSE = MIT

$(eval $(python-package))
